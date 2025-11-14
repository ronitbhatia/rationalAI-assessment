# RationalAI - Comparable Company Finder

A production-quality Python tool for investment analysts to identify publicly traded comparable companies for any target company. The tool uses LLM-based extraction and similarity scoring to find companies that offer similar products/services and serve similar customer segments.

## Features

- Normalized Target Profiling: Uses LLM to extract key products/services and customer segments from target company description
- Candidate Discovery: Discovers publicly traded companies through web search and known sources
- Field Extraction: Extracts structured company data (name, ticker, exchange, business activity, customer segments, SIC industry) using LLM
- Similarity Scoring: Computes product/service and customer segment similarity using Jaccard and TF-IDF metrics
- Validation: Multiple validation checks including product overlap, segment overlap, public listing verification, and LLM-based plausibility checks
- Provenance Logging: Tracks data sources for each extracted field
- Flexible Output: Supports both CSV and Parquet output formats

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up environment variables:
```bash
cp env.example .env
# Edit .env and add your OPENAI_API_KEY
```

Important: You need an OpenAI API key with credits. GPT Plus subscription does not include API credits - you must add a payment method and purchase credits separately at https://platform.openai.com/account/billing

## Usage

### Command-Line Interface

The CLI accepts either a JSON file or individual command-line flags:

#### Using JSON file:
```bash
python -m app.cli \
  --json example_target.json \
  --out comparables.parquet \
  --max-candidates 40 \
  --min-score 0.35
```

#### Using command-line flags:
```bash
python -m app.cli \
  --name "Huron Consulting Group Inc." \
  --url "http://www.huronconsultinggroup.com/" \
  --business-description "Huron Consulting Group Inc. provides consultancy and managed services..." \
  --primary-industry "Research and Consulting Services" \
  --out huron_comps.parquet \
  --max-candidates 40 \
  --min-score 0.35
```

### JSON Input Format

```json
{
  "name": "Company Name",
  "business_description": "Detailed business description...",
  "url": "https://company.com",
  "primary_industry_classification": "SIC Industry Name"
}
```

### Command-Line Options

- `--json`: Path to JSON file with target company data
- `--name`: Target company name (required if not using --json)
- `--url`: Target company URL
- `--business-description`: Business description (required if using --name)
- `--primary-industry`: Primary industry classification (SIC name)
- `--out`: Output file path (.csv or .parquet) [required]
- `--max-candidates`: Maximum number of candidates to discover (default: 40)
- `--min-score`: Minimum validation score threshold (default: 0.35)
- `--model`: OpenAI model to use (default: gpt-5)
- `--max-final`: Maximum number of final comparables to return (default: 10)
- `--debug`: Enable debug logging

## How It Works

### 1. Candidate Discovery

The tool builds search queries from normalized target profile:
- Combines products/services with customer segments
- Adds industry-based keywords
- Searches Wikipedia, company sites, and known financial sources

Note: This implementation uses a curated list of publicly traded companies for demonstration purposes. The list focuses on consulting, technology, healthcare, and education sectors. In production, this would integrate with Bing Search API, Google Custom Search, or similar services for comprehensive candidate discovery across all industries.

### 2. LLM Extraction

For each candidate, the tool:
- Fetches text from company website, Wikipedia, and other sources
- Uses OpenAI API with strict JSON schema to extract:
  - Company name, URL, exchange, ticker
  - Business activity (summary of offerings)
  - Customer segment (who they sell to)
  - SIC industry (if derivable)
  - Evidence URLs (sources used)

LLM Constraints:
- Uses JSON mode for structured output
- System prompt explicitly forbids inventing facts
- Only uses information present in provided snippets
- Returns null/unknown for unclear fields

### 3. Validation Checks

The tool implements multiple validation checks:

#### a. Product/Service Overlap Check
- Requires at least 2 key service keywords to overlap
- Extracts noun phrases and compares against target products/services
- Example: "ERP implementation", "revenue cycle", "managed services"

#### b. Customer Segment/Vertical Check
- Requires at least 1 overlapping vertical or buyer type
- Compares customer segments (e.g., hospitals, universities, Fortune 1000)
- Validates that companies serve similar markets

#### c. Public Listing Check
- Confirms exchange and ticker are present
- Validates against source snippets or Wikipedia/SEC lookup
- Discards candidates without public listing information (unless score is very high)

#### d. Negative Filter
- Excludes firms primarily focused on unrelated areas
- Filters out pure manufacturers or hardware vendors
- Only excludes if no consulting/service overlap exists

### 4. Similarity Scoring

For each candidate:
- Service Similarity: Jaccard similarity on noun phrases + TF-IDF cosine on key terms (60% weight)
- Segment Similarity: Same method on customer/industry terms (40% weight)
- Validation Score: `0.6 * service_similarity + 0.4 * segment_similarity`
- LLM Cross-Check: Binary validation with reason and failure type

