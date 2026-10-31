"""CLI Runner for Phase 9 Stage 4A: Authentic News NLP Preprocessing & Feature Generation.

Executes:
1. Ingestion of 62,329 authentic NSE disclosures.
2. Verification of source hash.
3. Deterministic NLP extraction (sentiment, 18-category events, importance, market relevance, causal novelty).
4. Authoritative Phase 8 PIT calendar partition (Snapshot A = 25,523, Snapshot B = 36,806).
5. Generation of authentic daily aggregates for Snapshot A and Snapshot B across all 4,653 trading days.
6. Recording of output artifacts and metrics.
"""

import json
import logging
from pathlib import Path
import sys
import time

from nifty_ai.data.news.preprocessing import run_authentic_news_preprocessing_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("nifty_ai.scripts.preprocess_authentic_news")


def main() -> None:
    project_root = Path(__file__).resolve().parent.parent
    raw_inventory_path = project_root / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"
    nifty_daily_path = project_root / "data" / "processed" / "nifty_50_daily.csv"
    output_dir = project_root / "data" / "interim" / "news"

    logger.info("================================================================================")
    logger.info("PHASE 9 — STAGE 4A: AUTHENTIC NEWS NLP PREPROCESSING & FEATURE GENERATION")
    logger.info("================================================================================")
    logger.info(f"Raw authentic inventory path: {raw_inventory_path}")
    logger.info(f"NIFTY 50 processed daily path: {nifty_daily_path}")
    logger.info(f"Output directory:             {output_dir}")

    t0 = time.time()
    try:
        results = run_authentic_news_preprocessing_pipeline(
            raw_inventory_path=raw_inventory_path,
            nifty_daily_path=nifty_daily_path,
            output_dir=output_dir,
        )
    except Exception as e:
        logger.error(f"STAGE 4A BLOCKED: Pipeline execution failed with error: {e}", exc_info=True)
        sys.exit(1)

    elapsed = time.time() - t0
    logger.info(f"Pipeline executed successfully in {elapsed:.2f}s ({elapsed/60:.2f} mins).")
    logger.info(f"Status: {results['status']}")
    logger.info(f"Input records processed: {results['input_record_count']}")
    logger.info(f"Snapshot A assigned:     {results['count_snapshot_a']}")
    logger.info(f"Snapshot B assigned:     {results['count_snapshot_b']}")
    logger.info(f"Unassigned count:        {results['unassigned_count']}")
    logger.info(f"Snapshot A daily rows:   {results['df_a_rows']}")
    logger.info(f"Snapshot B daily rows:   {results['df_b_rows']}")
    logger.info(f"No-news days (Snap A):   {results['no_news_days_a']}")
    logger.info(f"No-news days (Snap B):   {results['no_news_days_b']}")

    summary_json_path = project_root / "data" / "interim" / "news" / "stage_4a_summary.json"
    with open(summary_json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    logger.info(f"Saved stage 4A execution summary to {summary_json_path}")
    logger.info("================================================================================")
    logger.info("STAGE 4A COMPLETE!")
    logger.info("================================================================================")


if __name__ == "__main__":
    main()
