"""LLM prompts to extract structured fields from raw text."""

import json
import logging
import os
import time
import re
from typing import Optional, List
from openai import OpenAI
from dotenv import load_dotenv

from app.schemas import (
    NormalizedTarget,
    CandidateExtraction,
    ValidationCheck,
    FailureType
)

load_dotenv()

logger = logging.getLogger(__name__)

# Initialize OpenAI client with validation
api_key = os.getenv("OPENAI_API_KEY")
if not api_key or api_key == "your_openai_api_key_here":
    raise ValueError(
        "OPENAI_API_KEY not found in environment. "
        "Please set it in .env file or environment variables."
    )

# Configure OpenAI API
client = OpenAI(api_key=api_key)
logger.info(f"OpenAI API Key loaded: {api_key[:10]}...{api_key[-4:]}")

# Default model configuration
# Available models: gpt-5, gpt-4o, gpt-4-turbo, gpt-3.5-turbo
# gpt-5 is the latest and most capable model
DEFAULT_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
logger.info(f"Using model: {DEFAULT_MODEL}")

# Rate limiting: add delay between API calls to avoid rate limit errors
_last_api_call_time = 0
_min_api_call_interval = 25.0  # Minimum seconds between API calls (OpenAI free tier rate limits)


def rate_limit_wait():
    """Wait to avoid rate limiting."""
    global _last_api_call_time
    current_time = time.time()
    time_since_last_call = current_time - _last_api_call_time
    
    if time_since_last_call < _min_api_call_interval:
        wait_time = _min_api_call_interval - time_since_last_call
        logger.info(f"Rate limiting: waiting {wait_time:.1f}s before next API call...")
        time.sleep(wait_time)
    
    _last_api_call_time = time.time()


def exponential_backoff_retry(func, max_retries: int = 5, base_delay: float = 2.0):
    """
    Retry function with exponential backoff and rate limit handling.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        base_delay: Base delay in seconds (default 2s)
        
    Returns:
        Function result
    """
    for attempt in range(max_retries):
        try:
            # Wait before each API call to avoid rate limiting
            rate_limit_wait()
            return func()
        except Exception as e:
            error_str = str(e).lower()
            error_msg = str(e)
            
            # Check for quota issues first (fail fast to avoid unnecessary retries)
            if 'quota' in error_str or 'resource exhausted' in error_str or 'insufficient_quota' in error_str:
                error_msg = (
                    "\n" + "="*60 + "\n"
                    "ERROR: OPENAI API QUOTA EXCEEDED\n"
                    "="*60 + "\n"
                    "Your OpenAI API account has no credits/quota remaining.\n\n"
                    "To fix this:\n"
                    "1. Go to: https://platform.openai.com/account/billing\n"
                    "2. Add a payment method and purchase credits\n"
                    "3. Wait a few minutes for the quota to update\n"
                    "4. Try again\n"
                    "="*60 + "\n"
                )
                print(error_msg)
                logger.error(error_msg)
                raise Exception("OpenAI API quota exceeded. Please check your quota and billing settings.")
            
            # Handle rate limiting errors (429 status code)
            if 'rate limit' in error_str or '429' in error_str or 'too many requests' in error_str:
                wait_time = base_delay * (2 ** attempt) + 1
                logger.warning(f"Rate limited. Retry {attempt + 1}/{max_retries} after {wait_time:.1f}s...")
                time.sleep(wait_time)
            elif attempt == max_retries - 1:
                logger.error(f"Failed after {max_retries} retries: {e}")
                raise
            else:
                delay = base_delay * (2 ** attempt)
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {delay:.1f}s: {str(e)[:100]}")
                time.sleep(delay)
    return None


def _extract_json_from_response(text: str) -> dict:
    """
    Extract JSON from OpenAI response text.
    
    OpenAI may return JSON wrapped in markdown code blocks or with extra text.
    This function extracts the JSON portion.
    
    Args:
        text: Raw response text from OpenAI
        
    Returns:
        Parsed JSON dictionary
    """
    # Try to find JSON in markdown code blocks
    json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
    if json_match:
        return json.loads(json_match.group(1))
    
    # Try to find JSON object directly
    json_match = re.search(r'\{.*\}', text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(0))
        except:
            pass
    
    # If no JSON found, try parsing the whole text
    try:
        return json.loads(text)
    except:
        raise ValueError(f"Could not extract JSON from response: {text[:200]}")


