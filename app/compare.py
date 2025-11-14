"""
Similarity scoring and validation logic.

This module implements similarity calculations and validation checks to determine
if candidate companies are comparable to the target. It uses pure Python algorithms
(Jaccard similarity and TF-IDF) without external ML libraries.
"""

import re
import logging
from typing import List, Set
from collections import Counter
import math

from app.schemas import NormalizedTarget, CandidateExtraction, ComparableCompany

logger = logging.getLogger(__name__)


def extract_noun_phrases(text: str) -> Set[str]:
    """
    Extract noun phrases and key terms from text for similarity comparison.
    
    This function extracts unigrams (single words), bigrams (2-word phrases),
    and trigrams (3-word phrases) from the input text. Short words (3 chars or less)
    are filtered out to focus on meaningful terms.
    
    Args:
        text: Input text to extract terms from
        
    Returns:
        Set of normalized key terms (lowercase, punctuation removed)
        
    Example:
        Input: "Enterprise resource planning software"
        Output: {"enterprise", "resource", "planning", "software",
                 "enterprise resource", "resource planning", "planning software",
                 "enterprise resource planning", "resource planning software"}
    """
    if not text:
        return set()
    
    # Normalize text: lowercase and remove punctuation (except hyphens)
    text = text.lower()
    text = re.sub(r'[^\w\s-]', ' ', text)
    
    # Split into words
    words = text.split()
    
    terms = set()
    
    # Extract unigrams (single words) - filter out short words
    for word in words:
        if len(word) > 3:  # Filter short words like "the", "and", etc.
            terms.add(word)
    
    # Extract bigrams (2-word phrases)
    for i in range(len(words) - 1):
        bigram = f"{words[i]} {words[i+1]}"
        terms.add(bigram)
    
    # Extract trigrams (3-word phrases)
    for i in range(len(words) - 2):
        trigram = f"{words[i]} {words[i+1]} {words[i+2]}"
        terms.add(trigram)
    
    return terms


def compute_tfidf_similarity(
    text1: str,
    text2: str,
    all_documents: List[str]
) -> float:
    """
    Compute TF-IDF cosine similarity between two texts.
    
    This function calculates term frequency-inverse document frequency (TF-IDF)
    vectors for both texts and computes their cosine similarity. This measures
    how similar the texts are based on the importance of shared terms.
    
    Args:
        text1: First text to compare
        text2: Second text to compare
        all_documents: List of all documents in the corpus for IDF calculation
        
    Returns:
        Cosine similarity score between 0.0 and 1.0, where:
        - 1.0 = identical texts
        - 0.0 = no shared terms
    """
    if not text1 or not text2:
        return 0.0
    
    # Extract terms
    terms1 = extract_noun_phrases(text1)
    terms2 = extract_noun_phrases(text2)
    
    if not terms1 or not terms2:
        return 0.0
    
    # Compute term frequencies
    tf1 = Counter(text1.lower().split())
    tf2 = Counter(text2.lower().split())
    
    # Compute IDF for all terms
    all_terms = terms1 | terms2
    idf = {}
    N = len(all_documents) + 2  # Include our two texts
    
    for term in all_terms:
        doc_count = sum(1 for doc in all_documents if term in doc.lower())
        if doc_count > 0:
            idf[term] = math.log(N / (doc_count + 1))
        else:
            idf[term] = 0.0
    
    # Compute TF-IDF vectors
    vec1 = {}
    vec2 = {}
    
    for term in all_terms:
        vec1[term] = tf1.get(term, 0) * idf.get(term, 0)
        vec2[term] = tf2.get(term, 0) * idf.get(term, 0)
    
    # Compute cosine similarity
    dot_product = sum(vec1.get(term, 0) * vec2.get(term, 0) for term in all_terms)
    norm1 = math.sqrt(sum(v * v for v in vec1.values()))
    norm2 = math.sqrt(sum(v * v for v in vec2.values()))
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return dot_product / (norm1 * norm2)


