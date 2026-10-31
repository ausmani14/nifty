"""Phase 8 Fresh Calibration Agreement Engine.

Compares:
- Annotator 1: data/interim/news/fresh_calibration_50_human_annotations_corrected.csv
- Annotator 2: data/interim/news/fresh_calibration_50_annotator_2_completed.csv

Computes chance-corrected inter-annotator agreement metrics:
- Sentiment: Cohen's Kappa, raw concordance
- Primary Event: Multiclass Cohen's Kappa, raw concordance
- Relevance: Multiclass Cohen's Kappa, raw concordance
- Importance: Linearly Weighted Cohen's Kappa (kappa_w), exact agreement
- Secondary Events: Jaccard set similarity

Evaluates formal gate threshold (Kappa >= 0.75).
Generates adjudication queue if disagreements exist.
"""

import argparse
import csv
import os
import sys
from collections import Counter
from typing import Dict, List, Tuple

def compute_cohens_kappa(labels_1: List[str], labels_2: List[str]) -> Tuple[float, float]:
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

def compute_linear_weighted_kappa(values_1: List[int], values_2: List[int], min_val: int = 1, max_val: int = 5) -> Tuple[float, float]:
    assert len(values_1) == len(values_2)
    n = len(values_1)
    if n == 0:
        return 0.0, 0.0

    k = max_val - min_val + 1
    matrix = [[0] * k for _ in range(k)]
    for v1, v2 in zip(values_1, values_2):
        matrix[v1 - min_val][v2 - min_val] += 1

    weights = [[0.0] * k for _ in range(k)]
    max_diff = k - 1
    for i in range(k):
        for j in range(k):
            weights[i][j] = 1.0 - abs(i - j) / max_diff

    p_o = sum(weights[i][j] * matrix[i][j] for i in range(k) for j in range(k)) / n

    row_sums = [sum(matrix[i][j] for j in range(k)) for i in range(k)]
    col_sums = [sum(matrix[j][i] for j in range(k)) for i in range(k)]

    p_e = sum(weights[i][j] * (row_sums[i] / n) * (col_sums[j] / n) for i in range(k) for j in range(k))

    if p_e >= 1.0:
        kappa_w = 1.0
    else:
        kappa_w = (p_o - p_e) / (1.0 - p_e)

    exact_p_o = sum(matrix[i][i] for i in range(k)) / n
    return round(kappa_w, 4), round(exact_p_o, 4)

