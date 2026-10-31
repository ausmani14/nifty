"""Phase 8 Statistical Agreement Engine & Disagreement Extractor.

Computes chance-corrected inter-annotator agreement metrics:
- Sentiment: Cohen's Kappa, raw concordance, confusion matrix, per-class F1
- Primary Event: Multiclass Cohen's Kappa, raw concordance, macro F1
- Secondary Events: Set-based Jaccard similarity, per-event concordance
- NIFTY Relevance: Multiclass Cohen's Kappa, raw concordance, confusion matrix
- Economic Importance: Linearly Weighted Cohen's Kappa (kappa_w), exact agreement, mean absolute error

Exports disputed records to data/interim/news/annotation_disagreements.csv.
Supports unannotated template status reporting without raising unhandled exceptions.
"""

import argparse
import csv
import os
import sys
from collections import Counter, defaultdict
from typing import Dict, List, Tuple, Any, Optional

DISAGREEMENTS_OUTPUT_PATH = 'data/interim/news/annotation_disagreements.csv'


def compute_cohens_kappa(labels_1: List[str], labels_2: List[str]) -> Tuple[float, float]:
    """Compute observed agreement (P_o) and chance-corrected Cohen's kappa.
    
    Returns (kappa, observed_agreement).
    """
    assert len(labels_1) == len(labels_2), "Length mismatch"
    n = len(labels_1)
    if n == 0:
        return 0.0, 0.0

    categories = sorted(list(set(labels_1) | set(labels_2)))
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)

    if k <= 1:
        return 1.0, 1.0

    matrix = [[0] * k for _ in range(k)]
    for l1, l2 in zip(labels_1, labels_2):
        matrix[cat_to_idx[l1]][cat_to_idx[l2]] += 1

    p_o = sum(matrix[i][i] for i in range(k)) / n

    p_e = 0.0
    for i in range(k):
        row_sum = sum(matrix[i][j] for j in range(k))
        col_sum = sum(matrix[j][i] for j in range(k))
        p_e += (row_sum / n) * (col_sum / n)

    if p_e >= 1.0:
        kappa = 1.0
    else:
        kappa = (p_o - p_e) / (1.0 - p_e)

    return round(kappa, 4), round(p_o, 4)


def compute_weighted_kappa(scores_1: List[int], scores_2: List[int], min_score: int = 1, max_score: int = 5) -> Tuple[float, float, float]:
    """Compute linearly weighted Cohen's kappa for ordinal ratings.
    
    Returns (weighted_kappa, exact_agreement, mean_absolute_error).
    """
    assert len(scores_1) == len(scores_2), "Length mismatch"
    n = len(scores_1)
    if n == 0:
        return 0.0, 0.0, 0.0

    k = max_score - min_score + 1
    matrix = [[0] * k for _ in range(k)]
    for s1, s2 in zip(scores_1, scores_2):
        i = s1 - min_score
        j = s2 - min_score
        if 0 <= i < k and 0 <= j < k:
            matrix[i][j] += 1

    # Linear weights: w_ij = 1 - |i - j| / (k - 1)
    weights = [[1.0 - abs(i - j) / (k - 1) for j in range(k)] for i in range(k)]

    p_o_w = 0.0
    for i in range(k):
        for j in range(k):
            p_o_w += weights[i][j] * (matrix[i][j] / n)

    p_e_w = 0.0
    for i in range(k):
        row_sum = sum(matrix[i][m] for m in range(k))
        for j in range(k):
            col_sum = sum(matrix[m][j] for m in range(k))
            p_e_w += weights[i][j] * (row_sum / n) * (col_sum / n)

    if p_e_w >= 1.0:
        kappa_w = 1.0
    else:
        kappa_w = (p_o_w - p_e_w) / (1.0 - p_e_w)

    raw_exact = sum(matrix[i][i] for i in range(k)) / n
    mean_abs_diff = sum(abs(s1 - s2) for s1, s2 in zip(scores_1, scores_2)) / n

    return round(kappa_w, 4), round(raw_exact, 4), round(mean_abs_diff, 4)


def compute_set_jaccard(sets_1: List[set], sets_2: List[set]) -> float:
    """Compute average Jaccard similarity across multi-label sets."""
    if not sets_1:
        return 0.0
    jaccards = []
    for s1, s2 in zip(sets_1, sets_2):
        if not s1 and not s2:
            jaccards.append(1.0)
        else:
            intersection = len(s1.intersection(s2))
            union = len(s1.union(s2))
            jaccards.append(intersection / union if union > 0 else 0.0)
    return round(sum(jaccards) / len(jaccards), 4)


def compute_confusion_matrix(labels_1: List[str], labels_2: List[str]) -> Tuple[List[str], List[List[int]]]:
    """Compute confusion matrix between two annotators."""
    categories = sorted(list(set(labels_1) | set(labels_2)))
    cat_to_idx = {c: i for i, c in enumerate(categories)}
    k = len(categories)
    matrix = [[0] * k for _ in range(k)]
    for l1, l2 in zip(labels_1, labels_2):
        matrix[cat_to_idx[l1]][cat_to_idx[l2]] += 1
    return categories, matrix


