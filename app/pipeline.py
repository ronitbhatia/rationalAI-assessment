"""
Main pipeline orchestration.

This module coordinates the complete workflow:
1. Normalize target company profile
2. Discover candidate companies
3. Extract and validate candidate data
4. Score and rank comparables
5. Return final results

All orchestration logic is centralized here for maintainability.
"""

import logging
from typing import List, Optional
import os

from app.schemas import (
    TargetInput,
    NormalizedTarget,
    CandidateExtraction,
    ComparableCompany
)
from app.extraction import normalize_target, extract_candidate_fields, validate_candidate
from app.retrieval import (
    build_search_queries,
    discover_candidates_simple,
    fetch_candidate_data
)
from app.exchanges import resolve_exchange_ticker
from app.compare import (
    compute_validation_score,
    validate_product_overlap,
    validate_segment_overlap,
    validate_public_listing,
    validate_not_unrelated,
    create_comparable
)

logger = logging.getLogger(__name__)

# Default configuration values (can be overridden via environment variables)
DEFAULT_MAX_CANDIDATES = int(os.getenv("MAX_CANDIDATES", "40"))
DEFAULT_MIN_SCORE = float(os.getenv("MIN_SCORE", "0.35"))


def normalize_target_profile(target: TargetInput, model: str) -> NormalizedTarget:
    """
    Step 1: Normalize target company profile.
    
    Args:
        target: Target company input
        model: OpenAI model to use
        
    Returns:
        Normalized target profile
    """
    logger.info(f"Step 1/4: Normalizing target profile for {target.name}")
    
    try:
        normalized = normalize_target(
            name=target.name,
            business_description=target.business_description,
            url=target.url,
            primary_industry=target.primary_industry_classification,
            model=model
        )
        
        
        logger.info(f"Extracted {len(normalized.target_products_services)} products/services")
        logger.info(f"Extracted {len(normalized.target_customer_segments)} customer segments")
        
        return normalized
    except Exception as e:
        logger.error(f"ERROR in normalize_target_profile: {e}")
        import traceback
        traceback.print_exc()
        raise


def discover_candidates(
    normalized_target: NormalizedTarget,
    max_candidates: int = DEFAULT_MAX_CANDIDATES
) -> List[tuple[str, Optional[str]]]:
    """
    Step 2: Discover candidate companies.
    
    Args:
        normalized_target: Normalized target profile
        max_candidates: Maximum number of candidates to discover
        
    Returns:
        List of (company_name, url) tuples
    """
    logger.info("Building search queries...")
    
    queries = build_search_queries(
        products_services=normalized_target.target_products_services,
        customer_segments=normalized_target.target_customer_segments,
        industry_keywords=normalized_target.keywords
    )
    
    logger.info(f"Built {len(queries)} search queries")
    
    candidates = discover_candidates_simple(queries, max_candidates=max_candidates)
    
    logger.info(f"Discovered {len(candidates)} candidate companies")
    
    return candidates


def fetch_and_extract_candidate(
    company_name: str,
    url: Optional[str],
    normalized_target: NormalizedTarget,
    model: str
) -> Optional[CandidateExtraction]:
    """
    Step 3: Fetch data and extract fields for a candidate.
    
    Args:
        company_name: Name of candidate company
        url: Optional company URL
        normalized_target: Normalized target profile (for context)
        model: OpenAI model to use
        
    Returns:
        CandidateExtraction or None if extraction fails
    """
    try:
        # Fetch raw data (with timeout handling)
        text_snippets, source_urls = fetch_candidate_data(company_name, url)
        
        if not text_snippets:
            logger.debug(f"No text snippets found for {company_name}, using minimal info")
            # Still try extraction with minimal info
        
        # Try to resolve exchange/ticker from snippets (non-blocking)
        try:
            exchange, ticker = resolve_exchange_ticker(text_snippets, company_name, url)
        except Exception as e:
            logger.debug(f"Exchange/ticker resolution failed for {company_name}: {e}")
            exchange, ticker = None, None
        
        # Extract fields using LLM
        try:
            extraction = extract_candidate_fields(
                company_name=company_name,
                text_snippets=text_snippets,
                source_urls=source_urls,
                model=model
            )
        except Exception as e:
            logger.warning(f"LLM extraction failed for {company_name}: {e}")
            return None
        
        # Override with resolved exchange/ticker if LLM didn't find them
        if not extraction.exchange and exchange:
            extraction.exchange = exchange
        if not extraction.ticker and ticker:
            extraction.ticker = ticker
        
        return extraction
    
    except Exception as e:
        logger.warning(f"Failed to extract candidate {company_name}: {e}")
        return None


