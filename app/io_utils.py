"""File I/O utilities for saving CSV/Parquet and provenance logging."""

import json
import logging
from pathlib import Path
from typing import List
import pandas as pd

from app.schemas import ComparableCompany, ProvenanceRecord

logger = logging.getLogger(__name__)


def save_comparables(
    comparables: List[ComparableCompany],
    output_path: str
) -> None:
    """
    Save comparables to CSV or Parquet file.
    
    Args:
        comparables: List of comparable companies
        output_path: Output file path (.csv or .parquet)
    """
    if not comparables:
        logger.warning("No comparables to save")
        return
    
    # Convert to DataFrame
    data = []
    for comp in comparables:
        data.append({
            'name': comp.name,
            'url': comp.url or '',
            'exchange': comp.exchange or '',
            'ticker': comp.ticker or '',
            'business_activity': comp.business_activity,
            'customer_segment': comp.customer_segment,
            'sic_industry': comp.sic_industry or '',
            'validation_score': comp.validation_score,
            'service_similarity': comp.service_similarity,
            'segment_similarity': comp.segment_similarity,
            'is_plausible': comp.is_plausible,
            'evidence_urls': '; '.join(comp.evidence_urls) if comp.evidence_urls else ''
        })
    
    df = pd.DataFrame(data)
    
    # Save based on file extension
    output_path_obj = Path(output_path)
    if output_path_obj.suffix.lower() == '.parquet':
        df.to_parquet(output_path, index=False)
        logger.info(f"Saved {len(comparables)} comparables to {output_path} (Parquet)")
    elif output_path_obj.suffix.lower() == '.csv':
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(comparables)} comparables to {output_path} (CSV)")
    else:
        # Default to CSV
        output_path = str(output_path_obj.with_suffix('.csv'))
        df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(comparables)} comparables to {output_path} (CSV)")


def save_provenance(
    comparables: List[ComparableCompany],
    provenance_path: str
) -> None:
    """
    Save provenance log to JSONL file.
    
    Args:
        comparables: List of comparable companies
        provenance_path: Path to save provenance log
    """
    records = []
    
    for comp in comparables:
        # Add records for each field
        fields = {
            'name': comp.name,
            'url': comp.url,
            'exchange': comp.exchange,
            'ticker': comp.ticker,
            'business_activity': comp.business_activity,
            'customer_segment': comp.customer_segment,
            'sic_industry': comp.sic_industry,
        }
        
        for field, value in fields.items():
            if value:  # Only log non-empty fields
                # Use first evidence URL as source, or default
                source_url = comp.evidence_urls[0] if comp.evidence_urls else ''
                records.append({
                    'candidate_name': comp.name,
                    'field': field,
                    'value': str(value),
                    'source_url': source_url
                })
    
    # Save as JSONL
    with open(provenance_path, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    
    logger.info(f"Saved {len(records)} provenance records to {provenance_path}")


def print_summary(comparables: List[ComparableCompany]) -> None:
    """
    Print a console summary of comparables.
    
    Args:
        comparables: List of comparable companies
    """
    if not comparables:
        print("No comparables found.")
        return
    
    print(f"\n{'='*80}")
    print(f"Found {len(comparables)} Comparable Companies")
    print(f"{'='*80}\n")
    
    for i, comp in enumerate(comparables, 1):
        print(f"{i}. {comp.name}")
        if comp.ticker:
            print(f"   Ticker: {comp.exchange}:{comp.ticker}" if comp.exchange else f"   Ticker: {comp.ticker}")
        else:
            print(f"   Exchange/Ticker: Not available")
        print(f"   Validation Score: {comp.validation_score:.3f}")
        print(f"   Service Similarity: {comp.service_similarity:.3f}")
        print(f"   Segment Similarity: {comp.segment_similarity:.3f}")
        if comp.url:
            print(f"   URL: {comp.url}")
        print()




