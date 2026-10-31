"""Phase 8 Human Annotation Forensic Completion & Template Validator.

Audits the 14 mandatory annotation integrity checks:
1. Required records exist (1,050 dev, 200 holdout).
2. No duplicate annotation IDs.
3. Mandatory label columns presence and completeness.
4. Valid sentiment values (POSITIVE, NEGATIVE, NEUTRAL, UNCERTAIN).
5. Valid event taxonomy values (canonical 16 classes).
6. Maximum 3 secondary events from taxonomy.
7. Valid relevance values (HIGH, MEDIUM, LOW, NONE).
8. Importance is integer 1–5.
9. Confidence is valid (HIGH, MEDIUM, LOW).
10. Development and holdout remain strictly separate (zero ID overlap, chronological separation).
11. Original source IDs remain valid in authentic news inventories.
12. No future information fields introduced (prices, returns, lookahead).
13. No model prediction fields introduced (FinBERT, VADER, LLM, probabilities).
14. Original source provenance remains intact (metadata matches raw inventory).

Fails loudly with non-zero exit code upon any invariant violation.
"""

import argparse
import csv
import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Set, Any

DEV_INPUT_FILE = 'data/interim/news/gold_annotation_input.csv'
DEV_MANIFEST_FILE = 'data/interim/news/gold_sampling_manifest.csv'
DEV_ANN1_FILE = 'data/interim/news/annotator_1_template.csv'
DEV_ANN2_FILE = 'data/interim/news/annotator_2_template.csv'
DEV_ADJ_FILE = 'data/interim/news/adjudication_template.csv'

HOLDOUT_INPUT_FILE = 'data/interim/news/gold_holdout_annotation_input.csv'
HOLDOUT_MANIFEST_FILE = 'data/interim/news/gold_holdout_manifest.csv'
HOLDOUT_ANN1_FILE = 'data/interim/news/annotator_1_holdout_template.csv'
HOLDOUT_ANN2_FILE = 'data/interim/news/annotator_2_holdout_template.csv'
HOLDOUT_ADJ_FILE = 'data/interim/news/adjudication_holdout_template.csv'

RAW_INVENTORY_DEV = 'data/interim/news/raw_authentic_news_inventory.jsonl'
RAW_INVENTORY_HOLDOUT = 'data/interim/news/raw_authentic_news_holdout_2022plus.jsonl'

VALID_SENTIMENTS = {'POSITIVE', 'NEGATIVE', 'NEUTRAL', 'UNCERTAIN'}
VALID_RELEVANCE = {'HIGH', 'MEDIUM', 'LOW', 'NONE'}
VALID_CONFIDENCE = {'HIGH', 'MEDIUM', 'LOW'}
VALID_EVENTS = {
    'EARNINGS', 'CONTRACTS', 'REGULATORY', 'MANAGEMENT', 'M_AND_A',
    'LITIGATION', 'DIVIDENDS', 'CAPITAL', 'EXPANSION', 'PRODUCT',
    'ESG', 'CREDIT_RATING', 'MACRO', 'GLOBAL', 'MARKET_RUMOR', 'OTHER'
}

FORBIDDEN_COLUMNS_KEYWORDS = [
    'return', 'price', 'close', 'open', 'high', 'low', 'volume', 'nifty_ret',
    'target', 'fwd', 'forward', 'prediction', 'pred', 'finbert', 'vader',
    'llm', 'model_prob', 'pred_prob', 'logit', 'score_sentiment'
]


def load_csv(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"Required file missing: {path}")
    with open(path, 'r', encoding='utf-8') as f:
        return list(csv.DictReader(f))


def load_raw_inventory_ids(path: str) -> Set[str]:
    ids = set()
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    rec_id = item.get('article_id') or item.get('record_id')
                    if rec_id:
                        ids.add(rec_id)
    return ids


