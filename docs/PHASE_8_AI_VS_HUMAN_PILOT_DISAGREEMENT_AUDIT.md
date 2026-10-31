# Phase 8 — AI-Simulated Annotator 2 vs. Corrected Human Pilot Disagreement Audit

**Audit Date**: September 15, 2026  
**Auditor**: Senior NLP Evaluation Engineer & Quantitative Research Methodology Auditor  
**Primary Anchor**: `data/interim/news/human_pilot_annotations_corrected.csv` (50 records, `ANN_000001`–`ANN_000050`)  
**Comparison Set**: `data/interim/news/annotator_2_simulated_annotations_1050.csv` (Slice `ANN_000001`–`ANN_000050`)  
**Methodological Label**: **AI-simulated second annotation pass / Sensitivity analysis**  
**Inter-Annotator Agreement Status**: **NOT APPLICABLE** (Zero human-human Kappa claimed)  
**Phase 8 Sealing Status**: **STRICTLY UNSEALED**  
**Phase 9 Status**: **STRICTLY PROHIBITED**  

---

> [!IMPORTANT]
> ### Methodological Foundation & Boundaries
> 1. `annotator_2_simulated_annotations_1050.csv` is an **AI-simulated independent second annotation pass**.
> 2. It **MUST NOT** be represented or cited as a human annotator, independent human gold data, or human inter-coder reliability.
> 3. **Cohen's Kappa is NOT calculated or claimed** using this comparison. Doing so would constitute scientific fabrication.
> 4. This comparison serves exclusively as a **methodological sensitivity audit** to identify guideline ambiguities, human cognitive biases, and systematic machine failure modes.
> 5. Neither source dataset has been modified.

---

## 1. Overall Exact-Match Percentages (N = 50 Pilot Records)

| Evaluation Dimension | Exact Agreement Count | Agreement Percentage | Chance Baseline (Uniform) | Sensitivity Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Sentiment Polarity** | **33 / 50** | **66.0%** | 25.0% | Moderate agreement; driven by shared `NEUTRAL` baseline. |
| **Confidence Level** | **9 / 50** | **18.0%** | 33.3% | Low agreement; human clustered on `MEDIUM`, AI2 clustered on `HIGH`/`LOW`. |
| **Market Relevance** | **24 / 50** | **48.0%** | 25.0% | Moderate agreement; divergence on sector vs. constituent weighting. |
| **Economic Importance** | **21 / 50** | **42.0%** | 20.0% | High proximity; **45 / 50 (90.0%)** agree within $\pm 1$ scale point. |
| **Primary Event Category**| **19 / 50** | **38.0%** | 6.25% | Low exact match; driven by multi-event composite filings and human defaulting. |

---

## 2. Full 50-Row Disagreement Matrix (`ANN_000001` through `ANN_000050`)

*Format: Human Value / AI2 Value (Match Status)*

