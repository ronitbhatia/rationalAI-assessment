"""Pydantic models for inputs, outputs, and intermediate data structures."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class TargetInput(BaseModel):
    """Input schema for target company."""
    name: str
    business_description: str
    url: Optional[str] = None
    primary_industry_classification: Optional[str] = None


class NormalizedTarget(BaseModel):
    """Normalized target profile from LLM."""
    target_products_services: List[str] = Field(
        description="5-12 bullet points of products/services"
    )
    target_customer_segments: List[str] = Field(
        description="5-10 bullet points of customer segments"
    )
    canonical_sic_names: List[str] = Field(
        default_factory=list,
        description="Canonical SIC industry names"
    )
    keywords: List[str] = Field(
        default_factory=list,
        description="Search keywords for discovery"
    )


class FailureType(str, Enum):
    """Types of validation failures."""
    DIFFERENT_PRODUCTS = "different_products"
    DIFFERENT_SEGMENTS = "different_segments"
    INSUFFICIENT_INFO = "insufficient_info"
    OTHER = "other"


class CandidateExtraction(BaseModel):
    """Extracted fields for a candidate company."""
    name: str
    url: Optional[str] = None
    exchange: Optional[str] = None
    ticker: Optional[str] = None
    business_activity: str = Field(
        description="Tight summary of main offerings"
    )
    customer_segment: str = Field(
        description="Who they sell to, industries/sectors"
    )
    sic_industry: Optional[str] = Field(
        default=None,
        description="SIC industry name(s) if derivable"
    )
    evidence_urls: List[str] = Field(
        default_factory=list,
        description="Top 3 source URLs used"
    )


class ValidationCheck(BaseModel):
    """LLM validation check result."""
    is_plausible: bool
    reason: str
    failure_type: Optional[FailureType] = None


class ComparableCompany(BaseModel):
    """Final comparable company with scores."""
    name: str
    url: Optional[str] = None
    exchange: Optional[str] = None
    ticker: Optional[str] = None
    business_activity: str
    customer_segment: str
    sic_industry: Optional[str] = None
    validation_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Combined similarity score"
    )
    service_similarity: float = Field(
        ge=0.0,
        le=1.0
    )
    segment_similarity: float = Field(
        ge=0.0,
        le=1.0
    )
    is_plausible: bool
    evidence_urls: List[str] = Field(default_factory=list)


class ProvenanceRecord(BaseModel):
    """Provenance log entry."""
    candidate_name: str
    field: str
    value: Any
    source_url: str


class CandidateRawData(BaseModel):
    """Raw scraped data for a candidate."""
    name: str
    url: Optional[str] = None
    text_snippets: List[str] = Field(
        default_factory=list,
        description="Scraped text content from various sources"
    )
    source_urls: List[str] = Field(
        default_factory=list,
        description="URLs where data was collected"
    )
    exchange: Optional[str] = None
    ticker: Optional[str] = None




