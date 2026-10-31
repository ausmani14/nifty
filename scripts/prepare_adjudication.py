"""Phase 8 Senior Adjudication Preparation & Disagreement Extractor.

Extracts inter-annotator disagreements and prepares the adjudication template.
Guarantees:
- Never auto-adjudicates.
- Disputed records are routed to adjudication with annotator 1 and 2 original labels preserved.
- Final gold columns and rationales are left empty for manual human adjudication.
- Any existing manual human adjudication entries are strictly preserved and never overwritten.
- Handles unannotated templates cleanly without throwing unhandled exceptions.
"""

import argparse
import csv
import os
import sys
from typing import Dict, List, Any, Set

DEFAULT_INPUT_1 = 'data/interim/news/annotator_1_template.csv'
DEFAULT_INPUT_2 = 'data/interim/news/annotator_2_template.csv'
DEFAULT_TEMPLATE = 'data/interim/news/adjudication_template.csv'
DEFAULT_DISAGREEMENTS = 'data/interim/news/annotation_disagreements.csv'
DEFAULT_META = 'data/interim/news/gold_annotation_input.csv'

HOLDOUT_INPUT_1 = 'data/interim/news/annotator_1_holdout_template.csv'
HOLDOUT_INPUT_2 = 'data/interim/news/annotator_2_holdout_template.csv'
HOLDOUT_TEMPLATE = 'data/interim/news/adjudication_holdout_template.csv'
HOLDOUT_DISAGREEMENTS = 'data/interim/news/annotation_holdout_disagreements.csv'
HOLDOUT_META = 'data/interim/news/gold_holdout_annotation_input.csv'


def parse_secondary_events(events_str: str) -> Set[str]:
    """Parse semicolon-separated secondary events into a normalized set."""
    if not events_str:
        return set()
    return set(x.strip() for x in events_str.split(';') if x.strip())


