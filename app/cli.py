"""CLI entry point for the comparable company finder."""

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Optional

from app.schemas import TargetInput
from app.pipeline import run_pipeline
from app.io_utils import save_comparables, save_provenance, print_summary

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)


def load_target_from_json(json_path: str) -> TargetInput:
    """
    Load target company data from JSON file.
    
    Args:
        json_path: Path to JSON file
        
    Returns:
        TargetInput object
    """
    with open(json_path, 'r') as f:
        data = json.load(f)
    
    return TargetInput(
        name=data.get('name', ''),
        business_description=data.get('business_description', ''),
        url=data.get('url'),
        primary_industry_classification=data.get('primary_industry_classification')
    )


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description='Find comparable companies for a target company',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Input options: either JSON file or individual flags
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        '--json',
        type=str,
        help='Path to JSON file with target company data'
    )
    input_group.add_argument(
        '--name',
        type=str,
        help='Target company name'
    )
    
    # Individual fields (required if --name is used)
    parser.add_argument(
        '--url',
        type=str,
        help='Target company URL'
    )
    parser.add_argument(
        '--business-description',
        type=str,
        dest='business_description',
        help='Target company business description'
    )
    parser.add_argument(
        '--primary-industry',
        type=str,
        dest='primary_industry',
        help='Primary industry classification (SIC name)'
    )
    
    # Output options
    parser.add_argument(
        '--out',
        type=str,
        required=True,
        help='Output file path (.csv or .parquet)'
    )
    
    # Pipeline parameters
    parser.add_argument(
        '--max-candidates',
        type=int,
        default=40,
        help='Maximum number of candidates to discover (default: 40)'
    )
    parser.add_argument(
        '--min-score',
        type=float,
        default=0.35,
        help='Minimum validation score threshold (default: 0.35)'
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-5',
        help='OpenAI model to use (default: gpt-5 - latest). Options: gpt-5, gpt-4o, gpt-4-turbo, gpt-3.5-turbo'
    )
    parser.add_argument(
        '--max-final',
        type=int,
        default=10,
        help='Maximum number of final comparables to return (default: 10)'
    )
    
    # Debug flag
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    # Validate: if --name is used, business_description is required
    if args.name and not args.business_description:
        parser.error("--business-description is required when using --name")
    
    return args


def main():
    """Main CLI entry point."""
    args = parse_args()
    
    # Set logging level
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load target company data
    if args.json:
        try:
            target = load_target_from_json(args.json)
        except Exception as e:
            logger.error(f"Failed to load JSON file: {e}")
            sys.exit(1)
    else:
        target = TargetInput(
            name=args.name,
            business_description=args.business_description,
            url=args.url,
            primary_industry_classification=args.primary_industry
        )
    
    # Validate target
    if not target.name or not target.business_description:
        logger.error("Target company name and business description are required")
        sys.exit(1)
    
    logger.info(f"Target company: {target.name}")
    logger.info(f"Parameters: max_candidates={args.max_candidates}, min_score={args.min_score}, model={args.model}")
    
    # Run pipeline
    try:
        comparables = run_pipeline(
            target=target,
            max_candidates=args.max_candidates,
            min_score=args.min_score,
            model=args.model,
            max_final=args.max_final
        )
    except KeyboardInterrupt:
        logger.warning("Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        error_msg = str(e)
        if 'quota' in error_msg.lower() or 'insufficient_quota' in error_msg.lower() or 'resource exhausted' in error_msg.lower():
            print("\n" + "="*60)
            print("ERROR: OPENAI API QUOTA EXCEEDED")
            print("="*60)
            print("Your OpenAI API account has no credits/quota remaining.")
            print("\nTo fix:")
            print("1. Go to: https://platform.openai.com/account/billing")
            print("2. Add a payment method and purchase credits")
            print("3. Wait a few minutes, then try again")
            print("="*60 + "\n")
        else:
            logger.error(f"Pipeline failed: {e}")
            if args.debug:
                import traceback
                traceback.print_exc()
        sys.exit(1)
    
    # Validate output - provide helpful feedback if no comparables found
    if not comparables:
        print("\n" + "="*60)
        print("WARNING: No comparables found")
        print("="*60)
        print("\nPossible reasons:")
        print("  1. Validation threshold too strict (try --min-score 0.25)")
        print("  2. Too few candidates discovered (try --max-candidates 50)")
        print("  3. Target company description may need more detail")
        print("\nSuggestions:")
        print("  - Lower threshold: --min-score 0.25")
        print("  - Increase candidates: --max-candidates 50")
        print("  - Try different model: --model gpt-4o")
        print("="*60 + "\n")
        logger.warning("No comparables found")
        sys.exit(0)
    
    if len(comparables) < 3:
        logger.warning(f"Found only {len(comparables)} comparables (expected 3-10)")
    
    # Save output
    try:
        save_comparables(comparables, args.out)
    except Exception as e:
        logger.error(f"Failed to save output: {e}")
        sys.exit(1)
    
    # Save provenance
    provenance_path = str(Path(args.out).with_suffix('.provenance.jsonl'))
    try:
        save_provenance(comparables, provenance_path)
    except Exception as e:
        logger.warning(f"Failed to save provenance: {e}")
    
    # Print summary
    print_summary(comparables)
    
    logger.info("Pipeline completed successfully")


if __name__ == '__main__':
    main()


