"""Storage and serialization layer for raw and processed datasets.

Enforces deterministic file layouts, SHA-256 checksum generation, and metadata tracking
for full reproducibility and auditability.
"""

import csv
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from nifty_ai.config import PROJECT_ROOT
from nifty_ai.data.schema import (
    DataFrequency,
    NormalizedMarketRecord,
    ProvenanceMetadata,
    ProviderTier,
)

RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"
MARKET_TIMEZONE = ZoneInfo("Asia/Kolkata")


def compute_sha256(content: str) -> str:
    """Compute SHA-256 hex digest for a string payload."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_file_sha256(file_path: Path) -> str:
    """Compute SHA-256 hex digest for an on-disk file."""
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def save_raw_market_data(
    raw_content: str,
    provider: str,
    symbol: str,
    start_date: date,
    end_date: date,
    retrieval_timestamp: Optional[datetime] = None,
    destination_dir: Optional[Path] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """Persist pristine raw data payload with full provenance metadata.

    Args:
        raw_content: Unmodified text/JSON response received from the data source.
        provider: Provider identifier (e.g., 'yahoo_finance').
        symbol: Symbol identifier (e.g., '^NSEI').
        start_date: Start of requested date range.
        end_date: End of requested date range.
        retrieval_timestamp: Time when payload was fetched (UTC).
        destination_dir: Target directory (defaults to data/raw/market/).

    Returns:
        Tuple of (saved_file_path, metadata_dict).
    """
    retrieval_dt = retrieval_timestamp or datetime.now(timezone.utc)
    target_dir = destination_dir or (RAW_DATA_DIR / "market")
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_sym = symbol.replace("^", "").replace(" ", "_").lower()
    retrieval_str = retrieval_dt.strftime("%Y%m%d_%H%M%S")
    filename = f"{provider}_{safe_sym}_{start_date}_{end_date}_{retrieval_str}.raw.json"
    file_path = target_dir / filename

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(raw_content)

    checksum = compute_sha256(raw_content)
    metadata = {
        "provider": provider,
        "symbol": symbol,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "retrieval_timestamp": retrieval_dt.isoformat(),
        "sha256": checksum,
        "byte_size": len(raw_content.encode("utf-8")),
        "raw_file": file_path.name,
    }

    meta_file = target_dir / f"{filename}.meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return file_path, metadata


def save_processed_market_data(
    records: List[NormalizedMarketRecord],
    output_path: Optional[Path] = None,
    extra_metadata: Optional[Dict[str, Any]] = None,
) -> Tuple[Path, Dict[str, Any]]:
    """Save normalized market records to a validated, deterministic CSV file.

    Accompanied by a .meta.json file detailing row count, date ranges, and SHA-256.
    """
    if not records:
        raise ValueError("Cannot save empty records list to processed storage.")

    target_path = output_path or (PROCESSED_DATA_DIR / "nifty50_daily.csv")
    target_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "trading_date",
        "timestamp",
        "symbol",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "is_adjusted",
        "adjustment_factor",
        "status",
        "provider",
        "source_identifier",
        "retrieval_timestamp",
        "source_timestamp",
        "timezone",
        "data_frequency",
        "tier",
    ]

    with open(target_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for rec in records:
            writer.writerow({
                "trading_date": rec.trading_date.isoformat(),
                "timestamp": rec.timestamp.isoformat(),
                "symbol": rec.symbol,
                "open": f"{rec.open:.4f}",
                "high": f"{rec.high:.4f}",
                "low": f"{rec.low:.4f}",
                "close": f"{rec.close:.4f}",
                "volume": f"{rec.volume:.0f}" if rec.volume is not None else "",
                "is_adjusted": rec.is_adjusted,
                "adjustment_factor": rec.adjustment_factor if rec.adjustment_factor is not None else "",
                "status": rec.status,
                "provider": rec.provenance.provider,
                "source_identifier": rec.provenance.source_identifier,
                "retrieval_timestamp": rec.provenance.retrieval_timestamp.isoformat(),
                "source_timestamp": rec.provenance.source_timestamp.isoformat() if rec.provenance.source_timestamp else "",
                "timezone": rec.provenance.timezone,
                "data_frequency": rec.provenance.data_frequency.value,
                "tier": rec.provenance.tier.value,
            })

    checksum = compute_file_sha256(target_path)
    metadata: Dict[str, Any] = {
        "dataset_name": target_path.stem,
        "file_name": target_path.name,
        "format": "csv",
        "row_count": len(records),
        "start_date": records[0].trading_date.isoformat(),
        "end_date": records[-1].trading_date.isoformat(),
        "start_timestamp": records[0].timestamp.isoformat(),
        "end_timestamp": records[-1].timestamp.isoformat(),
        "sha256": checksum,
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "provider": records[0].provenance.provider,
        "symbol": records[0].symbol,
        "schema_version": "1.0.0",
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    meta_file = target_path.parent / f"{target_path.name}.meta.json"
    with open(meta_file, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return target_path, metadata


def load_processed_market_data(file_path: Path) -> List[NormalizedMarketRecord]:
    """Load and deserialize NormalizedMarketRecord objects from a processed CSV file."""
    if not file_path.is_file():
        raise FileNotFoundError(f"Processed file not found: {file_path}")

    records: List[NormalizedMarketRecord] = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            retrieval_ts = datetime.fromisoformat(row["retrieval_timestamp"])
            source_ts = datetime.fromisoformat(row["source_timestamp"]) if row.get("source_timestamp") else None
            prov = ProvenanceMetadata(
                provider=row["provider"],
                source_identifier=row["source_identifier"],
                retrieval_timestamp=retrieval_ts,
                source_timestamp=source_ts,
                timezone=row["timezone"],
                data_frequency=DataFrequency(row["data_frequency"]),
                tier=ProviderTier(row["tier"]),
            )

            vol_val = float(row["volume"]) if row.get("volume") else None
            adj_factor = float(row["adjustment_factor"]) if row.get("adjustment_factor") else None

            record = NormalizedMarketRecord(
                timestamp=datetime.fromisoformat(row["timestamp"]),
                trading_date=date.fromisoformat(row["trading_date"]),
                symbol=row["symbol"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=vol_val,
                is_adjusted=(row["is_adjusted"].lower() == "true"),
                adjustment_factor=adj_factor,
                status=row.get("status", "finalized"),
                provenance=prov,
            )
            records.append(record)

    return records


__all__ = [
    "compute_sha256",
    "compute_file_file_sha256" if "compute_file_file_sha256" in locals() else "compute_file_sha256",
    "save_raw_market_data",
    "save_processed_market_data",
    "load_processed_market_data",
]
