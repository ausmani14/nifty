"""CLI Script to Execute Phase 9 Step 3 News NLP Feature Generation Pipeline."""

import logging
from pathlib import Path
import sys

from nifty_ai.data.news.feature_generation import run_point_in_time_news_feature_pipeline

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

logger = logging.getLogger("scripts.generate_news_features")


def main():
    root = Path(__file__).resolve().parent.parent
    hist_path = root / "data" / "interim" / "news" / "raw_authentic_news_inventory.jsonl"
    term_path = root / "data" / "interim" / "news" / "raw_authentic_news_terminal_2022_2026_step2e.jsonl"
    nifty_daily_path = root / "data" / "processed" / "nifty_50_daily.csv"
    output_dir = root / "data" / "interim" / "news"

    logger.info("Starting Phase 9 Step 3 Point-in-Time News Feature Generation...")
    res = run_point_in_time_news_feature_pipeline(
        historical_inventory_path=hist_path,
        terminal_holdout_path=term_path,
        nifty_daily_path=nifty_daily_path,
        output_dir=output_dir,
    )

    print("\n" + "=" * 80)
    print("PHASE 9 STEP 3 FEATURE GENERATION SUCCESSFUL")
    print("=" * 80)
    print(f"Snapshot A Rows: {len(res['df_a'])}, Active Records: {res['count_a_active']}, Total: {res['count_a_total']}")
    print(f"Snapshot B Rows: {len(res['df_b'])}, Active Records: {res['count_b_active']}, Total: {res['count_b_total']}")
    print(f"Filtered Inactive: {res['filtered_inactive_count']}, Unassigned: {res['unassigned_count']}")
    print(f"Snapshot A SHA-256: {res['sha_a']}")
    print(f"Snapshot B SHA-256: {res['sha_b']}")
    print(f"Snapshot Delta SHA-256: {res['sha_delta']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