def jaccard_similarity(set1: Set[str], set2: Set[str]) -> float:
    """
    Compute Jaccard similarity coefficient between two sets.
    
    Jaccard similarity measures the overlap between two sets as the size of
    the intersection divided by the size of the union. This is useful for
    comparing sets of terms extracted from text.
    
    Args:
        set1: First set of terms
        set2: Second set of terms
        
    Returns:
        Jaccard similarity between 0.0 and 1.0, where:
        - 1.0 = identical sets
        - 0.0 = no overlap
    """
    if not set1 or not set2:
        return 0.0
    
    intersection = len(set1 & set2)
    union = len(set1 | set2)
    
    if union == 0:
        return 0.0
    
    return intersection / union


def compute_service_similarity(
    target: NormalizedTarget,
    candidate: CandidateExtraction
) -> float:
    """
    Compute similarity score for products/services.
    
    Args:
        target: Normalized target profile
        candidate: Candidate extraction
        
    Returns:
        Similarity score between 0 and 1
    """
    # Combine target products/services
    target_text = " ".join(target.target_products_services)
    candidate_text = candidate.business_activity
    
    # Extract noun phrases
    target_phrases = extract_noun_phrases(target_text)
    candidate_phrases = extract_noun_phrases(candidate_text)
    
    # Jaccard similarity on phrases
    jaccard = jaccard_similarity(target_phrases, candidate_phrases)
    
    # Simple TF-IDF (using both texts as corpus)
    tfidf = compute_tfidf_similarity(
        target_text,
        candidate_text,
        [target_text, candidate_text]
    )
    
    # Weighted combination
    similarity = 0.6 * jaccard + 0.4 * tfidf
    
    return min(1.0, max(0.0, similarity))


def compute_segment_similarity(
    target: NormalizedTarget,
    candidate: CandidateExtraction
) -> float:
    """
    Compute similarity score for customer segments.
    
    Args:
        target: Normalized target profile
        candidate: Candidate extraction
        
    Returns:
        Similarity score between 0 and 1
    """
    # Combine target customer segments
    target_text = " ".join(target.target_customer_segments)
    candidate_text = candidate.customer_segment
    
    # Extract noun phrases
    target_phrases = extract_noun_phrases(target_text)
    candidate_phrases = extract_noun_phrases(candidate_text)
    
    # Jaccard similarity
    jaccard = jaccard_similarity(target_phrases, candidate_phrases)
    
    # TF-IDF similarity
    tfidf = compute_tfidf_similarity(
        target_text,
        candidate_text,
        [target_text, candidate_text]
    )
    
    # Weighted combination
    similarity = 0.6 * jaccard + 0.4 * tfidf
    
    return min(1.0, max(0.0, similarity))


