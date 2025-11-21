# Output Files for Huron Consulting Group Analysis

This directory contains the complete output from running the comparable company finder for **Huron Consulting Group Inc.**

## Files Included

### 1. `huron_comparables.csv`
**Format**: CSV (Comma-Separated Values)  
**Size**: ~2.8 KB  
**Description**: Human-readable spreadsheet containing 8 comparable companies with all extracted fields and similarity scores.

**Quick View**:
- Open in Excel, Google Sheets, or any text editor
- Contains columns: name, url, exchange, ticker, business_activity, customer_segment, sic_industry, validation_score, service_similarity, segment_similarity, is_plausible, evidence_urls
- Companies are sorted by validation_score (highest first)

### 2. `huron_comparables.parquet`
**Format**: Parquet (Binary columnar format)  
**Size**: ~9.7 KB  
**Description**: Same data as CSV but in efficient binary format for data analysis tools.

**Usage**:
```python
import pandas as pd
df = pd.read_parquet('huron_comparables.parquet')
```

### 3. `huron_comparables.provenance.jsonl`
**Format**: JSONL (JSON Lines)  
**Size**: ~1.5 KB  
**Description**: Line-delimited JSON log tracking the source URLs for each extracted field.

**Format**:
```json
{"candidate_name": "Accenture plc", "field": "business_activity", "value": "...", "source_url": "https://www.accenture.com", "timestamp": "2024-11-21T09:58:00"}
```

### 4. `RESULTS_SUMMARY.md`
**Format**: Markdown  
**Description**: Detailed analysis document explaining:
- Summary of findings
- Top 8 comparables with explanations
- Validation methodology
- Notes and limitations

### 5. `HOW_TO_READ_OUTPUT.md`
**Format**: Markdown  
**Description**: Comprehensive guide on how to:
- Read and interpret the CSV/Parquet files
- Understand validation scores
- Analyze the results using Python, Excel, or command-line tools
- Read the provenance log

## Quick Summary

**Total Comparables Found**: 8

**Top 3 Companies**:
1. **Accenture plc** (NYSE: ACN) - Validation Score: 0.72
2. **Deloitte Consulting LLP** - Validation Score: 0.68
3. **IBM Global Business Services** (NYSE: IBM) - Validation Score: 0.65

**Average Validation Score**: 0.60

**Public Companies**: 5 (Accenture, IBM, Cognizant, Perficient, EPAM)  
**Private Companies**: 3 (Deloitte, Guidehouse, Publicis Sapient)

## How to Use These Files

### For Quick Review
1. Open `huron_comparables.csv` in Excel or Google Sheets
2. Review `RESULTS_SUMMARY.md` for detailed analysis

### For Data Analysis
1. Use `huron_comparables.parquet` with pandas for efficient processing
2. See `HOW_TO_READ_OUTPUT.md` for code examples

### For Verification
1. Check `huron_comparables.provenance.jsonl` to see data sources
2. Verify evidence URLs to confirm data accuracy

## Validation Methodology

Each company was evaluated using:
- **Service Similarity** (60% weight): Jaccard + TF-IDF on products/services
- **Segment Similarity** (40% weight): Jaccard + TF-IDF on customer segments
- **Automated Checks**: Product overlap, segment overlap, public listing, negative filter
- **LLM Validation**: OpenAI API cross-check for plausibility

All 8 companies passed validation checks and have `is_plausible=True`.

## Notes

- Some companies (Deloitte, Guidehouse, Publicis Sapient) are private and show "N/A" for exchange/ticker
- Validation scores range from 0.50 to 0.72 (all above the 0.35 minimum threshold)
- All companies serve similar customer segments (healthcare, education, large enterprises)
- Evidence URLs show the primary sources used for data extraction

## Questions?

Refer to:
- `HOW_TO_READ_OUTPUT.md` for detailed usage instructions
- `RESULTS_SUMMARY.md` for analysis and methodology
- `README.md` for overall project documentation

