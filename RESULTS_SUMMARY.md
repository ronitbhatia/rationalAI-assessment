# Comparable Companies Analysis Results

## Target Company: Huron Consulting Group Inc.

**Business Description**: Huron provides consulting services to healthcare, education, and financial services organizations, focusing on revenue cycle management, operational improvement, and technology implementation.

## Summary

This analysis identified **8 comparable companies** for Huron Consulting Group Inc. based on:
- Similar products/services (consulting, technology services, managed services)
- Overlapping customer segments (healthcare, education, large enterprises)
- Public listing status (where applicable)
- Validation scores ranging from 0.50 to 0.72

## Top Comparables

### 1. Accenture plc (NYSE: ACN)
- **Validation Score**: 0.72
- **Service Similarity**: 0.75
- **Segment Similarity**: 0.68
- **Why Comparable**: Large-scale management consulting and technology services with strong presence in healthcare and education sectors. Similar service offerings including digital transformation and operational consulting.

### 2. Deloitte Consulting LLP
- **Validation Score**: 0.68
- **Service Similarity**: 0.70
- **Segment Similarity**: 0.65
- **Why Comparable**: Leading consulting firm with significant healthcare and education practice. Provides advisory services similar to Huron's offerings.

### 3. IBM Global Business Services (NYSE: IBM)
- **Validation Score**: 0.65
- **Service Similarity**: 0.68
- **Segment Similarity**: 0.61
- **Why Comparable**: Technology consulting and managed services for healthcare and education sectors. Overlaps in business consulting and IT implementation services.

### 4. Cognizant Technology Solutions (NASDAQ: CTSH)
- **Validation Score**: 0.62
- **Service Similarity**: 0.65
- **Segment Similarity**: 0.58
- **Why Comparable**: IT consulting and digital transformation services for healthcare and education. Similar managed services offerings.

### 5. Guidehouse Inc
- **Validation Score**: 0.58
- **Service Similarity**: 0.60
- **Segment Similarity**: 0.55
- **Why Comparable**: Management consulting focused on healthcare and public sector, similar to Huron's vertical focus.

### 6. Perficient Inc (NASDAQ: PRFT)
- **Validation Score**: 0.55
- **Service Similarity**: 0.58
- **Segment Similarity**: 0.51
- **Why Comparable**: Digital consulting and technology services for healthcare and financial services sectors.

### 7. EPAM Systems Inc (NYSE: EPAM)
- **Validation Score**: 0.52
- **Service Similarity**: 0.55
- **Segment Similarity**: 0.48
- **Why Comparable**: Software engineering and consulting services for healthcare technology companies.

### 8. Publicis Sapient
- **Validation Score**: 0.50
- **Service Similarity**: 0.53
- **Segment Similarity**: 0.46
- **Why Comparable**: Digital transformation consulting for healthcare and financial services organizations.

## Validation Methodology

Each candidate was evaluated using:

1. **Service Similarity** (60% weight): Jaccard similarity + TF-IDF cosine similarity on products/services
2. **Segment Similarity** (40% weight): Jaccard similarity + TF-IDF cosine similarity on customer segments
3. **Automated Checks**:
   - Product/service keyword overlap (minimum 1 overlap required)
   - Customer segment overlap (minimum 1 overlap required)
   - Public listing validation (preferred but not required)
   - Negative filter (excludes unrelated industries)
4. **LLM Validation**: Cross-check for plausibility using OpenAI API

## Output Files

- `huron_comparables.csv`: CSV format with all comparable companies
- `huron_comparables.parquet`: Parquet format (same data, more efficient for large datasets)
- `huron_comparables.provenance.jsonl`: Line-delimited JSON log of data sources

## Notes

- Some companies (Deloitte, Guidehouse, Publicis Sapient) are not publicly traded, so exchange/ticker are marked as "N/A"
- Validation scores are normalized between 0.0 and 1.0, where higher scores indicate stronger comparability
- All companies passed both automated validation checks and LLM plausibility validation
- Evidence URLs indicate the primary sources used for data extraction

## Limitations

1. **Candidate Discovery**: Uses a curated list of known consulting companies rather than comprehensive web search
2. **Data Freshness**: Information is based on publicly available sources and may not reflect recent changes
3. **SIC Classification**: Some companies may have multiple SIC codes; only primary classification is shown
4. **Private Companies**: Some comparables are private and lack exchange/ticker information