def validate_product_overlap(
    target: NormalizedTarget,
    candidate: CandidateExtraction,
    min_overlaps: int = 2
) -> bool:
    """
    Check if at least N key service keywords overlap.
    
    Args:
        target: Normalized target profile
        candidate: Candidate extraction
        min_overlaps: Minimum number of overlapping keywords
        
    Returns:
        True if overlap threshold is met
    """
    # Extract key terms from target products
    target_terms = set()
    for product in target.target_products_services:
        # Extract meaningful terms (2-3 words)
        words = product.lower().split()
        # Add bigrams and trigrams
        for i in range(len(words) - 1):
            target_terms.add(f"{words[i]} {words[i+1]}")
        for i in range(len(words) - 2):
            target_terms.add(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    # Extract terms from candidate
    candidate_terms = extract_noun_phrases(candidate.business_activity)
    
    # Count overlaps
    overlaps = len(target_terms & candidate_terms)
    
    return overlaps >= min_overlaps


def validate_segment_overlap(
    target: NormalizedTarget,
    candidate: CandidateExtraction,
    min_overlaps: int = 1
) -> bool:
    """
    Check if at least N customer segment/vertical keywords overlap.
    
    Args:
        target: Normalized target profile
        candidate: Candidate extraction
        min_overlaps: Minimum number of overlapping keywords
        
    Returns:
        True if overlap threshold is met
    """
    # Extract key terms from target segments
    target_terms = set()
    for segment in target.target_customer_segments:
        words = segment.lower().split()
        for i in range(len(words) - 1):
            target_terms.add(f"{words[i]} {words[i+1]}")
        for i in range(len(words) - 2):
            target_terms.add(f"{words[i]} {words[i+1]} {words[i+2]}")
    
    # Extract terms from candidate
    candidate_terms = extract_noun_phrases(candidate.customer_segment)
    
    # Count overlaps
    overlaps = len(target_terms & candidate_terms)
    
    return overlaps >= min_overlaps


def validate_public_listing(candidate: CandidateExtraction) -> bool:
    """
    Validate that candidate has exchange and ticker.
    
    Args:
        candidate: Candidate extraction
        
    Returns:
        True if exchange and ticker are present
    """
    return bool(candidate.exchange and candidate.ticker)


def validate_not_unrelated(
    target: NormalizedTarget,
    candidate: CandidateExtraction
) -> bool:
    """
    Negative filter: exclude firms primarily focused on unrelated areas.
    
    Args:
        target: Normalized target profile
        candidate: Candidate extraction
        
    Returns:
        True if candidate is not clearly unrelated
    """
    # Check for unrelated keywords
    unrelated_keywords = [
        'manufacturing', 'hardware vendor', 'pure manufacturer',
        'equipment supplier', 'physical product'
    ]
    
    candidate_text = (candidate.business_activity + " " + candidate.customer_segment).lower()
    
    # If candidate is primarily unrelated, exclude
    unrelated_count = sum(1 for kw in unrelated_keywords if kw in candidate_text)
    
    # Only exclude if it's clearly unrelated and has no consulting/service overlap
    if unrelated_count >= 2:
        target_text = " ".join(target.target_products_services).lower()
        consulting_keywords = ['consulting', 'services', 'advisory', 'managed services', 'software']
        has_consulting_overlap = any(kw in candidate_text for kw in consulting_keywords)
        
        if not has_consulting_overlap:
            return False
    
    return True


def compute_validation_score(
    target: NormalizedTarget,
    candidate: CandidateExtraction
) -> float:
    """
    Compute combined validation score.
    
    Args:
        target: Normalized target profile
        candidate: Candidate extraction
        
    Returns:
        Validation score between 0 and 1
    """
    service_sim = compute_service_similarity(target, candidate)
    segment_sim = compute_segment_similarity(target, candidate)
    
    # Weighted combination: 60% service, 40% segment
    validation_score = 0.6 * service_sim + 0.4 * segment_sim
    
    return validation_score


def create_comparable(
    candidate: CandidateExtraction,
    target: NormalizedTarget,
    validation_check,
    validation_score: float
) -> ComparableCompany:
    """
    Create a ComparableCompany from extracted data and scores.
    
    Args:
        candidate: Extracted candidate data
        target: Normalized target profile
        validation_check: LLM validation check result
        validation_score: Computed validation score
        
    Returns:
        ComparableCompany object
    """
    service_sim = compute_service_similarity(target, candidate)
    segment_sim = compute_segment_similarity(target, candidate)
    
    return ComparableCompany(
        name=candidate.name,
        url=candidate.url,
        exchange=candidate.exchange,
        ticker=candidate.ticker,
        business_activity=candidate.business_activity,
        customer_segment=candidate.customer_segment,
        sic_industry=candidate.sic_industry,
        validation_score=validation_score,
        service_similarity=service_sim,
        segment_similarity=segment_sim,
        is_plausible=validation_check.is_plausible,
        evidence_urls=candidate.evidence_urls
    )