def normalize_target(
    name: str,
    business_description: str,
    url: Optional[str] = None,
    primary_industry: Optional[str] = None,
    model: str = DEFAULT_MODEL
) -> NormalizedTarget:
    """
    Normalize target company profile using OpenAI LLM.
    
    This function takes a raw business description and extracts structured information
    including products/services, customer segments, and industry keywords. The LLM
    is constrained to output only valid JSON and is instructed not to invent facts.
    
    Args:
        name: Company name
        business_description: Raw business description text
        url: Optional company URL for context
        primary_industry: Optional primary industry classification (SIC name)
        model: OpenAI model to use (default: gpt-5)
        
    Returns:
        NormalizedTarget object containing:
        - target_products_services: List of 5-12 product/service bullets
        - target_customer_segments: List of 5-10 customer segment bullets
        - canonical_sic_names: List of SIC industry names
        - keywords: List of search keywords for candidate discovery
        
    Raises:
        Exception: If API call fails after retries, returns fallback NormalizedTarget
    """
    logger.info(f"Making OpenAI API call to normalize target: {name} (model: {model})")
    
    # Construct prompt for LLM to extract structured information
    # The prompt explicitly instructs the model to output only valid JSON
    prompt = f"""You are an investment analyst helping to identify comparable companies.

Given the following company information, extract and normalize the profile:

Company Name: {name}
Business Description: {business_description}
Primary Industry: {primary_industry or "Not specified"}
URL: {url or "Not provided"}

Your task:
1. Extract 5-12 key products/services as concise bullet points
2. Extract 5-10 key customer segments/verticals as concise bullet points
3. Identify canonical SIC industry name(s) if derivable
4. Generate 10-15 search keywords for finding comparable companies

Output ONLY valid JSON in this exact format:
{{
    "target_products_services": ["bullet 1", "bullet 2", ...],
    "target_customer_segments": ["segment 1", "segment 2", ...],
    "canonical_sic_names": ["SIC name 1", ...],
    "keywords": ["keyword 1", "keyword 2", ...]
}}

Be specific and avoid generic terms. Focus on distinctive offerings and customer types.
Do not include any text outside the JSON object."""

    def call_api():
        logger.debug(f"Sending request to OpenAI API (model: {model})")
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.3
            )
            response_text = response.choices[0].message.content
            logger.debug(f"Received response from OpenAI ({len(response_text)} chars)")
            return response_text
        except Exception as e:
            logger.error(f"API call failed: {e}")
            raise
    
    try:
        response_text = exponential_backoff_retry(call_api)
        result = _extract_json_from_response(response_text)
        return NormalizedTarget(**result)
    except Exception as e:
        logger.error(f"Failed to normalize target: {e}")
        # Fallback to basic extraction
        return NormalizedTarget(
            target_products_services=[business_description[:100]],
            target_customer_segments=["Various industries"],
            canonical_sic_names=[primary_industry] if primary_industry else [],
            keywords=[]
        )


def extract_candidate_fields(
    company_name: str,
    text_snippets: List[str],
    source_urls: List[str],
    model: str = DEFAULT_MODEL
) -> CandidateExtraction:
    """
    Extract structured company data from raw text snippets using OpenAI LLM.
    
    This function processes text gathered from company websites, Wikipedia, and
    other sources to extract structured fields. The LLM is constrained to only
    use information present in the provided snippets and must output valid JSON.
    
    Args:
        company_name: Name of the candidate company
        text_snippets: List of text snippets from various sources (website, Wikipedia, etc.)
        source_urls: List of URLs where the text was collected
        model: OpenAI model to use (default: gpt-5)
        
    Returns:
        CandidateExtraction object containing:
        - name, url, exchange, ticker
        - business_activity: Summary of main offerings
        - customer_segment: Who they sell to
        - sic_industry: SIC industry name(s) if derivable
        - evidence_urls: Top 3 source URLs used
        
    Note:
        If extraction fails, returns a minimal CandidateExtraction with
        "Information not available" for missing fields.
    """
    combined_text = "\n\n---\n\n".join(text_snippets[:5])  # Limit to 5 snippets
    evidence_urls = source_urls[:3]  # Top 3 URLs
    
    prompt = f"""You are extracting company information from provided text snippets.

Company Name: {company_name}

Text Snippets (from company website, Wikipedia, SEC filings, etc.):
{combined_text}

Source URLs:
{', '.join(evidence_urls)}

Extract the following fields. If a field cannot be determined from the snippets, use null or "unknown":
- name: Company name
- url: Company website URL (if found in snippets or use first source URL)
- exchange: Stock exchange (NYSE, NASDAQ, AMEX, OTC, etc.)
- ticker: Stock ticker symbol
- business_activity: Tight summary of main products/services (2-3 sentences)
- customer_segment: Who they sell to, industries/sectors (1-2 sentences)
- sic_industry: SIC industry name(s) if derivable, else null
- evidence_urls: List of the 3 most relevant source URLs

IMPORTANT:
- Only use information present in the snippets
- Do not invent or infer facts not supported by the text
- If exchange/ticker is unclear, use null
- Be precise and factual

Output ONLY valid JSON in this exact format:
{{
    "name": "Company Name",
    "url": "https://...",
    "exchange": "NYSE" or null,
    "ticker": "SYMBOL" or null,
    "business_activity": "Description...",
    "customer_segment": "Description...",
    "sic_industry": "SIC Name" or null,
    "evidence_urls": ["url1", "url2", "url3"]
}}

Do not include any text outside the JSON object."""

    def call_api():
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.2
        )
        return response.choices[0].message.content
    
    try:
        response_text = exponential_backoff_retry(call_api)
        result = _extract_json_from_response(response_text)
        
        # Ensure evidence_urls is set
        if "evidence_urls" not in result or not result["evidence_urls"]:
            result["evidence_urls"] = evidence_urls
        
        # Ensure url is set
        if not result.get("url") and evidence_urls:
            result["url"] = evidence_urls[0]
        
        # Ensure required string fields are not None
        if not result.get("business_activity") or result.get("business_activity") is None:
            result["business_activity"] = "Information not available"
        if not result.get("customer_segment") or result.get("customer_segment") is None:
            result["customer_segment"] = "Information not available"
        
        return CandidateExtraction(**result)
    except Exception as e:
        logger.error(f"Failed to extract fields for {company_name}: {e}")
        # Return minimal extraction
        return CandidateExtraction(
            name=company_name,
            url=evidence_urls[0] if evidence_urls else None,
            exchange=None,
            ticker=None,
            business_activity="Information not available",
            customer_segment="Information not available",
            sic_industry=None,
            evidence_urls=evidence_urls
        )