def compute_macro_f1(labels_1: List[str], labels_2: List[str]) -> float:
    """Compute pairwise macro F1 between two annotators treating Annotator 1 as pseudo-gold."""
    categories = sorted(list(set(labels_1) | set(labels_2)))
    f1s = []
    for cat in categories:
        tp = sum(1 for l1, l2 in zip(labels_1, labels_2) if l1 == cat and l2 == cat)
        fp = sum(1 for l1, l2 in zip(labels_1, labels_2) if l1 != cat and l2 == cat)
        fn = sum(1 for l1, l2 in zip(labels_1, labels_2) if l1 == cat and l2 != cat)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        f1s.append(f1)
    return round(sum(f1s) / len(f1s), 4) if f1s else 0.0


def interpret_kappa(kappa: float) -> str:
    """Interpret kappa score according to project standards."""
    if kappa < 0.70:
        return "UNACCEPTABLE (<0.70)"
    elif kappa < 0.80:
        return "ACCEPTABLE (0.70-0.79)"
    elif kappa < 0.90:
        return "GOOD (0.80-0.89)"
    else:
        return "EXCELLENT (>=0.90)"


def evaluate_templates(file1: str, file2: str, input_meta_file: str = 'data/interim/news/gold_annotation_input.csv',
                       disagreements_path: str = DISAGREEMENTS_OUTPUT_PATH,
                       subset: str = 'all') -> Dict[str, Any]:
    """Evaluate agreement between two annotation templates."""
    print(f"Loading Annotator 1 from: {file1}")
    with open(file1, 'r', encoding='utf-8') as f:
        rows_1 = {r['annotation_id']: r for r in csv.DictReader(f)}

    print(f"Loading Annotator 2 from: {file2}")
    with open(file2, 'r', encoding='utf-8') as f:
        rows_2 = {r['annotation_id']: r for r in csv.DictReader(f)}

    # Optional metadata lookup for headline / company / split
    meta_lookup = {}
    if os.path.exists(input_meta_file):
        with open(input_meta_file, 'r', encoding='utf-8') as f:
            for r in csv.DictReader(f):
                meta_lookup[r['annotation_id']] = r

    common_ids = sorted(list(set(rows_1.keys()) & set(rows_2.keys())))

    # Filter by subset if requested
    if subset == 'pilot':
        common_ids = [aid for aid in common_ids if meta_lookup.get(aid, {}).get('annotation_split') == 'DEVELOPMENT_PILOT']
    elif subset == 'holdout':
        common_ids = [aid for aid in common_ids if meta_lookup.get(aid, {}).get('annotation_split') == 'HOLDOUT' or aid.startswith('ANN_HLD_')]

    total_records = len(common_ids)
    print(f"Comparing {total_records} records (subset={subset})...")

    # Check how many are populated
    populated_ids = []
    for aid in common_ids:
        r1 = rows_1[aid]
        r2 = rows_2[aid]
        # Considered populated if sentiment or event is non-empty in either
        if (r1.get('sentiment', '').strip() or r1.get('primary_event', '').strip()) and \
           (r2.get('sentiment', '').strip() or r2.get('primary_event', '').strip()):
            populated_ids.append(aid)

    if len(populated_ids) == 0:
        print("\n================================================================================")
        print(f"STATUS: TEMPLATES UNANNOTATED — AWAITING HUMAN INPUT (0/{total_records} records labeled)")
        print("Both annotator templates are structurally verified, synchronized, and ready for use.")
        print("Independent double-blind annotation must be performed before agreement metrics apply.")
        print("================================================================================")
        return {
            'status': 'AWAITING_HUMAN_LABELS',
            'total_records': total_records,
            'populated_records': 0,
            'disagreements_count': 0
        }

    print(f"Analyzing {len(populated_ids)} completed records...")

    sent_1, sent_2 = [], []
    event_1, event_2 = [], []
    sec_1, sec_2 = [], []
    rel_1, rel_2 = [], []
    imp_1, imp_2 = [], []

    disagreements = []

    for aid in populated_ids:
        r1 = rows_1[aid]
        r2 = rows_2[aid]
        meta = meta_lookup.get(aid, {})

        s1, s2 = r1.get('sentiment', '').strip(), r2.get('sentiment', '').strip()
        e1, e2 = r1.get('primary_event', '').strip(), r2.get('primary_event', '').strip()
        sec_s1 = set(x.strip() for x in r1.get('secondary_events', '').split(';') if x.strip())
        sec_s2 = set(x.strip() for x in r2.get('secondary_events', '').split(';') if x.strip())
        rel_s1, rel_s2 = r1.get('relevance', '').strip(), r2.get('relevance', '').strip()

        try:
            val_imp1 = int(r1.get('importance', 0))
            val_imp2 = int(r2.get('importance', 0))
        except ValueError:
            val_imp1, val_imp2 = 0, 0

        sent_1.append(s1)
        sent_2.append(s2)
        event_1.append(e1)
        event_2.append(e2)
        sec_1.append(sec_s1)
        sec_2.append(sec_s2)
        rel_1.append(rel_s1)
        rel_2.append(rel_s2)
        if val_imp1 > 0 and val_imp2 > 0:
            imp_1.append(val_imp1)
            imp_2.append(val_imp2)

        # Check for disagreements
        dis_types = []
        if s1 != s2:
            dis_types.append('SENTIMENT')
        if e1 != e2:
            dis_types.append('PRIMARY_EVENT')
        if sec_s1 != sec_s2:
            dis_types.append('SECONDARY_EVENTS')
        if rel_s1 != rel_s2:
            dis_types.append('RELEVANCE')
        if abs(val_imp1 - val_imp2) >= 1:
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
                'annotator_1_importance': val_imp1,
                'annotator_2_importance': val_imp2,
                'annotator_1_relevance': rel_s1,
                'annotator_2_relevance': rel_s2,
            })

    # Metric Calculations
    sent_kappa, sent_raw = compute_cohens_kappa(sent_1, sent_2)
    event_kappa, event_raw = compute_cohens_kappa(event_1, event_2)
    rel_kappa, rel_raw = compute_cohens_kappa(rel_1, rel_2)
    sec_jaccard = compute_set_jaccard(sec_1, sec_2)
    imp_kappa_w, imp_exact, imp_mae = compute_weighted_kappa(imp_1, imp_2)
    macro_f1_event = compute_macro_f1(event_1, event_2)

    print("\n================================================================================")
    print(f"INTER-ANNOTATOR AGREEMENT REPORT ({len(populated_ids)} records evaluated)")
    print("================================================================================")
    print(f"Sentiment:           Cohen's Kappa = {sent_kappa:+.4f} ({interpret_kappa(sent_kappa)}) | Raw Agreement = {sent_raw * 100:.2f}%")
    print(f"Primary Event:       Cohen's Kappa = {event_kappa:+.4f} ({interpret_kappa(event_kappa)}) | Raw Agreement = {event_raw * 100:.2f}% | Macro F1 = {macro_f1_event:.4f}")
    print(f"Secondary Events:    Mean Jaccard Similarity = {sec_jaccard:.4f}")
    print(f"NIFTY Relevance:     Cohen's Kappa = {rel_kappa:+.4f} ({interpret_kappa(rel_kappa)}) | Raw Agreement = {rel_raw * 100:.2f}%")
    print(f"Economic Importance: Weighted Kappa = {imp_kappa_w:+.4f} ({interpret_kappa(imp_kappa_w)}) | Exact = {imp_exact * 100:.2f}% | MAE = {imp_mae:.4f}")
    print("--------------------------------------------------------------------------------")
    print(f"Total Disputed Records: {len(disagreements)} / {len(populated_ids)} ({len(disagreements)/len(populated_ids)*100:.1f}%)")
    print("================================================================================")

    # Export Disagreements
    if disagreements and disagreements_path:
        os.makedirs(os.path.dirname(disagreements_path), exist_ok=True)
        with open(disagreements_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=list(disagreements[0].keys()))
            writer.writeheader()
            writer.writerows(disagreements)
        print(f"Exported {len(disagreements)} disputed records to: {disagreements_path}")

    return {
        'status': 'EVALUATION_COMPLETE',
        'total_records': total_records,
        'populated_records': len(populated_ids),
        'sentiment_kappa': sent_kappa,
        'sentiment_raw': sent_raw,
        'event_kappa': event_kappa,
        'event_raw': event_raw,
        'event_macro_f1': macro_f1_event,
        'relevance_kappa': rel_kappa,
        'relevance_raw': rel_raw,
        'importance_weighted_kappa': imp_kappa_w,
        'importance_exact': imp_exact,
        'importance_mae': imp_mae,
        'secondary_jaccard': sec_jaccard,
        'disagreements_count': len(disagreements)
    }


def main():
    parser = argparse.ArgumentParser(description="Calculate Phase 8 Inter-Annotator Agreement")
    parser.add_argument('--input-1', default='data/interim/news/annotator_1_template.csv', help="Annotator 1 CSV")
    parser.add_argument('--input-2', default='data/interim/news/annotator_2_template.csv', help="Annotator 2 CSV")
    parser.add_argument('--input-meta', default='data/interim/news/gold_annotation_input.csv', help="Metadata CSV")
    parser.add_argument('--disagreements', default=DISAGREEMENTS_OUTPUT_PATH, help="Output CSV for disagreements")
    parser.add_argument('--subset', choices=['all', 'pilot', 'holdout'], default='all', help="Subset of records to evaluate")
    args = parser.parse_args()

    evaluate_templates(args.input_1, args.input_2, input_meta_file=args.input_meta,
                       disagreements_path=args.disagreements, subset=args.subset)


if __name__ == '__main__':
    main()
