"""Basic smoke tests for the comparable company finder."""

import pytest
import os
from pathlib import Path

from app.schemas import TargetInput
from app.pipeline import run_pipeline
from app.extraction import normalize_target
from app.compare import compute_service_similarity, compute_segment_similarity


# Skip tests if OpenAI API key is not set
pytestmark = pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OpenAI API key not set"
)


@pytest.fixture
def huron_target():
    """Fixture for Huron Consulting Group target."""
    return TargetInput(
        name="Huron Consulting Group Inc.",
        url="http://www.huronconsultinggroup.com/",
        business_description="""Huron Consulting Group Inc. provides consultancy and managed services in the United States and internationally. It operates through three segments: Healthcare, Education, and Commercial. The company offers financial and operational performance improvement consulting services; digital offerings; spanning technology and analytic-related services, including enterprise health record, enterprise resource planning, enterprise performance management, customer relationship management, data management, artificial intelligence and automation, technology managed services, and a portfolio of software products; organizational transformation; revenue cycle managed services and outsourcing; financial and capital advisory consulting; and strategy and innovation consulting. It also provides digital offerings; spanning technology and analytic-related services; technology managed services; research-focused consulting; managed services; and global philanthropy consulting services, as well as Huron Research product suite, a software suite designed to facilitate and enhance research administration service delivery and compliance. In addition, the company offers digital services, software products, financial capital advisory services, and Commercial consulting.""",
        primary_industry_classification="Research and Consulting Services"
    )


@pytest.fixture
def sample_companies():
    """Fixture with sample companies for testing."""
    return [
        TargetInput(
            name="Accenture",
            url="https://www.accenture.com",
            business_description="Accenture is a global professional services company that provides strategy, consulting, digital, technology and operations services.",
            primary_industry_classification="Professional Services"
        ),
        TargetInput(
            name="IBM Global Services",
            url="https://www.ibm.com/services",
            business_description="IBM offers consulting, technology, and business services to help clients transform their operations.",
            primary_industry_classification="Information Technology Services"
        ),
    ]


def test_normalize_target(huron_target):
    """Test target normalization."""
    normalized = normalize_target(
        name=huron_target.name,
        business_description=huron_target.business_description,
        url=huron_target.url,
        primary_industry=huron_target.primary_industry_classification
    )
    
    assert len(normalized.target_products_services) >= 5
    assert len(normalized.target_customer_segments) >= 5
    assert isinstance(normalized.keywords, list)


def test_pipeline_smoke_test(huron_target):
    """Smoke test: pipeline should run without errors."""
    # Run with very small limits for testing
    comparables = run_pipeline(
        target=huron_target,
        max_candidates=5,
        min_score=0.2,
        max_final=3
    )
    
    # Should return a list (might be empty if no matches found)
    assert isinstance(comparables, list)
    assert len(comparables) <= 3


def test_pipeline_output_format(huron_target):
    """Test that pipeline output has correct format."""
    comparables = run_pipeline(
        target=huron_target,
        max_candidates=10,
        min_score=0.25,
        max_final=5
    )
    
    if comparables:
        comp = comparables[0]
        # Check required fields
        assert comp.name
        assert comp.business_activity
        assert comp.customer_segment
        assert comp.validation_score >= 0.0
        assert comp.validation_score <= 1.0
        assert comp.service_similarity >= 0.0
        assert comp.segment_similarity >= 0.0


def test_similarity_computation(huron_target):
    """Test similarity computation functions."""
    from app.schemas import CandidateExtraction
    
    normalized = normalize_target(
        name=huron_target.name,
        business_description=huron_target.business_description,
        url=huron_target.url,
        primary_industry=huron_target.primary_industry_classification
    )
    
    # Create a test candidate
    candidate = CandidateExtraction(
        name="Test Consulting",
        business_activity="Provides consulting services for healthcare and education sectors",
        customer_segment="Serves hospitals, universities, and research institutions",
        evidence_urls=["https://example.com"]
    )
    
    service_sim = compute_service_similarity(normalized, candidate)
    segment_sim = compute_segment_similarity(normalized, candidate)
    
    assert 0.0 <= service_sim <= 1.0
    assert 0.0 <= segment_sim <= 1.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])