def validate_candidate(
    target_products: List[str],
    target_segments: List[str],
    candidate: CandidateExtraction,
    model: str = DEFAULT_MODEL
) -> ValidationCheck:
    """
    Validate if candidate is a plausible comparable using OpenAI LLM.
    
    This function performs a cross-check to ensure the candidate company is
    actually comparable to the target. It compares products/services and
    customer segments to determine plausibility.
    
    Args:
        target_products: List of target company products/services (from normalization)
        target_segments: List of target company customer segments (from normalization)
        candidate: Extracted candidate company data
        model: OpenAI model to use (default: gpt-5)
        
    Returns:
        ValidationCheck object containing:
        - is_plausible: Boolean indicating if candidate is a valid comparable
        - reason: Brief explanation of the validation decision
        - failure_type: Type of failure if not plausible (different_products,
          different_segments, insufficient_info, or None)
        
    Note:
        If validation fails due to API error, defaults to is_plausible=True
        as a failsafe to avoid false negatives.
    """
    target_products_str = "\n".join([f"- {p}" for p in target_products])
    target_segments_str = "\n".join([f"- {s}" for s in target_segments])
    
    prompt = f"""You are validating if a candidate company is a plausible comparable.

TARGET COMPANY:
Products/Services:
{target_products_str}

Customer Segments:
{target_segments_str}

CANDIDATE COMPANY:
Name: {candidate.name}
Business Activity: {candidate.business_activity}
Customer Segment: {candidate.customer_segment}
SIC Industry: {candidate.sic_industry or "Not specified"}

Determine if this candidate is a plausible comparable based on:
1. Product/Service similarity - do they offer similar solutions?
2. Customer segment similarity - do they serve similar customers/industries?
3. Industry overlap - are they in related industries?

Output ONLY valid JSON:
{{
    "is_plausible": true or false,
    "reason": "Brief explanation (1-2 sentences)",
    "failure_type": "different_products" or "different_segments" or "insufficient_info" or null
}}

failure_type should be:
- "different_products" if products/services are too different
- "different_segments" if customer segments don't overlap
- "insufficient_info" if we can't determine from available data
- null if is_plausible is true

Do not include any text outside the JSON object."""

    def call_api():
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that outputs only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            temperature=0.3
        )
        return response.choices[0].message.content
    
    try:
        response_text = exponential_backoff_retry(call_api)
        result = _extract_json_from_response(response_text)
        
        # Parse failure_type
        failure_type_str = result.get("failure_type")
        failure_type = None
        if failure_type_str:
            try:
                failure_type = FailureType(failure_type_str)
            except ValueError:
                failure_type = FailureType.OTHER
        
        return ValidationCheck(
            is_plausible=result.get("is_plausible", False),
            reason=result.get("reason", "No reason provided"),
            failure_type=failure_type
        )
    except Exception as e:
        logger.error(f"Failed to validate candidate {candidate.name}: {e}")
        # Default to plausible if validation fails (failsafe)
        return ValidationCheck(
            is_plausible=True,
            reason="Validation check failed, defaulting to plausible",
            failure_type=None
        )
