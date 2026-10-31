# NIFTY AI

A professional machine-learning research and paper-trading system designed to predict next-day movements of the **NIFTY 50** index on the National Stock Exchange of India (NSE).

---

## 1. Project Purpose & Objectives

The primary objective of **NIFTY AI** is to generate disciplined, quantitative next-trading-day predictions for the NIFTY 50 index:

1. **Directional Classification**: `UP` / `DOWN` / `SIDEWAYS`
2. **Regression Estimates**: Expected next-day return (%) and closing price level

### Dual Prediction Snapshots

To capture both finalized domestic market sessions and overnight global developments, the system is designed around two strict prediction snapshots:

* **3:40 PM IST Snapshot (Post-Market Close)**:
  * Triggered after market closing (3:30 PM IST).
  * Uses finalized same-day domestic price action, sector breadth, derivatives/open interest, and domestic institutional data.
* **8:50 AM IST Snapshot (Pre-Market Open)**:
  * Triggered before market opening (9:00 AM IST).
  * Ingests overnight global market trends (US/European closes, Asian early action, GIFT Nifty, crude oil, currency/forex) and overnight financial news/NLP sentiment.

---

## 2. Current Development Stage

**Status: Stage 0 — Project Foundation (Pre-Alpha)**

* Modular project structure initialized.
* Modern package management via `pyproject.toml` using `src/` layout.
* Virtual environment configured with foundational dependencies (`pytest`, `python-dotenv`).
* Baseline test suite and safety checks established.
* **Note**: No models, data downloads, live API calls, or trading logic have been implemented yet.

---

## 3. Planned Architecture

The system follows a strict separation of concerns across dedicated modules:

```
src/nifty_ai/
├── config/           # Environment and operational configuration
├── data/             # Ingestion pipelines, schema validation, raw/interim/processed storage
├── features/         # Point-in-time technical, macro, and sentiment feature engineering
├── models/           # Modular model interfaces (XGBoost baseline, future hybrid architectures)
├── evaluation/       # Walk-forward validation, regime-aware metrics, calibration checks
├── backtesting/      # Simulation engine with slippage, transaction costs, and liquidity constraints
├── trading/          # Paper trading execution, portfolio tracking, pre-trade risk controls
├── explainability/   # SHAP values, feature attributions, prediction confidence scoring
├── news/             # Financial news ingestion and point-in-time NLP sentiment pipelines
└── utils/            # Shared utilities (logging, timezone handlers, date math)
```

---

## 4. Core Development Principles

* **Zero Look-Ahead Bias**: Features and signals strictly use information timestamped before the respective snapshot cutoffs (3:40 PM IST or 8:50 AM IST).
* **Zero Data Leakage**: Transformations, scalers, and target encodings are fitted only on training folds.
* **Timestamp-Aware Everywhere**: All data records and features carry precise timezone-aware timestamps (`Asia/Kolkata` or UTC).
* **Pluggable & Replaceable Models**: Initial models will utilize XGBoost, but all model definitions adhere to an abstract interface to allow seamless upgrades to deep learning or ensemble architectures.
* **Walk-Forward Validation**: Models are never evaluated with randomized K-fold cross-validation or optimized on the final test period. Expanding or rolling window walk-forward backtesting is strictly enforced.
* **Reproducibility Over Convenience**: All pipelines, seeds, data snapshots, and hyperparameters are tracked and reproducible.

---

## 5. Setup & Installation

### Prerequisites

* Python 3.11+ (Python 3.13 or 3.14 supported)
* Git

### Step 1: Virtual Environment Creation & Activation

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**macOS / Linux (Bash/Zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Step 2: Install Dependencies

Install foundational dependencies and editable package:
```bash
pip install -r requirements.txt
```

Alternatively, install with optional development dependencies using `pip`:
```bash
pip install -e ".[dev]"
```

---

## 6. Running Tests

Run the test suite using `pytest`:

```bash
pytest
```

To run with verbose output:
```bash
pytest -v
```

---

## 7. Data and Secret-Handling Rules

1. **Never Commit Secrets**:
   * API keys, broker tokens, passwords, and sensitive credentials must never be committed to Git.
   * Copy `.env.example` to `.env` and set local variables:
     ```bash
     cp .env.example .env
     ```
   * The `.env` file is excluded in `.gitignore`.
2. **Never Commit Raw/Processed Data or Models**:
   * Datasets (`data/raw/`, `data/processed/`, etc.) and model weights (`*.pkl`, `*.onnx`, etc.) are ignored by Git.
   * Only empty folder markers (`.gitkeep`) remain tracked.
3. **Point-In-Time Integrity**:
   * Any newly added data source must register its publication delay / availability timestamp to guarantee historical backtest fidelity.