def prepare_adjudication(
    file1: str,
    file2: str,
    template_path: str,
    disagreements_path: str,
    meta_path: str
) -> Dict[str, Any]:
    """Identify disagreements and populate the adjudication template."""
    print(f"Loading Annotator 1 from: {file1}")
    with open(file1, 'r', encoding='utf-8') as f:
        rows_1 = {r['annotation_id']: r for r in csv.DictReader(f)}

    print(f"Loading Annotator 2 from: {file2}")
    with open(file2, 'r', encoding='utf-8') as f:
        rows_2 = {r['annotation_id']: r for r in csv.DictReader(f)}

    meta_lookup = {}
    if os.path.exists(meta_path):
        print(f"Loading Metadata from: {meta_path}")
        with open(meta_path, 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                meta_lookup[r['annotation_id']] = r

    # Load existing adjudication template if present
    existing_adj = {}
    template_fieldnames = []
    if os.path.exists(template_path):
        with open(template_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            template_fieldnames = reader.fieldnames or []
            for r in reader:
                existing_adj[r['annotation_id']] = r

    common_ids = sorted(list(set(rows_1.keys()) & set(rows_2.keys())))
    total_records = len(common_ids)

    # Check for populated records
    populated_ids = []
    for aid in common_ids:
        r1 = rows_1[aid]
        r2 = rows_2[aid]
        if (r1.get('sentiment', '').strip() or r1.get('primary_event', '').strip()) and \
           (r2.get('sentiment', '').strip() or r2.get('primary_event', '').strip()):
            populated_ids.append(aid)

    if len(populated_ids) == 0:
        print("\n================================================================================")
        print(f"STATUS: TEMPLATES UNANNOTATED — AWAITING HUMAN INPUT (0/{total_records} records labeled)")
        print("Adjudication template is preserved in its initial state.")
        print("Disagreements will be calculated once independent human annotators submit labels.")
        print("================================================================================")
        return {
            'status': 'AWAITING_HUMAN_LABELS',
            'total_records': total_records,
            'populated_records': 0,
            'disagreements_count': 0
        }

    print(f"Analyzing {len(populated_ids)} completed records for discrepancies...")

    disagreements = []
    updated_adj_rows = []

    for aid in common_ids:
        r1 = rows_1[aid]
        r2 = rows_2[aid]
        meta = meta_lookup.get(aid, {})
        existing = existing_adj.get(aid, {})

        # If not populated in both, keep existing row as is
        if aid not in populated_ids:
            if existing:
                updated_adj_rows.append(existing)
            continue

        s1 = r1.get('sentiment', '').strip()
        s2 = r2.get('sentiment', '').strip()
        e1 = r1.get('primary_event', '').strip()
        e2 = r2.get('primary_event', '').strip()
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
        dis_types = []
        sent_dis = s1 != s2
        event_dis = e1 != e2
        sec_dis = sec1 != sec2
        rel_dis = rel1 != rel2
        imp_dis = abs(imp1 - imp2) >= 1

        if sent_dis:
            dis_types.append('SENTIMENT')
        if event_dis:
            dis_types.append('PRIMARY_EVENT')
        if sec_dis:
            dis_types.append('SECONDARY_EVENTS')
        if rel_dis:
            dis_types.append('RELEVANCE')
        if imp_dis:
            dis_types.append('IMPORTANCE')

        if dis_types:
            disagreements.append({
                'annotation_id': aid,
                'source_record_id': r1.get('source_record_id', meta.get('source_record_id', '')),
                'company': meta.get('company', ''),
                'timestamp': meta.get('timestamp', ''),
                'headline': meta.get('headline', ''),
                'disagreement_types': ';'.join(dis_types),
                'annotator_1_sentiment': s1,
                'annotator_2_sentiment': s2,
                'annotator_1_event': e1,
                'annotator_2_event': e2,
                'annotator_1_secondary_events': r1.get('secondary_events', ''),
                'annotator_2_secondary_events': r2.get('secondary_events', ''),
                'annotator_1_relevance': rel1,
                'annotator_2_relevance': rel2,
                'annotator_1_importance': imp1,
                'annotator_2_importance': imp2,
            })

        # Build adjudication row
        adj_row = dict(existing)
        adj_row['annotation_id'] = aid
        adj_row['source_record_id'] = r1.get('source_record_id', existing.get('source_record_id', ''))
        if 'holdout_id' in template_fieldnames:
            adj_row['holdout_id'] = existing.get('holdout_id', meta.get('holdout_id', ''))

        adj_row['annotator_1_sentiment'] = s1
        adj_row['annotator_2_sentiment'] = s2
        adj_row['sentiment_disagreement'] = 'TRUE' if sent_dis else 'FALSE'

        adj_row['annotator_1_event'] = e1
        adj_row['annotator_2_event'] = e2
        adj_row['event_disagreement'] = 'TRUE' if event_dis else 'FALSE'

        adj_row['annotator_1_secondary_events'] = r1.get('secondary_events', '')
        adj_row['annotator_2_secondary_events'] = r2.get('secondary_events', '')

        adj_row['annotator_1_relevance'] = rel1
        adj_row['annotator_2_relevance'] = rel2

        adj_row['annotator_1_importance'] = imp1 if imp1 > 0 else ''
        adj_row['annotator_2_importance'] = imp2 if imp2 > 0 else ''

        # Preserve human adjudicator inputs if already entered, otherwise leave empty
        adj_row['final_gold_sentiment'] = existing.get('final_gold_sentiment', '')
        adj_row['final_gold_event'] = existing.get('final_gold_event', '')
        adj_row['final_gold_secondary_events'] = existing.get('final_gold_secondary_events', '')
        adj_row['final_gold_relevance'] = existing.get('final_gold_relevance', '')
        adj_row['final_gold_importance'] = existing.get('final_gold_importance', '')
        adj_row['adjudicator_id'] = existing.get('adjudicator_id', '')
        adj_row['adjudication_rationale'] = existing.get('adjudication_rationale', '')
        adj_row['adjudication_timestamp'] = existing.get('adjudication_timestamp', '')

        updated_adj_rows.append(adj_row)

    # Export Disagreements
    if disagreements:
        os.makedirs(os.path.dirname(disagreements_path), exist_ok=True)
        with open(disagreements_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(disagreements[0].keys()))
            writer.writeheader()
            writer.writerows(disagreements)
        print(f"\nExported {len(disagreements)} disputed records to: {disagreements_path}")

    # Update Adjudication Template
    if updated_adj_rows and template_fieldnames:
        with open(template_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=template_fieldnames)
            writer.writeheader()
            writer.writerows(updated_adj_rows)
        print(f"Updated adjudication template with annotator labels at: {template_path}")
        print("Note: Final gold columns and rationales are preserved/left empty for manual adjudication.")

    print("\n================================================================================")
    print(f"ADJUDICATION PREPARATION COMPLETE")
    print(f"Total Evaluated Records:   {len(populated_ids)}")
    print(f"Total Disputed Records:    {len(disagreements)} ({len(disagreements)/len(populated_ids)*100:.1f}%)")
    print("================================================================================")

    return {
        'status': 'PREPARATION_COMPLETE',
        'total_records': total_records,
        'populated_records': len(populated_ids),
        'disagreements_count': len(disagreements)
    }


def main():
    parser = argparse.ArgumentParser(description="Prepare Phase 8 Adjudication File")
    parser.add_argument('--input-1', default=DEFAULT_INPUT_1, help="Annotator 1 CSV")
    parser.add_argument('--input-2', default=DEFAULT_INPUT_2, help="Annotator 2 CSV")
    parser.add_argument('--template', default=DEFAULT_TEMPLATE, help="Adjudication Template CSV")
    parser.add_argument('--disagreements', default=DEFAULT_DISAGREEMENTS, help="Disagreements Output CSV")
    parser.add_argument('--meta', default=DEFAULT_META, help="Metadata CSV")
    parser.add_argument('--holdout', action='store_true', help="Use Holdout files")
    args = parser.parse_args()

    if args.holdout:
        input_1 = HOLDOUT_INPUT_1
        input_2 = HOLDOUT_INPUT_2
        template = HOLDOUT_TEMPLATE
        disagreements = HOLDOUT_DISAGREEMENTS
        meta = HOLDOUT_META
    else:
        input_1 = args.input_1
        input_2 = args.input_2
        template = args.template
        disagreements = args.disagreements
        meta = args.meta

    prepare_adjudication(
        file1=input_1,
        file2=input_2,
        template_path=template,
        disagreements_path=disagreements,
        meta_path=meta
    )


if __name__ == '__main__':
    main()
