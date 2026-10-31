"""Generate Gold Sampling Manifest and Human Annotation Package.

Reproducibly generates:
- data/interim/news/gold_sampling_manifest.csv
- data/interim/news/gold_annotation_input.csv
- data/interim/news/annotator_1_template.csv
- data/interim/news/annotator_2_template.csv
- data/interim/news/adjudication_template.csv

Uses deterministic pseudo-random sampling (seed=42) from the authentic 62,329-record inventory.
Strictly decoupled from model predictions; zero labels generated.
"""

import csv
import hashlib
import json
import os
import random
from collections import Counter, defaultdict

CORPUS_PATH = 'data/interim/news/raw_authentic_news_inventory.jsonl'
EXPECTED_SHA = '6134fd770b30abe70ed1a839968ce165176e920f5e742651923d3749709ab7b3'
RANDOM_SEED = 42

OUTPUT_DIR = 'data/interim/news'
MANIFEST_CSV = os.path.join(OUTPUT_DIR, 'gold_sampling_manifest.csv')
ANNOTATION_INPUT_CSV = os.path.join(OUTPUT_DIR, 'gold_annotation_input.csv')
ANNOTATOR_1_CSV = os.path.join(OUTPUT_DIR, 'annotator_1_template.csv')
ANNOTATOR_2_CSV = os.path.join(OUTPUT_DIR, 'annotator_2_template.csv')
ADJUDICATION_CSV = os.path.join(OUTPUT_DIR, 'adjudication_template.csv')


def get_length_tier(text: str) -> str:
    l = len(text)
    if l <= 290:
        return 'SHORT'
    elif l <= 533:
        return 'MEDIUM'
    else:
        return 'LONG'


def get_snapshot(pit: str) -> str:
    if 'SNAPSHOT_A' in pit:
        return 'SNAPSHOT_A'
    return 'SNAPSHOT_B'


def get_regime(year: str) -> str:
    y = int(year)
    if y in (2008, 2009):
        return 'REGIME_1_GFC'
    elif y in (2010, 2011, 2012):
        return 'REGIME_2_EURO_DEBT_INFLATION'
    elif y in (2013, 2014, 2015, 2016, 2017):
        return 'REGIME_3_STRUCTURAL_BULL'
    elif y in (2018, 2019):
        return 'REGIME_4_NBFC_CRISIS'
    else:
        return 'REGIME_5_COVID_PANDEMIC'