def run_calibration_agreement(ann1_path: str, ann2_path: str, out_disagreements: str, out_adjudication: str):
    if not os.path.exists(ann2_path):
        print(f"ERROR: Annotator 2 completed file not found: {ann2_path}")
        print("Status: PHASE 8 INCOMPLETE — SECOND HUMAN ANNOTATION PENDING")
        return False

    with open(ann1_path, "r", encoding="utf-8") as f:
        rows1 = list(csv.DictReader(f))
    with open(ann2_path, "r", encoding="utf-8") as f:
        rows2 = list(csv.DictReader(f))

    assert len(rows1) == 50, f"Expected 50 rows in Ann1, got {len(rows1)}"
    assert len(rows2) == 50, f"Expected 50 rows in Ann2, got {len(rows2)}"

    dict1 = {r["calibration_id"]: r for r in rows1}
    dict2 = {r["calibration_id"]: r for r in rows2}

    for cid, r in dict2.items():
        for fld in ["sentiment", "confidence", "relevance", "importance", "primary_event"]:
            val = r.get(fld, "").strip()
            if not val:
                print(f"ERROR: Record {cid} in Annotator 2 has empty field '{fld}'")
                return False

    cids = sorted(list(dict1.keys()))
    sent1 = [dict1[c]["sentiment"] for c in cids]
    sent2 = [dict2[c]["sentiment"] for c in cids]
    sent_k, sent_po = compute_cohens_kappa(sent1, sent2)

    ev1 = [dict1[c]["primary_event"] for c in cids]
    ev2 = [dict2[c]["primary_event"] for c in cids]
    ev_k, ev_po = compute_cohens_kappa(ev1, ev2)

    rel1 = [dict1[c]["relevance"] for c in cids]
    rel2 = [dict2[c]["relevance"] for c in cids]
    rel_k, rel_po = compute_cohens_kappa(rel1, rel2)

    imp1 = [int(dict1[c]["importance"]) for c in cids]
    imp2 = [int(dict2[c]["importance"]) for c in cids]
    imp_kw, imp_po = compute_linear_weighted_kappa(imp1, imp2)

    disagreements = []
    for c in cids:
        r1 = dict1[c]
        r2 = dict2[c]
        has_dis = (
            r1["sentiment"] != r2["sentiment"] or
            r1["primary_event"] != r2["primary_event"] or
            r1["relevance"] != r2["relevance"] or
            r1["importance"] != r2["importance"]
        )
        if has_dis:
            disagreements.append({
                "calibration_id": c,
                "source_record_id": r1["source_record_id"],
                "company": r1["company"],
                "headline": r1["headline"],
                "ann1_sentiment": r1["sentiment"],
                "ann2_sentiment": r2["sentiment"],
                "sentiment_match": r1["sentiment"] == r2["sentiment"],
                "ann1_event": r1["primary_event"],
                "ann2_event": r2["primary_event"],
                "event_match": r1["primary_event"] == r2["primary_event"],
                "ann1_importance": r1["importance"],
                "ann2_importance": r2["importance"],
                "importance_match": r1["importance"] == r2["importance"],
                "ann1_relevance": r1["relevance"],
                "ann2_relevance": r2["relevance"],
                "relevance_match": r1["relevance"] == r2["relevance"],
            })

    print("================================================================================")
    print("PHASE 8 FRESH CALIBRATION HUMAN-VS-HUMAN AGREEMENT REPORT")
    print("================================================================================")
    print(f"Sample Size: 50 Records (CAL2_000001 - CAL2_000050)")
    print(f"Sentiment Kappa:          {sent_k:.4f} (Observed: {sent_po*100:.1f}%)")
    print(f"Primary Event Kappa:      {ev_k:.4f} (Observed: {ev_po*100:.1f}%)")
    print(f"Relevance Kappa:          {rel_k:.4f} (Observed: {rel_po*100:.1f}%)")
    print(f"Importance Weighted Kappa:{imp_kw:.4f} (Exact: {imp_po*100:.1f}%)")
    print(f"Total Disputed Records:   {len(disagreements)} / 50 ({len(disagreements)/50*100:.1f}%)")

    passed_gate = (sent_k >= 0.75) and (ev_k >= 0.75) and (imp_kw >= 0.75)
    print(f"Calibration Gate Status:  {'PASSED' if passed_gate else 'FAILED (Kappa < 0.75)'}")
    print("================================================================================")

    if out_disagreements and disagreements:
        os.makedirs(os.path.dirname(out_disagreements), exist_ok=True)
        with open(out_disagreements, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(disagreements[0].keys()))
            writer.writeheader()
            writer.writerows(disagreements)
        print(f"Exported disagreements to: {out_disagreements}")

    if out_adjudication and disagreements:
        os.makedirs(os.path.dirname(out_adjudication), exist_ok=True)
        adj_fields = [
            "calibration_id", "source_record_id", "company", "headline",
            "ann1_sentiment", "ann2_sentiment", "adjudicated_sentiment",
            "ann1_event", "ann2_event", "adjudicated_event",
            "ann1_importance", "ann2_importance", "adjudicated_importance",
            "ann1_relevance", "ann2_relevance", "adjudicated_relevance",
            "adjudication_rationale", "adjudicator"
        ]
        with open(out_adjudication, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=adj_fields)
            writer.writeheader()
            for d in disagreements:
                writer.writerow({
                    "calibration_id": d["calibration_id"],
                    "source_record_id": d["source_record_id"],
                    "company": d["company"],
                    "headline": d["headline"],
                    "ann1_sentiment": d["ann1_sentiment"],
                    "ann2_sentiment": d["ann2_sentiment"],
                    "adjudicated_sentiment": "",
                    "ann1_event": d["ann1_event"],
                    "ann2_event": d["ann2_event"],
                    "adjudicated_event": "",
                    "ann1_importance": d["ann1_importance"],
                    "ann2_importance": d["ann2_importance"],
                    "adjudicated_importance": "",
                    "ann1_relevance": d["ann1_relevance"],
                    "ann2_relevance": d["ann2_relevance"],
                    "adjudicated_relevance": "",
                    "adjudication_rationale": "",
                    "adjudicator": ""
                })
        print(f"Prepared adjudication template: {out_adjudication}")

    return passed_gate

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Phase 8 Fresh Calibration Agreement Engine")
    parser.add_argument("--ann1", default="data/interim/news/fresh_calibration_50_human_annotations_corrected.csv")
    parser.add_argument("--ann2", default="data/interim/news/fresh_calibration_50_annotator_2_completed.csv")
    parser.add_argument("--disagreements", default="data/interim/news/fresh_calibration_50_disagreements.csv")
    parser.add_argument("--adjudication", default="data/interim/news/fresh_calibration_50_adjudication_template.csv")
    args = parser.parse_args()

    run_calibration_agreement(args.ann1, args.ann2, args.disagreements, args.adjudication)