def validate_and_score_candidate(
    candidate: CandidateExtraction,
    normalized_target: NormalizedTarget,
    model: str,
    min_score: float = DEFAULT_MIN_SCORE
) -> Optional[ComparableCompany]:
    """
    Step 4: Validate and score a candidate.
    
    Args:
        candidate: Extracted candidate data
        normalized_target: Normalized target profile
        model: OpenAI model to use
        min_score: Minimum validation score threshold
        
    Returns:
        ComparableCompany if valid, None otherwise
    """
    try:
        # Compute similarity scores
        validation_score = compute_validation_score(normalized_target, candidate)
        
        # Run validation checks
        product_overlap = validate_product_overlap(normalized_target, candidate)
        segment_overlap = validate_segment_overlap(normalized_target, candidate)
        public_listing = validate_public_listing(candidate)
        not_unrelated = validate_not_unrelated(normalized_target, candidate)
        
        # LLM validation check
        validation_check = validate_candidate(
            target_products=normalized_target.target_products_services,
            target_segments=normalized_target.target_customer_segments,
            candidate=candidate,
            model=model
        )
        
        # Combine checks: public_listing is preferred but not required if other checks pass
        # Allow candidates without ticker if they score well and pass other checks
        passes_automated = (
            product_overlap and
            segment_overlap and
            not_unrelated
        )
        
        # More lenient validation logic:
        # 1. Very high score (>= 0.7) - always pass (failsafe)
        # 2. High score (>= 0.5) with LLM validation - pass
        # 3. Medium score (>= min_score) with automated checks AND LLM validation - pass
        # 4. Public listing is preferred but not required if score is good
        if validation_score >= 0.7:
            # High score failsafe - always accept
            passes = True
        elif validation_score >= 0.5 and validation_check.is_plausible:
            # Good score with LLM validation - accept
            passes = True
        elif validation_score >= min_score:
            # Standard threshold: need automated checks AND LLM validation
            # Public listing preferred but not required
            passes = passes_automated and validation_check.is_plausible
            # If public listing is missing but everything else passes, still accept if score is decent
            if not public_listing and passes and validation_score >= 0.4:
                logger.debug(f"Accepting {candidate.name} without public listing (good score and validation)")
        else:
            passes = False
        
        if not passes:
            logger.debug(
                f"Rejected {candidate.name}: score={validation_score:.3f}, "
                f"product_overlap={product_overlap}, segment_overlap={segment_overlap}, "
                f"public_listing={public_listing}, is_plausible={validation_check.is_plausible}"
            )
            return None
        
        # Create comparable company
        comparable = create_comparable(
            candidate=candidate,
            target=normalized_target,
            validation_check=validation_check,
            validation_score=validation_score
        )
        
        return comparable
    
    except Exception as e:
        logger.error(f"Failed to validate candidate {candidate.name}: {e}")
        return None


def run_pipeline(
    target: TargetInput,
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    min_score: float = DEFAULT_MIN_SCORE,
    model: str = "gpt-4o-mini",
    max_final: int = 10
) -> List[ComparableCompany]:
    """
    Run the complete pipeline to find comparable companies.
    
    Args:
        target: Target company input
        max_candidates: Maximum number of candidates to discover
        min_score: Minimum validation score threshold
        model: OpenAI model to use
        max_final: Maximum number of final comparables to return
        
    Returns:
        List of comparable companies, sorted by validation score
    """
    logger.info(f"Starting pipeline for target: {target.name}")
    
    # Step 1: Normalize target profile
    normalized_target = normalize_target_profile(target, model)
    
    # Step 2: Discover candidates
    candidates = discover_candidates(normalized_target, max_candidates=max_candidates)
    
    if not candidates:
        logger.warning("No candidates discovered")
        return []
    
    # Step 3 & 4: Fetch, extract, validate, and score each candidate
    comparables = []
    total_candidates = len(candidates)
    
    logger.info(f"Step 3/4: Processing {total_candidates} candidates")
    logger.info(f"Estimated time: ~{total_candidates * 25 / 60:.1f} minutes (with rate limiting)")
    
    for idx, (company_name, url) in enumerate(candidates, 1):
        logger.info(f"Processing candidate {idx}/{total_candidates}: {company_name}")
        
        try:
            # Extract candidate fields (includes rate limiting)
            candidate = fetch_and_extract_candidate(
                company_name=company_name,
                url=url,
                normalized_target=normalized_target,
                model=model
            )
            
            if not candidate:
                logger.debug(f"Skipped {company_name}: extraction failed")
                continue
            
            # Validate and score (includes rate limiting)
            comparable = validate_and_score_candidate(
                candidate=candidate,
                normalized_target=normalized_target,
                model=model,
                min_score=min_score
            )
            
            if comparable:
                comparables.append(comparable)
                logger.info(
                    f"Accepted: {comparable.name} "
                    f"(score={comparable.validation_score:.3f}, "
                    f"ticker={comparable.ticker or 'N/A'})"
                )
            else:
                logger.debug(f"Rejected {company_name}: validation failed")
        
        except KeyboardInterrupt:
            logger.warning("Interrupted by user")
            break
        except Exception as e:
            logger.warning(f"Error processing {company_name}: {e}")
            continue
    
    logger.info(f"Step 4/4: Completed processing - {len(comparables)} comparables found")
    
    # Sort by validation score (descending)
    comparables.sort(key=lambda x: x.validation_score, reverse=True)
    
    # Also consider completeness (number of evidence URLs, field completeness)
    # Secondary sort: more complete records first
    comparables.sort(
        key=lambda x: (
            x.validation_score,
            len(x.evidence_urls),
            bool(x.sic_industry),
            bool(x.exchange and x.ticker)
        ),
        reverse=True
    )
    
    # Return top N
    final_comparables = comparables[:max_final]
    
    logger.info(f"Pipeline completed: {len(final_comparables)} final comparables")
    
    return final_comparables

