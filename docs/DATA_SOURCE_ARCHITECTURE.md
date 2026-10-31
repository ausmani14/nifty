# DATA SOURCE ARCHITECTURE

**Phase 1 Architecture Document**  
**Module:** `nifty_ai.data`  
**Status:** Implemented  

---

## 1. Architectural Overview

The **NIFTY AI** data layer is designed around three fundamental engineering principles:
1. **Provider Agnosticism:** Core models, features, and trading layers have zero direct dependencies on any third-party market data API or library. All raw ingested feeds are normalized immediately into canonical representations.
2. **Strict Provenance & Auditability:** Every observation carries immutable metadata recording its originating provider, retrieval time, original publishing timestamp, timezone, and data frequency.
3. **Zero Look-Ahead Bias via Snapshot Awareness:** All data points are indexed by their point-in-time availability and filtered strictly against prediction snapshot cutoff timestamps.

```
┌────────────────────────────────────────────────────────┐
│                   External Sources                     │
│  [NSE Bhavcopy]     [Yahoo Finance]     [Macro/News]   │
└───────────┬────────────────┬───────────────────┬───────┘
            │                │                   │
            ▼                ▼                   ▼
┌────────────────────────────────────────────────────────┐
│            Provider Adapters & Abstractions            │
│  BaseMarketDataProvider | BaseMacroDataProvider | News │
└───────────────────────────┬────────────────────────────┘
                            │ (Normalize)
                            ▼
┌────────────────────────────────────────────────────────┐
│                   Normalized Schemas                   │
│  NormalizedMarketRecord | MacroRecord | NewsRecord     │
│  (Mandatory ProvenanceMetadata & Timezone Awareness)   │
└───────────────────────────┬────────────────────────────┘
                            │
               ┌────────────┴────────────┐
               ▼                         ▼
┌────────────────────────────┐ ┌───────────────────────────┐
│     Validation Engine      │ │   Snapshot Cutoff Filter  │
│  (MarketDataValidator)     │ │   (SnapshotCutoff:        │
│  - Bounds & positivity     │ │    15:30 IST / 08:50 IST) │
│  - Timezone integrity      │ │   - Strict leakage block  │
│  - No duplicate timestamps │ └─────────────┬─────────────┘
└────────────────────────────┘               │
                                             ▼
                               ┌───────────────────────────┐
                               │ Feature Engineering (P4)  │
                               └───────────────────────────┘
```

---

## 2. Provider Abstraction

All data ingestion sources inherit from unified abstract base classes defined in `nifty_ai.data.providers.base`:

* **`BaseDataProvider`**: Common ancestor defining `name`, `tier`, `status`, and `is_available()`.
* **`BaseMarketDataProvider`**: Exposes `fetch_daily_ohlcv(symbol, start_date, end_date)` and `get_supported_symbols()`.
* **`BaseMacroDataProvider`**: Exposes `fetch_macro_series(indicator_name, start_date, end_date)` and `get_supported_indicators()`.
* **`BaseNewsDataProvider`**: Exposes `fetch_news(start_time, end_time, symbols)` with point-in-time constraints.

### Provider Status & Tiers
Providers are categorized explicitly by lifecycle status and tier:
* **Lifecycle Status:**
  * `planned`: Defined conceptually in architecture; implementation scheduled in a future phase.
  * `development`: Free or rapid prototyping adapter used for offline/sandbox testing.
  * `reference`: Authoritative exchange archive or audited benchmark data.
  * `production`: High-reliability, low-latency production feed.
* **Tiers:**
  * `free`: Unauthenticated or publicly accessible sources.
  * `official`: Primary exchange-issued reports (e.g., NSE India Bhavcopy).
  * `professional`: Commercial market data vendors.

---

## 3. Normalized Schemas

All incoming data must be converted into immutable Python dataclasses defined in `nifty_ai.data.schema`:

### `NormalizedMarketRecord`
| Field | Type | Description |
| :--- | :--- | :--- |
| `timestamp` | `datetime` | Bar closing timestamp (must be timezone-aware). |
| `trading_date` | `date` | Market session calendar date. |
| `symbol` | `str` | Asset or index ticker (e.g., `"NIFTY 50"`, `"^NSEI"`). |
| `open` | `float` | Bar open price. |
| `high` | `float` | Bar high price. |
| `low` | `float` | Bar low price. |
| `close` | `float` | Bar close / settlement price. |
| `volume` | `Optional[float]` | Bar trading volume / contracts traded. |
| `provenance` | `ProvenanceMetadata` | Complete lineage metadata. |
| `is_adjusted` | `bool` | True if retroactively adjusted for corporate actions. |
| `adjustment_factor` | `Optional[float]` | Split/dividend adjustment ratio if applicable. |
| `status` | `str` | Record status (`"finalized"`, `"provisional"`). |