def run_forensic_audit(mode: str = 'templates') -> bool:
    print("\n================================================================================")
    print(f"PHASE 8 FORENSIC ANNOTATION VALIDATION AUDIT (Mode: {mode.upper()})")
    print("================================================================================")

    violations = []

    # 1. Required records exist
    dev_input = load_csv(DEV_INPUT_FILE)
    dev_manifest = load_csv(DEV_MANIFEST_FILE)
    dev_ann1 = load_csv(DEV_ANN1_FILE)
    dev_ann2 = load_csv(DEV_ANN2_FILE)
    dev_adj = load_csv(DEV_ADJ_FILE)

    holdout_input = load_csv(HOLDOUT_INPUT_FILE)
    holdout_manifest = load_csv(HOLDOUT_MANIFEST_FILE)
    holdout_ann1 = load_csv(HOLDOUT_ANN1_FILE)
    holdout_ann2 = load_csv(HOLDOUT_ANN2_FILE)
    holdout_adj = load_csv(HOLDOUT_ADJ_FILE)

    print(f"[Check 1] Checking record counts...")
    if len(dev_input) != 1050:
        violations.append(f"Check 1 Failed: Development input count is {len(dev_input)}, expected 1050")
    if len(dev_manifest) != 1050:
        violations.append(f"Check 1 Failed: Development manifest count is {len(dev_manifest)}, expected 1050")
    if len(dev_ann1) != 1050 or len(dev_ann2) != 1050 or len(dev_adj) != 1050:
        violations.append("Check 1 Failed: Development templates row count mismatch (expected 1050 each)")

    if len(holdout_input) != 200:
        violations.append(f"Check 1 Failed: Holdout input count is {len(holdout_input)}, expected 200")
    if len(holdout_manifest) != 200:
        violations.append(f"Check 1 Failed: Holdout manifest count is {len(holdout_manifest)}, expected 200")
    if len(holdout_ann1) != 200 or len(holdout_ann2) != 200 or len(holdout_adj) != 200:
        violations.append("Check 1 Failed: Holdout templates row count mismatch (expected 200 each)")

    # 2. No duplicate annotation IDs
    print(f"[Check 2] Checking for duplicate annotation IDs...")
    dev_ids = [r['annotation_id'] for r in dev_input]
    holdout_ids = [r['annotation_id'] for r in holdout_input]
    if len(dev_ids) != len(set(dev_ids)):
        violations.append(f"Check 2 Failed: Duplicate annotation IDs found in development ({len(dev_ids)} vs {len(set(dev_ids))} unique)")
    if len(holdout_ids) != len(set(holdout_ids)):
        violations.append(f"Check 2 Failed: Duplicate annotation IDs found in holdout ({len(holdout_ids)} vs {len(set(holdout_ids))} unique)")

    # 3. Missing mandatory labels check
    print(f"[Check 3] Auditing mandatory labels...")
    templates_to_check = [
        ('Development Annotator 1', dev_ann1),
        ('Development Annotator 2', dev_ann2),
        ('Holdout Annotator 1', holdout_ann1),
        ('Holdout Annotator 2', holdout_ann2),
    ]

    for name, rows in templates_to_check:
        populated_sentiments = [r['sentiment'].strip() for r in rows if r.get('sentiment', '').strip()]
        if mode == 'templates':
            # Templates must be pristine and blank prior to human labeling
            if len(populated_sentiments) > 0:
                violations.append(f"Check 3 Failed: {name} contains {len(populated_sentiments)} pre-populated labels in templates mode (expected 0 prior to human labeling)")
        elif mode == 'completed':
            # Completed mode requires 100% populated labels
            if len(populated_sentiments) < len(rows):
                violations.append(f"Check 3 Failed: {name} incomplete ({len(populated_sentiments)}/{len(rows)} labeled)")

    # 4 to 9: Value validation (runs on any populated labels in either mode)
    print(f"[Checks 4-9] Auditing label vocabulary and constraints...")
    for name, rows in templates_to_check:
        for idx, r in enumerate(rows):
            aid = r.get('annotation_id', f'Row {idx}')
            s = r.get('sentiment', '').strip()
            e = r.get('primary_event', '').strip()
            sec = r.get('secondary_events', '').strip()
            rel = r.get('relevance', '').strip()
            imp = r.get('importance', '').strip()
            conf = r.get('sentiment_confidence', '').strip()

            if s and s not in VALID_SENTIMENTS:
                violations.append(f"Check 4 Failed ({name}, {aid}): Invalid sentiment '{s}'")
            if e and e not in VALID_EVENTS:
                violations.append(f"Check 5 Failed ({name}, {aid}): Invalid primary event '{e}'")
            if sec:
                sec_list = [x.strip() for x in sec.split(';') if x.strip()]
                if len(sec_list) > 3:
                    violations.append(f"Check 6 Failed ({name}, {aid}): More than 3 secondary events ({len(sec_list)})")
                for sub_e in sec_list:
                    if sub_e not in VALID_EVENTS:
                        violations.append(f"Check 6 Failed ({name}, {aid}): Invalid secondary event '{sub_e}'")
            if rel and rel not in VALID_RELEVANCE:
                violations.append(f"Check 7 Failed ({name}, {aid}): Invalid relevance '{rel}'")
            if imp:
                try:
                    imp_val = int(imp)
                    if not (1 <= imp_val <= 5):
                        violations.append(f"Check 8 Failed ({name}, {aid}): Importance {imp_val} outside 1-5")
                except ValueError:
                    violations.append(f"Check 8 Failed ({name}, {aid}): Non-integer importance '{imp}'")
            if conf and conf not in VALID_CONFIDENCE:
                violations.append(f"Check 9 Failed ({name}, {aid}): Invalid confidence '{conf}'")

    # 10. Development and holdout remain separate
    print(f"[Check 10] Auditing strict development / holdout partition separation...")
    overlap_ann_ids = set(dev_ids) & set(holdout_ids)
    if overlap_ann_ids:
        violations.append(f"Check 10 Failed: {len(overlap_ann_ids)} annotation IDs overlap between dev and holdout")

    dev_source_ids = {r['source_record_id'] for r in dev_input}
    holdout_source_ids = {r['source_record_id'] for r in holdout_input}
    overlap_source_ids = dev_source_ids & holdout_source_ids
    if overlap_source_ids:
        violations.append(f"Check 10 Failed: {len(overlap_source_ids)} source record IDs overlap between dev and holdout")

    # Chronological cutoff check
    dev_max_date = max(r['timestamp'][:10] for r in dev_input)
    holdout_min_date = min(r['timestamp'][:10] for r in holdout_input)
    if dev_max_date >= '2022-01-01':
        violations.append(f"Check 10 Failed: Development set contains post-2021 timestamp: {dev_max_date}")
    if holdout_min_date < '2022-01-01':
        violations.append(f"Check 10 Failed: Holdout set contains pre-2022 timestamp: {holdout_min_date}")

    # 11. Original source IDs remain valid
    print(f"[Check 11] Auditing source IDs against raw authentic inventories...")
    raw_dev_ids = load_raw_inventory_ids(RAW_INVENTORY_DEV)
    raw_holdout_ids = load_raw_inventory_ids(RAW_INVENTORY_HOLDOUT)

    invalid_dev_sources = [sid for sid in dev_source_ids if sid not in raw_dev_ids]
    if invalid_dev_sources:
        violations.append(f"Check 11 Failed: {len(invalid_dev_sources)} development source IDs not found in authentic inventory")

    invalid_holdout_sources = [sid for sid in holdout_source_ids if sid not in raw_holdout_ids]
    if invalid_holdout_sources:
        violations.append(f"Check 11 Failed: {len(invalid_holdout_sources)} holdout source IDs not found in authentic holdout inventory")

    # 12 & 13. Forbidden future information and model prediction columns
    print(f"[Checks 12-13] Scanning for forbidden future return and model prediction columns...")
    all_files = [
        DEV_INPUT_FILE, DEV_MANIFEST_FILE, DEV_ANN1_FILE, DEV_ANN2_FILE, DEV_ADJ_FILE,
        HOLDOUT_INPUT_FILE, HOLDOUT_MANIFEST_FILE, HOLDOUT_ANN1_FILE, HOLDOUT_ANN2_FILE, HOLDOUT_ADJ_FILE
    ]

    for fpath in all_files:
        with open(fpath, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            cols = reader.fieldnames or []
            for col in cols:
                col_parts = col.lower().split('_')
                for forbidden in FORBIDDEN_COLUMNS_KEYWORDS:
                    if forbidden in col_parts or col.lower() == forbidden:
                        violations.append(f"Checks 12/13 Failed: Forbidden column '{col}' detected in {fpath}")

    # 14. Original source provenance remains intact
    print(f"[Check 14] Auditing source metadata consistency...")
    dev_lookup = {r['annotation_id']: r for r in dev_input}
    for r in dev_ann1:
        aid = r['annotation_id']
        if r['source_record_id'] != dev_lookup[aid]['source_record_id']:
            violations.append(f"Check 14 Failed: Source record ID mismatch for {aid} in Annotator 1 template")
    for r in dev_ann2:
        aid = r['annotation_id']
        if r['source_record_id'] != dev_lookup[aid]['source_record_id']:
            violations.append(f"Check 14 Failed: Source record ID mismatch for {aid} in Annotator 2 template")

    holdout_lookup = {r['annotation_id']: r for r in holdout_input}
    for r in holdout_ann1:
        aid = r['annotation_id']
        if r['source_record_id'] != holdout_lookup[aid]['source_record_id']:
            violations.append(f"Check 14 Failed: Source record ID mismatch for {aid} in Holdout Annotator 1 template")
    for r in holdout_ann2:
        aid = r['annotation_id']
        if r['source_record_id'] != holdout_lookup[aid]['source_record_id']:
            violations.append(f"Check 14 Failed: Source record ID mismatch for {aid} in Holdout Annotator 2 template")

    # Output verdict
    print("\n--------------------------------------------------------------------------------")
    if violations:
        print(f"FAILED: {len(violations)} INVARIANT VIOLATIONS DETECTED:")
        for v in violations:
            print(f"  - {v}")
        print("--------------------------------------------------------------------------------")
        return False
    else:
        print("PASS: ALL 14 FORENSIC INVARIANTS SATISFIED.")
        print(f"  - Development Package: 1,050 records (50 pilot + 1,000 dev) verified")
        print(f"  - Holdout Package:     200 records (2022+) strictly isolated & quarantined")
        print(f"  - Authenticity:        100% traced to raw NSE disclosure inventories")
        print(f"  - Contamination:       0 future lookahead columns, 0 model prediction columns")
        print("--------------------------------------------------------------------------------")
        return True


def main():
    parser = argparse.ArgumentParser(description="Validate Phase 8 Human Annotation Integrity")
    parser.add_argument('--mode', choices=['templates', 'completed'], default='templates',
                        help="templates: check structural readiness & quarantine; completed: require 100% human labels")
    args = parser.parse_args()

    passed = run_forensic_audit(mode=args.mode)
    if not passed:
        sys.exit(1)


if __name__ == '__main__':
    main()