def main():
    print("=== Step 1: Verify Authentic Corpus SHA-256 ===")
    assert os.path.exists(CORPUS_PATH), f"Corpus not found: {CORPUS_PATH}"
    h = hashlib.sha256()
    with open(CORPUS_PATH, 'rb') as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    actual_sha = h.hexdigest()
    if actual_sha != EXPECTED_SHA:
        raise ValueError(f"Corpus SHA mismatch! Expected: {EXPECTED_SHA}, Actual: {actual_sha}")
    print(f"SHA-256 Verified: {actual_sha}")

    print("=== Step 2: Ingest & Stratify Authentic Records ===")
    records = []
    strata_counts = Counter()
    with open(CORPUS_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            r = json.loads(line)
            text = (r.get('headline') or '') + ' ' + (r.get('summary_or_body') or '')
            r['doc_len'] = len(text)
            r['length_tier'] = get_length_tier(text)
            r['norm_snapshot'] = get_snapshot(r.get('pit_eligibility', ''))
            year = r.get('published_timestamp', '')[:4]
            r['pub_year'] = year
            r['regime'] = get_regime(year)
            r['stratum'] = f"{year}__{r.get('sector')}__{r['norm_snapshot']}__{r['length_tier']}"
            strata_counts[r['stratum']] += 1
            records.append(r)

    total_records = len(records)
    print(f"Loaded {total_records} records across {len(strata_counts)} strata.")

    print("=== Step 3: Deterministic Stratified Sampling (Seed=42) ===")
    rng = random.Random(RANDOM_SEED)

    # Group records by stratum
    strata_map = defaultdict(list)
    for r in records:
        strata_map[r['stratum']].append(r)

    # Deterministic sort and shuffle within each stratum
    for s in strata_map:
        strata_map[s].sort(key=lambda x: x['article_id'])
        rng.shuffle(strata_map[s])

    strata_keys = sorted(list(strata_map.keys()))
    rng.shuffle(strata_keys)

    # Target: 1050 records total (50 pilot + 1000 development)
    TARGET_TOTAL = 1050
    selected = []
    company_counts = Counter()
    selected_ids = set()

    # Pass 1: Draw from strata enforcing diversity and company cap <= 30
    while len(selected) < TARGET_TOTAL:
        added_in_round = 0
        for s in strata_keys:
            if len(selected) >= TARGET_TOTAL:
                break
            for cand in strata_map[s]:
                aid = cand['article_id']
                if aid in selected_ids:
                    continue
                comp = cand.get('company', '')
                if company_counts[comp] >= 30 and len(selected) > 850:
                    continue
                selected.append(cand)
                selected_ids.add(aid)
                company_counts[comp] += 1
                added_in_round += 1
                break
        if added_in_round == 0:
            # Fallback: fill remaining without strict company cap
            for s in strata_keys:
                if len(selected) >= TARGET_TOTAL:
                    break
                for cand in strata_map[s]:
                    aid = cand['article_id']
                    if aid not in selected_ids:
                        selected.append(cand)
                        selected_ids.add(aid)
                        company_counts[cand.get('company', '')] += 1
                        break

    print(f"Sampled {len(selected)} records.")

    # Sort selected records chronologically
    selected.sort(key=lambda x: (x['published_timestamp'], x['article_id']))

    # Step 4: Split into 50 Calibration Pilot and 1000 Production Development
    # Use deterministic seeded selection for pilot to ensure representative spread
    rng_pilot = random.Random(RANDOM_SEED)
    pilot_indices = set(rng_pilot.sample(range(len(selected)), 50))

    manifest_rows = []
    annotation_rows = []
    annotator_rows = []
    adjudication_rows = []

    for i, r in enumerate(selected):
        is_pilot = (i in pilot_indices)
        sample_num = i + 1
        sample_id = f"SMP_{sample_num:06d}"
        ann_id = f"ANN_{sample_num:06d}"

        split = "DEVELOPMENT_PILOT" if is_pilot else "DEVELOPMENT"
        stratum_total = strata_counts[r['stratum']]
        # stratum sample count in our selection
        stratum_sampled = sum(1 for x in selected if x['stratum'] == r['stratum'])
        sampling_prob = round(stratum_sampled / stratum_total, 6) if stratum_total > 0 else 0.0

        # Manifest Row
        manifest_rows.append({
            'sample_id': sample_id,
            'source_record_id': r['article_id'],
            'document_timestamp': r['published_timestamp'],
            'company': r.get('company', ''),
            'snapshot': r['norm_snapshot'],
            'source_url': r.get('source_url', ''),
            'year': r['pub_year'],
            'sector': r.get('sector', ''),
            'document_length': r['doc_len'],
            'length_tier': r['length_tier'],
            'market_regime': r['regime'],
            'split': split,
            'is_pilot': 'true' if is_pilot else 'false',
            'sampling_stratum': r['stratum'],
            'random_seed': RANDOM_SEED,
            'sampling_probability': sampling_prob
        })

        # Annotation Input Row (Visible to human annotators)
        annotation_rows.append({
            'annotation_id': ann_id,
            'source_record_id': r['article_id'],
            'timestamp': r['published_timestamp'],
            'snapshot': r['norm_snapshot'],
            'company': r.get('company', ''),
            'headline': r.get('headline', ''),
            'summary_or_body': r.get('summary_or_body', ''),
            'source_url': r.get('source_url', ''),
            'annotation_split': split,
            'annotation_version': '1.0.0'
        })

        # Annotator Template Row
        annotator_rows.append({
            'annotation_id': ann_id,
            'source_record_id': r['article_id'],
            'annotator_id': '',
            'sentiment': '',
            'sentiment_confidence': '',
            'primary_event': '',
            'secondary_events': '',
            'relevance': '',
            'importance': '',
            'notes': ''
        })

        # Adjudication Template Row
        adjudication_rows.append({
            'annotation_id': ann_id,
            'source_record_id': r['article_id'],
            'annotator_1_sentiment': '',
            'annotator_2_sentiment': '',
            'sentiment_disagreement': '',
            'final_gold_sentiment': '',
            'annotator_1_event': '',
            'annotator_2_event': '',
            'event_disagreement': '',
            'final_gold_event': '',
            'annotator_1_secondary_events': '',
            'annotator_2_secondary_events': '',
            'final_gold_secondary_events': '',
            'annotator_1_relevance': '',
            'annotator_2_relevance': '',
            'final_gold_relevance': '',
            'annotator_1_importance': '',
            'annotator_2_importance': '',
            'final_gold_importance': '',
            'adjudicator_id': '',
            'adjudication_rationale': '',
            'adjudication_timestamp': ''
        })

    print("=== Step 5: Export CSV Artifacts ===")
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # 1. Manifest
    with open(MANIFEST_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=manifest_rows[0].keys())
        writer.writeheader()
        writer.writerows(manifest_rows)
    print(f"Exported: {MANIFEST_CSV} ({len(manifest_rows)} rows)")

    # 2. Annotation Input
    with open(ANNOTATION_INPUT_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=annotation_rows[0].keys())
        writer.writeheader()
        writer.writerows(annotation_rows)
    print(f"Exported: {ANNOTATION_INPUT_CSV} ({len(annotation_rows)} rows)")

    # 3. Annotator 1 Template
    with open(ANNOTATOR_1_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=annotator_rows[0].keys())
        writer.writeheader()
        for row in annotator_rows:
            r_copy = dict(row)
            r_copy['annotator_id'] = 'ANN_USER_1'
            writer.writerow(r_copy)
    print(f"Exported: {ANNOTATOR_1_CSV} ({len(annotator_rows)} rows)")

    # 4. Annotator 2 Template
    with open(ANNOTATOR_2_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=annotator_rows[0].keys())
        writer.writeheader()
        for row in annotator_rows:
            r_copy = dict(row)
            r_copy['annotator_id'] = 'ANN_USER_2'
            writer.writerow(r_copy)
    print(f"Exported: {ANNOTATOR_2_CSV} ({len(annotator_rows)} rows)")

    # 5. Adjudication Template
    with open(ADJUDICATION_CSV, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=adjudication_rows[0].keys())
        writer.writeheader()
        writer.writerows(adjudication_rows)
    print(f"Exported: {ADJUDICATION_CSV} ({len(adjudication_rows)} rows)")

    print("=== Successfully Generated Complete Human Annotation Package ===")


if __name__ == '__main__':
    main()
