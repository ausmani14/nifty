"""Phase 8 Gold Dataset Assembly Engine.

Assembles the verified gold benchmark dataset from independent human annotations
and senior adjudication decisions.

Guarantees & Invariants:
1. Strict Completeness: Raises RuntimeError if 100% of human labels and required adjudications are not present.
2. Zero Imputation: Never defaults, imputes, or infers missing labels.
3. Zero Synthetic/Model Labels: Entirely driven by human annotators and adjudicators.
4. Hard Holdout Protection: Access to holdout gold generation strictly blocked without --final-evaluation flag.
5. Strict Schema Isolation: Excludes all future market returns, prices, and model predictions.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Any, Set

DEV_INPUT_1 = 'data/interim/news/annotator_1_template.csv'
DEV_INPUT_2 = 'data/interim/news/annotator_2_template.csv'
DEV_ADJUDICATION = 'data/interim/news/adjudication_template.csv'
DEV_META = 'data/interim/news/gold_annotation_input.csv'
DEV_OUTPUT = 'data/interim/news/gold_dataset_development.csv'

HOLDOUT_INPUT_1 = 'data/interim/news/annotator_1_holdout_template.csv'
HOLDOUT_INPUT_2 = 'data/interim/news/annotator_2_holdout_template.csv'
HOLDOUT_ADJUDICATION = 'data/interim/news/adjudication_holdout_template.csv'
HOLDOUT_META = 'data/interim/news/gold_holdout_annotation_input.csv'
HOLDOUT_OUTPUT = 'data/interim/news/gold_dataset_holdout.csv'

VALID_SENTIMENTS = {'POSITIVE', 'NEGATIVE', 'NEUTRAL', 'UNCERTAIN'}
VALID_RELEVANCE = {'HIGH', 'MEDIUM', 'LOW', 'NONE'}
VALID_EVENTS = {
    'EARNINGS', 'CONTRACTS', 'REGULATORY', 'MANAGEMENT', 'M_AND_A',
    'LITIGATION', 'DIVIDENDS', 'CAPITAL', 'EXPANSION', 'PRODUCT',
    'ESG', 'CREDIT_RATING', 'MACRO', 'GLOBAL', 'MARKET_RUMOR', 'OTHER'
}


def parse_secondary_events(events_str: str) -> Set[str]:
    """Parse semicolon-separated secondary events into a normalized set."""
    if not events_str:
        return set()
    return set(x.strip() for x in events_str.split(';') if x.strip())


def build_gold_dataset(
    split: str = 'development',
    final_evaluation: bool = False,
    input_1_path: str = None,
    input_2_path: str = None,
    adjudication_path: str = None,
    meta_path: str = None,
    output_path: str = None
) -> str:
    """Build gold dataset with strict integrity checks."""
    if split == 'holdout':
        if not final_evaluation:
            raise PermissionError(
                "ERROR: HOLDOUT GOLD DATASET ACCESS BLOCKED — "
                "The 200-record terminal holdout is quarantined. "
                "Requires explicit --final-evaluation flag to prevent data leakage."
            )
        input_1 = input_1_path or HOLDOUT_INPUT_1
        input_2 = input_2_path or HOLDOUT_INPUT_2
        adjudication = adjudication_path or HOLDOUT_ADJUDICATION
        meta_file = meta_path or HOLDOUT_META
        out_file = output_path or HOLDOUT_OUTPUT
    else:
        input_1 = input_1_path or DEV_INPUT_1
        input_2 = input_2_path or DEV_INPUT_2
        adjudication = adjudication_path or DEV_ADJUDICATION
        meta_file = meta_path or DEV_META
        out_file = output_path or DEV_OUTPUT

    print(f"\n================================================================================")
    print(f"ASSEMBLING GOLD DATASET ({split.upper()})")
    print(f"Annotator 1:     {input_1}")
    print(f"Annotator 2:     {input_2}")
    print(f"Adjudication:    {adjudication}")
    print(f"Input Metadata:  {meta_file}")
    print(f"Target Output:   {out_file}")
    print(f"================================================================================")

    # Load Annotator 1
    if not os.path.exists(input_1):
        raise FileNotFoundError(f"Annotator 1 file not found: {input_1}")
    with open(input_1, 'r', encoding='utf-8') as f:
        rows_1 = {r['annotation_id']: r for r in csv.DictReader(f)}

    # Load Annotator 2
    if not os.path.exists(input_2):
        raise FileNotFoundError(f"Annotator 2 file not found: {input_2}")
    with open(input_2, 'r', encoding='utf-8') as f:
        rows_2 = {r['annotation_id']: r for r in csv.DictReader(f)}

    # Load Adjudication
    existing_adj = {}
    if os.path.exists(adjudication):
        with open(adjudication, 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                existing_adj[r['annotation_id']] = r

    # Load Metadata
    meta_lookup = {}
    if os.path.exists(meta_file):
        with open(meta_file, 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                meta_lookup[r['annotation_id']] = r

    common_ids = sorted(list(set(rows_1.keys()) & set(rows_2.keys())))
    total_records = len(common_ids)

    # Check for complete human annotations
    unannotated = []
    for aid in common_ids:
        r1 = rows_1[aid]
        r2 = rows_2[aid]
        if not r1.get('sentiment', '').strip() or not r2.get('sentiment', '').strip() or \
           not r1.get('primary_event', '').strip() or not r2.get('primary_event', '').strip():
            unannotated.append(aid)

    if unannotated:
        raise RuntimeError(
            f"ERROR: GOLD DATASET CANNOT BE GENERATED — HUMAN ANNOTATION INCOMPLETE "
            f"({len(unannotated)}/{total_records} records missing human annotations). "
            f"Independent human annotators must complete all records before gold compilation."
        )

    # Validate annotations and resolve adjudications
    gold_records = []
    adjudicated_count = 0
    consensus_count = 0

    for aid in common_ids:
        r1 = rows_1[aid]
        r2 = rows_2[aid]
        meta = meta_lookup.get(aid, {})
        adj = existing_adj.get(aid, {})

        s1 = r1['sentiment'].strip()
        s2 = r2['sentiment'].strip()
        e1 = r1['primary_event'].strip()
        e2 = r2['primary_event'].strip()
        sec1 = parse_secondary_events(r1.get('secondary_events', ''))
        sec2 = parse_secondary_events(r2.get('secondary_events', ''))
        rel1 = r1.get('relevance', '').strip()
        rel2 = r2.get('relevance', '').strip()

        try:
            imp1 = int(r1.get('importance', 0))
            imp2 = int(r2.get('importance', 0))
        except ValueError:
            imp1, imp2 = 0, 0

        # Discrepancy checks
        is_disputed = (s1 != s2) or (e1 != e2) or (sec1 != sec2) or (rel1 != rel2) or (abs(imp1 - imp2) >= 1)

        if not is_disputed:
            # Consensus
            gold_sentiment = s1
            gold_event = e1
            gold_secondary = r1.get('secondary_events', '')
            gold_relevance = rel1
            gold_importance = imp1
            is_adj = False
            adj_id = ''
            adj_rationale = ''
            consensus_count += 1
        else:
            # Adjudication Required
            gold_sentiment = adj.get('final_gold_sentiment', '').strip() or (s1 if s1 == s2 else '')
            gold_event = adj.get('final_gold_event', '').strip() or (e1 if e1 == e2 else '')
            gold_secondary = adj.get('final_gold_secondary_events', '').strip() if sec1 != sec2 else r1.get('secondary_events', '')
            gold_relevance = adj.get('final_gold_relevance', '').strip() or (rel1 if rel1 == rel2 else '')
            gold_importance_str = adj.get('final_gold_importance', '').strip()
            gold_importance = int(gold_importance_str) if gold_importance_str else (imp1 if imp1 == imp2 else 0)

            adj_id = adj.get('adjudicator_id', '').strip()
            adj_rationale = adj.get('adjudication_rationale', '').strip()

            if not gold_sentiment or not gold_event or not gold_relevance or gold_importance == 0 or not adj_id or not adj_rationale:
                raise RuntimeError(
                    f"ERROR: GOLD DATASET CANNOT BE GENERATED — ADJUDICATION INCOMPLETE for record {aid}. "
                    f"Senior Adjudicator must provide final labels, adjudicator ID, and written rationale for all disputed records."
                )

            is_adj = True
            adjudicated_count += 1

        # Check validity of final values
        if gold_sentiment not in VALID_SENTIMENTS:
            raise ValueError(f"Invalid gold sentiment '{gold_sentiment}' for record {aid}")
        if gold_event not in VALID_EVENTS:
            raise ValueError(f"Invalid gold event '{gold_event}' for record {aid}")
        if gold_relevance not in VALID_RELEVANCE:
            raise ValueError(f"Invalid gold relevance '{gold_relevance}' for record {aid}")
        if not (1 <= gold_importance <= 5):
            raise ValueError(f"Invalid gold importance '{gold_importance}' for record {aid}")

        gold_records.append({
            'annotation_id': aid,
            'source_record_id': meta.get('source_record_id', r1.get('source_record_id', '')),
            'company': meta.get('company', ''),
            'timestamp': meta.get('timestamp', ''),
            'headline': meta.get('headline', ''),
            'source_url': meta.get('source_url', ''),
            'annotation_split': meta.get('annotation_split', split.upper()),
            'sentiment': gold_sentiment,
            'primary_event': gold_event,
            'secondary_events': gold_secondary,
            'relevance': gold_relevance,
            'importance': gold_importance,
            'is_adjudicated': 'TRUE' if is_adj else 'FALSE',
            'annotator_1_id': r1.get('annotator_id', 'ANN_USER_1'),
            'annotator_2_id': r2.get('annotator_id', 'ANN_USER_2'),
            'adjudicator_id': adj_id,
            'adjudication_rationale': adj_rationale,
        })

    # Export Gold Dataset
    os.makedirs(os.path.dirname(out_file), exist_ok=True)
    with open(out_file, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(gold_records[0].keys()))
        writer.writeheader()
        writer.writerows(gold_records)

    print(f"\nSUCCESS: Gold Dataset generated at: {out_file}")
    print(f"Total Gold Records:      {len(gold_records)}")
    print(f"Consensus Records:       {consensus_count} ({consensus_count/len(gold_records)*100:.1f}%)")
    print(f"Adjudicated Records:     {adjudicated_count} ({adjudicated_count/len(gold_records)*100:.1f}%)")
    print("================================================================================")
    return out_file


def main():
    parser = argparse.ArgumentParser(description="Assemble Phase 8 Gold Dataset")
    parser.add_argument('--split', choices=['development', 'holdout'], default='development')
    parser.add_argument('--final-evaluation', action='store_true', help="Mandatory authorization flag for holdout access")
    parser.add_argument('--input-1', default=None)
    parser.add_argument('--input-2', default=None)
    parser.add_argument('--adjudication', default=None)
    parser.add_argument('--meta', default=None)
    parser.add_argument('--output', default=None)
    args = parser.parse_args()

    try:
        build_gold_dataset(
            split=args.split,
            final_evaluation=args.final_evaluation,
            input_1_path=args.input_1,
            input_2_path=args.input_2,
            adjudication_path=args.adjudication,
            meta_path=args.meta,
            output_path=args.output
        )
    except (RuntimeError, PermissionError, ValueError, FileNotFoundError) as e:
        print(f"\n{str(e)}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