Final candidates must:
- Have validation_score >= min_score (default 0.35)
- Pass automated validation checks OR LLM validation
- Have validation_score >= 0.7 (failsafe for high-scoring candidates)

### 5. Selection and Ranking

Candidates are ranked by:
1. Validation score (primary)
2. Number of evidence URLs (completeness)
3. Field completeness (SIC industry, exchange/ticker)

Top 3-10 comparables are returned based on `--max-final` parameter.

## Output Format

### Comparables File (CSV/Parquet)

Columns:
- `name`: Company name
- `url`: Company website URL
- `exchange`: Stock exchange (NYSE, NASDAQ, etc.)
- `ticker`: Stock ticker symbol
- `business_activity`: Summary of main offerings
- `customer_segment`: Customer segments/industries served
- `sic_industry`: SIC industry name(s)
- `validation_score`: Combined similarity score (0-1)
- `service_similarity`: Product/service similarity (0-1)
- `segment_similarity`: Customer segment similarity (0-1)
- `is_plausible`: LLM validation result (true/false)
- `evidence_urls`: Semicolon-separated list of source URLs

### Provenance Log (JSONL)

Each line contains:
```json
{
  "candidate_name": "Company Name",
  "field": "field_name",
  "value": "field_value",
  "source_url": "https://source-url.com"
}
```

## Example: Huron Consulting Group

```bash
python -m app.cli \
  --json example_target.json \
  --out huron_comparables.parquet \
  --max-candidates 40 \
  --min-score 0.35
```

## Testing

Run smoke tests:
```bash
# Set OPENAI_API_KEY environment variable
export OPENAI_API_KEY=your_key_here

# Run tests
pytest tests/test_basic.py -v
```

## Known Limitations

1. Candidate Discovery: Uses a curated list of publicly traded companies rather than real-time web search. Best results for consulting, technology, healthcare, and education sectors. In production, would integrate with Bing Search API or Google Custom Search.

2. Region Coverage: Currently focuses on US-listed companies. International exchanges may not be fully supported.

3. SIC Mapping: SIC industry names may not always be derivable from source material. Some candidates may have null SIC industry.

4. Managed Services Ambiguity: "Managed services" can refer to different things (IT managed services vs. business process outsourcing). The tool attempts to distinguish based on context.

5. Rate Limits: OpenAI API rate limits may affect processing speed. The tool includes exponential backoff retry logic with 25-second delays between calls for free tier accounts.

6. JavaScript Sites: Some company websites rely heavily on JavaScript. The tool uses simple HTML parsing which may miss dynamic content.

7. Data Freshness: Company information may change over time. The tool uses current web data but doesn't track historical changes.

8. Zero Results: If no comparables are found, try lowering the `--min-score` threshold (e.g., `--min-score 0.25`) or increasing `--max-candidates`.

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key (required)
- `OPENAI_MODEL`: OpenAI model to use (default: gpt-5)
- `MAX_CANDIDATES`: Default maximum candidates (default: 40)
- `MIN_SCORE`: Default minimum score threshold (default: 0.35)

### Model Selection

You can switch models via `--model` flag or `OPENAI_MODEL` environment variable:
- `gpt-5`: Latest model (default)
- `gpt-4o`: Previous latest
- `gpt-4-turbo`: Balanced option
- `gpt-3.5-turbo`: Fastest and cheapest

### Threshold Tuning

Adjust `--min-score` to control strictness:
- Lower (0.2-0.3): More candidates, may include less similar companies
- Higher (0.4-0.5): Fewer candidates, only very similar companies

## Project Structure

```
rationalAI/
├── app/
│   ├── __init__.py
│   ├── cli.py              # CLI entry point
│   ├── pipeline.py         # Main orchestration
│   ├── retrieval.py        # Web search and scraping
│   ├── extraction.py       # LLM-based field extraction
│   ├── compare.py          # Similarity and validation
│   ├── schemas.py          # Pydantic models
│   ├── io_utils.py         # File I/O and provenance
│   └── exchanges.py       # Exchange/ticker utilities
├── tests/
│   ├── __init__.py
│   └── test_basic.py       # Smoke tests
├── requirements.txt        # Dependencies
├── env.example             # Environment variable template
├── example_target.json     # Example input file
└── README.md               # This file
```

## Dependencies

- `pydantic>=2.0.0`: Data validation and modeling
- `requests>=2.31.0`: HTTP requests
- `pandas>=2.0.0`: Data manipulation
- `pyarrow>=14.0.0`: Parquet file support
- `beautifulsoup4>=4.12.0`: HTML parsing
- `openai>=1.0.0`: OpenAI API client
- `python-dotenv>=1.0.0`: Environment variable management
- `httpx>=0.25.0`: Async HTTP (optional, for future use)
- `lxml>=4.9.0`: XML/HTML parser