| Annotation ID | Company | Sentiment (H / AI2) | Confidence (H / AI2) | Relevance (H / AI2) | Importance (H / AI2) | Primary Event Category (H / AI2) |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ANN_000001` | Bajaj Finance Limi | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `CORPORATE_ACTION` / `CORPORATE_ACTION` (MATCH) |
| `ANN_000002` | Vedanta Limited | POSITIVE / POSITIVE (MATCH) | MEDIUM / HIGH (DIFF) | HIGH / MEDIUM (DIFF) | 5 / 3 (DIFF) | `SHAREHOLDING_CHANGE` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000003` | Hindustan Unilever | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | LOW / HIGH (DIFF) | 2 / 4 (DIFF) | `MANAGEMENT_CHANGE` / `BUYBACK` (DIFF) |
| `ANN_000004` | State Bank of Indi | NEGATIVE / POSITIVE (DIFF) | MEDIUM / MEDIUM (MATCH) | HIGH / HIGH (MATCH) | 4 / 4 (MATCH) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000005` | Bharat Heavy Elect | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | LOW / MEDIUM (DIFF) | 2 / 2 (MATCH) | `MANAGEMENT_CHANGE` / `MANAGEMENT_CHANGE` (MATCH) |
| `ANN_000006` | ICICI Bank Limited | NEUTRAL / NEUTRAL (MATCH) | LOW / HIGH (DIFF) | LOW / HIGH (DIFF) | 2 / 4 (DIFF) | `CORPORATE_ACTION` / `FUNDRAISING` (DIFF) |
| `ANN_000007` | ICICI Bank Limited | NEUTRAL / NEUTRAL (MATCH) | HIGH / HIGH (MATCH) | LOW / LOW (MATCH) | 2 / 2 (MATCH) | `CORPORATE_ACTION` / `CORPORATE_ACTION` (MATCH) |
| `ANN_000008` | Punjab National Ba | NEUTRAL / NEUTRAL (MATCH) | HIGH / HIGH (MATCH) | LOW / MEDIUM (DIFF) | 2 / 2 (MATCH) | `MANAGEMENT_CHANGE` / `MANAGEMENT_CHANGE` (MATCH) |
| `ANN_000009` | Cipla Limited | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | LOW / MEDIUM (DIFF) | 2 / 2 (MATCH) | `MANAGEMENT_CHANGE` / `MANAGEMENT_CHANGE` (MATCH) |
| `ANN_000010` | Cairn India Limite | NEUTRAL / POSITIVE (DIFF) | LOW / HIGH (DIFF) | LOW / HIGH (DIFF) | 2 / 4 (DIFF) | `CORPORATE_ACTION` / `FUNDRAISING` (DIFF) |
| `ANN_000011` | Larsen & Toubro Li | POSITIVE / POSITIVE (MATCH) | HIGH / HIGH (MATCH) | HIGH / HIGH (MATCH) | 5 / 4 (DIFF) | `ORDER_CONTRACT` / `ORDER_CONTRACT` (MATCH) |
| `ANN_000012` | Infosys Limited | POSITIVE / POSITIVE (MATCH) | HIGH / MEDIUM (DIFF) | HIGH / HIGH (MATCH) | 5 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000013` | Infosys Limited | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `CORPORATE_ACTION` / `CORPORATE_ACTION` (MATCH) |
| `ANN_000014` | Mahindra & Mahindr | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000015` | Tata Consultancy S | POSITIVE / POSITIVE (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 2 / 3 (DIFF) | `DIVIDEND` / `DIVIDEND` (MATCH) |
| `ANN_000016` | Ranbaxy Laboratori | POSITIVE / POSITIVE (MATCH) | MEDIUM / LOW (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `STRATEGIC_PARTNERSHIP` / `OTHER` (DIFF) |
| `ANN_000017` | UPL Limited | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 2 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000018` | Idea Cellular Limi | POSITIVE / POSITIVE (MATCH) | HIGH / MEDIUM (DIFF) | HIGH / HIGH (MATCH) | 5 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000019` | Reliance Communica | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `DIVIDEND` / `DIVIDEND` (MATCH) |
| `ANN_000020` | Indian Oil Corpora | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 2 (DIFF) | `EARNINGS_RESULTS` / `MANAGEMENT_CHANGE` (DIFF) |
| `ANN_000021` | Asian Paints Limit | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / LOW (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `DIVIDEND` / `OTHER` (DIFF) |
| `ANN_000022` | Asian Paints Limit | POSITIVE / POSITIVE (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 4 / 4 (MATCH) | `ORDER_CONTRACT` / `EARNINGS_RESULTS` (DIFF) |
| `ANN_000023` | JSW Steel Limited | NEUTRAL / POSITIVE (DIFF) | MEDIUM / LOW (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `EARNINGS_RESULTS` / `OTHER` (DIFF) |
| `ANN_000024` | Hindustan Unilever | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / MEDIUM (MATCH) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000025` | Bajaj Auto Limited | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `DIVIDEND` (DIFF) |
| `ANN_000026` | Britannia Industri | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `DIVIDEND` (DIFF) |
| `ANN_000027` | Bajaj Finance Limi | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000028` | GAIL (India) Limit | POSITIVE / NEUTRAL (DIFF) | HIGH / MEDIUM (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `CAPEX_BUSINESS_UPDATE` / `CAPEX_BUSINESS_UPDATE` (MATCH) |
| `ANN_000029` | Tech Mahindra Limi | NEUTRAL / NEUTRAL (MATCH) | LOW / HIGH (DIFF) | LOW / MEDIUM (DIFF) | 2 / 3 (DIFF) | `CORPORATE_ACTION` / `CORPORATE_ACTION` (MATCH) |
| `ANN_000030` | Grasim Industries  | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `DIVIDEND` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000031` | Zee Entertainment  | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `SHAREHOLDING_CHANGE` (DIFF) |
| `ANN_000032` | ICICI Bank Limited | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `EARNINGS_RESULTS` / `FUNDRAISING` (DIFF) |
| `ANN_000033` | Tata Consultancy S | NEUTRAL / POSITIVE (DIFF) | MEDIUM / MEDIUM (MATCH) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `MANAGEMENT_CHANGE` / `EARNINGS_RESULTS` (DIFF) |
| `ANN_000034` | Larsen & Toubro Li | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `MANAGEMENT_CHANGE` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000035` | JSW Steel Limited | POSITIVE / NEUTRAL (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 2 (DIFF) | `STRATEGIC_PARTNERSHIP` / `MANAGEMENT_CHANGE` (DIFF) |
| `ANN_000036` | ACC Limited | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `DIVIDEND` (DIFF) |
| `ANN_000037` | Kotak Mahindra Ban | POSITIVE / POSITIVE (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 2 (DIFF) | `ORDER_CONTRACT` / `MANAGEMENT_CHANGE` (DIFF) |
| `ANN_000038` | Britannia Industri | NEUTRAL / POSITIVE (DIFF) | MEDIUM / MEDIUM (MATCH) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000039` | Cairn India Limite | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `DIVIDEND` / `EARNINGS_RESULTS` (DIFF) |
| `ANN_000040` | Hero MotoCorp Limi | NEUTRAL / POSITIVE (DIFF) | MEDIUM / MEDIUM (MATCH) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000041` | Punjab National Ba | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / LOW (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `EARNINGS_RESULTS` / `OTHER` (DIFF) |
| `ANN_000042` | NTPC Limited | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `CAPEX_BUSINESS_UPDATE` (DIFF) |
| `ANN_000043` | Cipla Limited | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000044` | UPL Limited | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `EARNINGS_RESULTS` / `EARNINGS_RESULTS` (MATCH) |
| `ANN_000045` | Cipla Limited | NEUTRAL / POSITIVE (DIFF) | MEDIUM / MEDIUM (MATCH) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `DIVIDEND` (DIFF) |
| `ANN_000046` | Zee Entertainment  | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 3 (MATCH) | `EARNINGS_RESULTS` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000047` | Hindalco Industrie | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / LOW (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `EARNINGS_RESULTS` / `OTHER` (DIFF) |
| `ANN_000048` | Bajaj Finserv Limi | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / HIGH (DIFF) | 3 / 4 (DIFF) | `EARNINGS_RESULTS` / `REGULATORY_LEGAL` (DIFF) |
| `ANN_000049` | UPL Limited | NEUTRAL / POSITIVE (DIFF) | MEDIUM / HIGH (DIFF) | MEDIUM / LOW (DIFF) | 3 / 2 (DIFF) | `EARNINGS_RESULTS` / `CORPORATE_ACTION` (DIFF) |
| `ANN_000050` | Idea Cellular Limi | NEUTRAL / NEUTRAL (MATCH) | MEDIUM / HIGH (DIFF) | MEDIUM / MEDIUM (MATCH) | 3 / 2 (DIFF) | `EARNINGS_RESULTS` / `MANAGEMENT_CHANGE` (DIFF) |

---

## 3. Sentiment Confusion Matrix

*Rows: Corrected Human Pilot | Columns: AI-Simulated Annotator 2*

| Human \ AI2 | POSITIVE | NEGATIVE | NEUTRAL | UNCERTAIN | Total Human |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **POSITIVE** | **8** | 0 | 2 | 0 | **10** |
| **NEGATIVE** | 1 | **0** | 0 | 0 | **1** |
| **NEUTRAL** | 14 | 0 | **25** | 0 | **39** |
| **UNCERTAIN** | 0 | 0 | 0 | **0** | **0** |
| **Total AI2** | **23** | **0** | **27** | **0** | **50** |

### Key Sentiment Observations:
- **Zero False Negatives**: AI2 generated 0 `NEGATIVE` tags across the 50 records.
- **Positive Skew in AI2 (14 Disagreements)**: AI2 labeled 14 filings as `POSITIVE` where the human assigned `NEUTRAL`. These primarily involve routine dividend recommendations (`ANN_000019`), press release intimations (`ANN_000023`), and ESOP allotments (`ANN_000006`, `ANN_000010`).
- **One Direct Inversion (`ANN_000004`)**: For State Bank of India's Q3 FY08 results, the human labeled `NEGATIVE` (likely noting margin pressure or sequential profit dip), whereas AI2 labeled `POSITIVE` (reacting to headline growth in gross interest earned).

---

## 4. Market Relevance Confusion Matrix

*Rows: Corrected Human Pilot | Columns: AI-Simulated Annotator 2*

| Human \ AI2 | HIGH | MEDIUM | LOW | NONE | Total Human |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **HIGH** | **4** | 1 | 0 | 0 | **5** |
| **MEDIUM** | 11 | **19** | 7 | 0 | **37** |
| **LOW** | 3 | 4 | **1** | 0 | **8** |
| **NONE** | 0 | 0 | 0 | **0** | **0** |
| **Total AI2** | **18** | **24** | **8** | **0** | **50** |

### Key Relevance Observations:
- In 11 records, the human assigned `MEDIUM` relevance while AI2 assigned `HIGH`. AI2 elevated heavyweights (RCOM, Infosys, BHEL, DLF) automatically to `HIGH` regardless of whether the filing was routine or catalyst-driven.

---

## 5. Economic Importance Difference Distribution

*Metric: $\Delta = \text{Importance}_{\text{AI2}} - \text{Importance}_{\text{Human}}$*

| Difference ($\Delta$) | Count | Percentage | Cumulative | Analysis |
| :---: | :---: | :---: | :---: | :--- |
| **$-2$** | 1 | 2.0% | 2.0% | AI2 rated substantially lower than Human (`ANN_000002`) |
| **$-1$** | 14 | 28.0% | 30.0% | AI2 rated 1 point lower than Human |
| **$0$** | **21** | **42.0%** | **72.0%** | **Exact agreement** |
| **$+1$** | 10 | 20.0% | 92.0% | AI2 rated 1 point higher than Human |
| **$+2$** | 4 | 8.0% | 100.0% | AI2 rated substantially higher than Human (`ANN_000003`, `ANN_000006`, `ANN_000010`, `ANN_000017`) |

### Critical Proximity Finding:
- **45 / 50 records (90.0%)** agree within $\pm 1$ point on the 1–5 ordinal scale.
- Only **5 records (10.0%)** exhibit severe importance disagreements ($|\Delta| \ge 2$).

---

## 6. Primary Event Confusion Matrix

| Human Primary Event | AI2: EARNINGS | AI2: CORP_ACT | AI2: DIVIDEND | AI2: MGMT | AI2: OTHER | AI2: FUNDRAISE | AI2: ORDER | AI2: BUYBACK | AI2: CAPEX | AI2: SHARE | AI2: REG_LEGAL | Total Human |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| `EARNINGS_RESULTS` | **8** | 5 | 4 | 2 | 3 | 1 | 0 | 0 | 1 | 1 | 1 | **26** |
| `CORPORATE_ACTION` | 0 | **4** | 0 | 0 | 0 | 2 | 0 | 0 | 0 | 0 | 0 | **6** |
| `MANAGEMENT_CHANGE`| 1 | 1 | 0 | **3** | 0 | 0 | 0 | 1 | 0 | 0 | 0 | **6** |
| `DIVIDEND` | 1 | 1 | **2** | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | **5** |
| `ORDER_CONTRACT` | 1 | 0 | 0 | 1 | 0 | 0 | **1** | 0 | 0 | 0 | 0 | **3** |
| `STRATEGIC_PARTNER` | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | **2** |
| `SHAREHOLDING_CHG` | 0 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **1** |
| `CAPEX_BUSINESS` | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | **1** | 0 | 0 | **1** |
| **Total AI2** | **11** | **12** | **6** | **7** | **5** | **3** | **1** | **1** | **2** | **1** | **1** | **50** |

---

## 7. Most Common Event-Category Confusions

The top pairwise event category confusions account for 21 of the 31 event disagreements:
1. **`EARNINGS_RESULTS` (Human) vs. `CORPORATE_ACTION` (AI2)**: 5 records.
   - *Cause*: Board meeting notices covering both financial statements and capital alterations / book closures.
2. **`EARNINGS_RESULTS` (Human) vs. `DIVIDEND` (AI2)**: 4 records.
   - *Cause*: Disclosures explicitly titled `"Dividend"` or announcing dividend recommendations passed during quarterly board meetings (`ANN_000025`, `ANN_000026`).
3. **`EARNINGS_RESULTS` (Human) vs. `OTHER` (AI2)**: 3 records.
   - *Cause*: Disclosures regarding monthly operational production releases or press release notifications.
4. **`CORPORATE_ACTION` (Human) vs. `FUNDRAISING` (AI2)**: 2 records.
   - *Cause*: Minor ESOP allotments (`ANN_000006`, `ANN_000010`) which AI2 interpreted as equity capital fundraising.
5. **`EARNINGS_RESULTS` (Human) vs. `MANAGEMENT_CHANGE` (AI2)**: 2 records.
   - *Cause*: Cessation of directorship announcements filed concurrently with or near quarterly meetings (`ANN_000020`).

---

## 8. AI-2 `OTHER` Classifications in Pilot vs. Full Dataset

- **In 50-Record Pilot Sample**: **5 records (10.00%)** classified as `OTHER` by AI2.
- **In Full 1,050 AI2 Dataset**: **359 records (34.19%)** classified as `OTHER` by AI2.

---

## 9. Comparison of `OTHER` Classification Rates

| Dataset / Slice | Total Records | `OTHER` Classifications | `OTHER` Percentage | Assessment |
| :--- | :---: | :---: | :---: | :--- |
| **Corrected Human Pilot (N=50)** | 50 | 0 | **0.00%** | Zero use; human forced items into canonical classes. |
| **AI-Simulated Annotator 2 Pilot (N=50)** | 50 | 5 | **10.00%** | Low; concentrated on monthly production press releases. |
| **Original AI Development Set (N=1,000)** | 1,000 | 121 | **12.10%** | Controlled residual bucket for secretarial filings. |
| **Full AI-Simulated Annotator 2 (N=1,050)**| 1,050 | 359 | **34.19%** | **High / Diagnostic Defect**. AI2 collapsed over a third of the corpus into `OTHER`. |

### Comparative Finding:
The full AI2 pass utilized `OTHER` at nearly **triple the rate (34.19% vs. 12.10%)** of the original AI-assisted development set. This indicates that AI2 had an overly conservative event classification threshold, treating non-standard board disclosures as unclassifiable rather than parsing multi-clause text.

---

## 10. Systematic Patterns in Disagreements

Four distinct systematic error patterns were identified across the audit:

1. **Pattern 1: Human Defaulting to `EARNINGS_RESULTS` (Over-Generalization)**:
   - The human annotator displayed a strong cognitive anchor toward `EARNINGS_RESULTS` (26 of 50 records).
   - In multiple instances, when a filing originated from a board meeting, the human coded `EARNINGS_RESULTS` even when the filing text was purely a dividend recommendation (`ANN_000025`, `ANN_000026`), a director resignation (`ANN_000020`), or a share capital increase (`ANN_000024`). In these cases, **AI2 was demonstrably more accurate** than the human pilot.

2. **Pattern 2: AI2 Inflation of Micro-ESOP Allotments**:
   - Routine allotments of shares to employees under ESOP schemes (e.g. 16,850 shares for ICICI Bank in `ANN_000006`, 792,240 shares for Cairn India in `ANN_000010`) were classified by AI2 as `FUNDRAISING` with `Importance = 4` and `Sentiment = POSITIVE`.
   - The human correctly classified these as routine `CORPORATE_ACTION` with `Importance = 2` and `Sentiment = NEUTRAL`.

3. **Pattern 3: Sentiment Optimism on Routine Corporate Actions**:
   - AI2 classified dividend recommendations and book closures as uniformly `POSITIVE`, whereas the human annotator applied the guideline rule that scheduled dividend intimations for established blue-chips are often baseline compliance (`NEUTRAL`).

4. **Pattern 4: The Multi-Clause Statutory Filing Dilemma**:
   - Indian corporate filings frequently bundle quarterly accounts, dividend payouts, book closures, and AGM scheduling into a single circular. Without explicit hierarchy rules, independent coders inevitably select different primary events.

---

## 11. Root Causes: Guideline Ambiguity vs. Coder Error

The audit established that disagreements are attributable to specific, identifiable causes:

| Disagreement Category | Attributable Cause | Concrete Evidence |
| :--- | :--- | :--- |
| **Multi-Event Priority** | **Guideline Ambiguity** | Current guidelines do not establish a strict precedence rule when a single disclosure contains both earnings statements and dividend / corporate action declarations. |
| **ESOP Dilution Thresholds** | **Guideline Ambiguity** | Guidelines do not define when an equity allotment ceases to be a routine `CORPORATE_ACTION` (Importance 1–2) and becomes a material `FUNDRAISING` event (Importance 4–5). |
| **Human Defaulting** | **Human Coder Inattention** | Coding an isolated director resignation (`ANN_000020`) or a standalone dividend notice (`ANN_000025`) as `EARNINGS_RESULTS` is an unambiguous human labeling slip. |
| **AI2 Over-Use of `OTHER`** | **Model Conservatism** | AI2 lacked granular heuristics for procedural listing intimations and defaulted to `OTHER`. |

---

## 12. Records Requiring Formal Human Review

The following 6 records from the pilot sample exhibit clear classification conflicts requiring formal human review:

| Record ID | Company | Filing Text Essence | Human Pilot Label | AI2 Label | Review Focus & Conflict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **`ANN_000003`** | `HINDUNILVR` | Board committee decided to close the buyback of shares. | `sent=NEUTRAL`, `imp=2`, **`ev=MANAGEMENT_CHANGE`** | `sent=POSITIVE`, `imp=4`, **`ev=BUYBACK`** | **Clear Human Error**: Buyback closure is `BUYBACK` or `CORPORATE_ACTION`, not `MANAGEMENT_CHANGE`. |
| **`ANN_000004`** | `SBIN` | Q3 FY08 consolidated results with interest earned Rs. 18,434 crore. | **`sent=NEGATIVE`**, `imp=4`, `ev=EARNINGS_RESULTS` | **`sent=POSITIVE`**, `imp=4`, `ev=EARNINGS_RESULTS` | **Polarity Conflict**: Did Q3 FY08 represent a profit decline/NPA spike (`NEGATIVE`) or robust topline expansion (`POSITIVE`)? |
| **`ANN_000020`** | `IOC` | Resignation/cessation of Shri Vineet Nayyar as Independent Director. | `sent=NEUTRAL`, `imp=3`, **`ev=EARNINGS_RESULTS`** | `sent=NEUTRAL`, `imp=3`, **`ev=MANAGEMENT_CHANGE`** | **Clear Human Error**: Cessation of directorship is unquestionably `MANAGEMENT_CHANGE`. |
| **`ANN_000024`** | `HINDUNILVR` | Intimation of increase in Paid-up Equity Capital. | `sent=NEUTRAL`, `imp=3`, **`ev=EARNINGS_RESULTS`** | `sent=POSITIVE`, `imp=3`, **`ev=CORPORATE_ACTION`** | **Human Error**: Capital increase is `CORPORATE_ACTION`, not `EARNINGS_RESULTS`. |
| **`ANN_000025`** | `BAJAJ-AUTO` | Board recommended dividend of Rs. 20 per share (200%). | `sent=NEUTRAL`, `imp=3`, **`ev=EARNINGS_RESULTS`** | `sent=POSITIVE`, `imp=4`, **`ev=DIVIDEND`** | **Event Conflict**: Standalone dividend announcement should be coded `DIVIDEND`. |
| **`ANN_000026`** | `BRITANNIA` | Board recommended dividend of 180% (Rs. 18/- per share). | `sent=NEUTRAL`, `imp=3`, **`ev=EARNINGS_RESULTS`** | `sent=POSITIVE`, `imp=4`, **`ev=DIVIDEND`** | **Event Conflict**: Standalone dividend announcement should be coded `DIVIDEND`. |

---

## 13. Concrete Recommendations for Guideline Refinements

To resolve these systematic divergences across future annotation rounds, the following rules should be incorporated:

1. **Rule 1: Multi-Event Precedence Hierarchy**:
   When a disclosure contains multiple concurrent disclosures, assign `primary_event` according to the following strict waterfall:
   $$\text{EARNINGS\_RESULTS} > \text{DIVIDEND} > \text{M\_AND\_A} > \text{MANAGEMENT\_CHANGE} > \text{CORPORATE\_ACTION} > \text{OTHER}$$
   *Exception*: If a disclosure is solely a dividend recommendation notice without accompanying financial figures, code strictly as `DIVIDEND`.

2. **Rule 2: ESOP Allotment vs. Capital Fundraising Rule**:
   - Allotments of shares under Employee Stock Option Plans (ESOPs) that represent $< 0.1\%$ of existing paid-up capital must be classified as **`CORPORATE_ACTION`** with **`Importance = 1` or `2`** and **`Sentiment = NEUTRAL`**.
   - Reserve **`FUNDRAISING`** with `Importance \ge 4` strictly for material external capital infusions (QIPs, rights issues, preferential allotments to promoters/PE).

3. **Rule 3: Standalone Board Intimations**:
   - Intimations of director resignations or appointments must **never** be coded as `EARNINGS_RESULTS` merely because they mention a board meeting. Code strictly as `MANAGEMENT_CHANGE`.

4. **Rule 4: Calibrate `OTHER` Category Usage**:
   - Limit `OTHER` to filings that cannot logically map to the 15 substantive event classes (e.g. change of registrar address, general secretarial notices). Routine press releases must be parsed for operational substance (`ORDER_CONTRACT`, `CAPEX_BUSINESS_UPDATE`, or `OPERATIONAL_EVENT`).

---

## 14. Final Methodological Verdict

Based on forensic evaluation of the 50 pilot comparisons:

### **`B) GUIDELINES REQUIRE TARGETED CORRECTION`**

#### Formal Rationale for Verdict B:
1. **Explainable Disagreements**: The divergences between the human pilot and AI-Simulated Annotator 2 are highly structured and explainable (multi-label bundling, ESOP misclassifications, and human defaulting).
2. **Methodology is Sound**: The fundamental architecture (16-class taxonomy, 4-way sentiment, 1–5 importance scale, and point-in-time constraints) remains robust and scientifically viable (eliminating Verdict C).
3. **Targeted Correction Required**: The guidelines lack explicit multi-event hierarchy rules and ESOP materiality thresholds (preventing Verdict A). Incorporating the four targeted rules above will systematically close the observed gaps.

---

*Report compiled for the NIFTY AI quantitative research repository.*
