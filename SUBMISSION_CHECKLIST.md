# Submission Checklist

## ✅ Code Structure
- [x] All required modules present (cli.py, pipeline.py, extraction.py, compare.py, retrieval.py, schemas.py, io_utils.py, exchanges.py)
- [x] Tests included (tests/test_basic.py)
- [x] Requirements file present (requirements.txt)
- [x] Example input file (example_target.json)
- [x] Environment template (env.example)
- [x] README with comprehensive documentation

## ✅ Functionality
- [x] CLI accepts JSON file or command-line flags
- [x] Target normalization using OpenAI
- [x] Candidate discovery (curated list for demo)
- [x] Field extraction using OpenAI with JSON schema
- [x] Similarity scoring (Jaccard + TF-IDF)
- [x] Validation checks (product overlap, segment overlap, public listing, LLM validation)
- [x] Output to CSV/Parquet
- [x] Provenance logging

## ✅ Code Quality
- [x] Type hints throughout
- [x] Docstrings for all functions
- [x] Error handling with clear messages
- [x] Rate limiting and retry logic
- [x] Clean, production-ready code

## ⚠️ Important Notes for Reviewers

1. **API Key Required**: Reviewers need a valid OpenAI API key with credits
2. **Candidate Discovery**: Uses curated list (documented in README)
3. **Rate Limiting**: 25-second delays between API calls (for free tier)
4. **Processing Time**: ~5-10 minutes for 5 candidates
5. **Zero Results**: If no comparables found, try `--min-score 0.25`

## 📝 Testing Instructions

1. Set up API key in `.env` file
2. Run: `python -m app.cli --json example_target.json --out test.parquet --max-candidates 5 --min-score 0.25 --max-final 3`
3. Expected: 3-5 comparables in output file