### `ProvenanceMetadata`
| Field | Type | Description |
| :--- | :--- | :--- |
| `provider` | `str` | Provider identifier (e.g., `"nse_official"`). |
| `source_identifier` | `str` | Source ticker or document ID. |
| `retrieval_timestamp` | `datetime` | UTC timestamp when fetched by NIFTY AI. |
| `source_timestamp` | `Optional[datetime]` | Provider-reported publication time. |
| `timezone` | `str` | Source timezone (e.g., `"Asia/Kolkata"`). |
| `data_frequency` | `DataFrequency` | Temporal resolution (`DAILY`, `MINUTE`, `TICK`). |
| `tier` | `ProviderTier` | `FREE`, `OFFICIAL`, or `PROFESSIONAL`. |
| `dataset_version` | `Optional[str]` | Hash or version string of dataset. |

---

## 4. Dual Snapshot & Information Cutoff Philosophy

In financial modeling, look-ahead bias invalidates research. NIFTY AI prevents this by binding all data ingestion and feature creation to an explicit `SnapshotCutoff` instance:

### Snapshot A (`SNAPSHOT_1540`)
* **Context:** Post-market close on Day \( T-1 \).
* **Execution Time:** 15:40:00 IST on Day \( T-1 \).
* **Information Cutoff:** Strictly **15:30:00 IST** on Day \( T-1 \).
* **Rule:** Only data generated or published on or before 15:30:00 IST of Day \( T-1 \) is accepted.

### Snapshot B (`SNAPSHOT_0850`)
* **Context:** Pre-market open on Day \( T \).
* **Execution Time:** 08:50:00 IST on Day \( T \).
* **Information Cutoff:** Strictly **08:50:00 IST** on Day \( T \).
* **Rule:** May incorporate overnight global indices, early GIFT Nifty prints, and financial news published between 15:30 IST (Day \( T-1 \)) and 08:50 IST (Day \( T \)).

The `SnapshotCutoff.filter_records(records, timestamp_getter)` method guarantees that records with timestamps exceeding the cutoff are pruned prior to feature construction.

---

## 5. Validation Architecture

The `MarketDataValidator` class (`nifty_ai.data.validation`) evaluates market data collections for integrity before persistence or transformation:

1. **Price Positiveness:** Open, High, Low, Close must be strictly positive (> 0).
2. **OHLC Boundary Invariance:**
   * \(\text{Low} \le \text{High}\)
   * \(\text{Low} \le \text{Open} \le \text{High}\)
   * \(\text{Low} \le \text{Close} \le \text{High}\)
3. **Volume Integrity:** Volume must be non-negative (\(\ge 0\)).
4. **Timezone Awareness:** Timestamps without timezone information are rejected.
5. **Temporal Sequencing:** Records must be strictly chronological (\(t_{i} < t_{i+1}\)).
6. **Duplicate Detection:** Duplicate timestamps for the same asset symbol trigger validation errors.

---

## 6. How to Add a New Provider

To integrate a new provider into NIFTY AI in future phases:

1. **Subclass the Interface:**
   Create a new adapter subclassing `BaseMarketDataProvider`, `BaseMacroDataProvider`, or `BaseNewsDataProvider`.
   ```python
   from nifty_ai.data.providers.base import BaseMarketDataProvider
   from nifty_ai.data.schema import ProviderStatus, ProviderTier

   class CustomMarketProvider(BaseMarketDataProvider):
       def __init__(self):
           super().__init__(
               name="custom_vendor",
               tier=ProviderTier.PROFESSIONAL,
               status=ProviderStatus.DEVELOPMENT,
               description="Custom market data provider adapter.",
           )

       def is_available(self) -> bool:
           # Validate API keys or network availability
           return True

       def get_supported_symbols(self) -> list[str]:
           return ["NIFTY 50"]

       def fetch_daily_ohlcv(self, symbol, start_date, end_date):
           # Fetch raw data, normalize into NormalizedMarketRecord instances
           ...
   ```

2. **Register in Provider Registry:**
   ```python
   from nifty_ai.data.providers.registry import default_registry

   default_registry.register_market_provider(CustomMarketProvider())
   ```

3. **Configure in `configs/providers.yaml`:**
   Add configuration parameters, symbol mappings, and point to environment variable keys for credentials.
