# How to Read the Output Files

This document explains how to interpret and use the comparable companies output files.

## Output Files

The pipeline generates three types of output files:

1. **CSV File** (`huron_comparables.csv`): Human-readable spreadsheet format
2. **Parquet File** (`huron_comparables.parquet`): Efficient binary format for data analysis
3. **Provenance Log** (`huron_comparables.provenance.jsonl`): Line-delimited JSON tracking data sources

## CSV File Format

The CSV file contains the following columns:

- **name**: Company name
- **url**: Company website URL
- **exchange**: Stock exchange (NYSE, NASDAQ, etc.) or "N/A" for private companies
- **ticker**: Stock ticker symbol or "N/A" for private companies
- **business_activity**: Summary of the company's main products/services
- **customer_segment**: Description of who the company sells to (industries/sectors)
- **sic_industry**: Standard Industrial Classification industry name (if available)
- **validation_score**: Overall similarity score (0.0 to 1.0, higher is better)
- **service_similarity**: Similarity score for products/services (0.0 to 1.0)
- **segment_similarity**: Similarity score for customer segments (0.0 to 1.0)
- **is_plausible**: Boolean indicating if LLM validation passed
- **evidence_urls**: List of source URLs used for data extraction

## Reading the CSV File

### Using Python (pandas)

```python
import pandas as pd

# Read the CSV file
df = pd.read_csv('huron_comparables.csv')

# Display the data
print(df)

# Filter by validation score
high_score = df[df['validation_score'] >= 0.6]
print(f"Companies with score >= 0.6: {len(high_score)}")

# Sort by validation score
sorted_df = df.sort_values('validation_score', ascending=False)
print(sorted_df[['name', 'ticker', 'validation_score']])
```

### Using Excel or Google Sheets

1. Open `huron_comparables.csv` in Excel or Google Sheets
2. The file will automatically be formatted as a table
3. You can sort, filter, and analyze the data using spreadsheet functions

### Using Command Line

```bash
# View the CSV file
cat huron_comparables.csv

# View with column alignment (requires column command)
column -t -s, huron_comparables.csv

# Count total comparables
wc -l huron_comparables.csv
```

## Reading the Parquet File

Parquet is a columnar storage format that's more efficient for large datasets:

```python
import pandas as pd

# Read the Parquet file
df = pd.read_parquet('huron_comparables.parquet')

# Same operations as CSV
print(df)
```

## Reading the Provenance Log

The provenance log is a JSONL (JSON Lines) file where each line is a separate JSON object:

```python
import json

# Read provenance log
with open('huron_comparables.provenance.jsonl', 'r') as f:
    for line in f:
        entry = json.loads(line)
        print(f"{entry['candidate_name']}: {entry['field']} = {entry['value']}")
        print(f"  Source: {entry['source_url']}")
```

## Understanding Validation Scores

- **validation_score**: Combined similarity score (0.0 to 1.0)
  - 0.7+: Very strong match
  - 0.5-0.7: Good match
  - 0.3-0.5: Moderate match
  - <0.3: Weak match (typically filtered out)

- **service_similarity**: How similar the products/services are
- **segment_similarity**: How similar the customer segments are

The validation_score is calculated as:
```
validation_score = 0.6 × service_similarity + 0.4 × segment_similarity
```

## Interpreting Results

1. **Sort by validation_score**: Companies with higher scores are more comparable
2. **Check is_plausible**: All companies in the output should have `is_plausible=True`
3. **Review business_activity**: Verify the services match your target company
4. **Review customer_segment**: Verify the customer base overlaps
5. **Check exchange/ticker**: Public companies will have exchange and ticker; private companies will show "N/A"

## Example Analysis

```python
import pandas as pd

df = pd.read_csv('huron_comparables.csv')

# Top 5 comparables
top_5 = df.nlargest(5, 'validation_score')
print("Top 5 Comparables:")
print(top_5[['name', 'ticker', 'validation_score', 'business_activity']])

# Public vs Private
public = df[df['exchange'] != 'N/A']
private = df[df['exchange'] == 'N/A']
print(f"\nPublic companies: {len(public)}")
print(f"Private companies: {len(private)}")

# Average scores
print(f"\nAverage validation score: {df['validation_score'].mean():.2f}")
print(f"Average service similarity: {df['service_similarity'].mean():.2f}")
print(f"Average segment similarity: {df['segment_similarity'].mean():.2f}")
```

## Notes

- Companies are ranked by validation_score in descending order
- All companies in the output passed validation checks
- Some companies may be private (no exchange/ticker)
- Evidence URLs show where the data was extracted from
- SIC industry may be None if not derivable from sources

