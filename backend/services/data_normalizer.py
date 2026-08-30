"""Data normalization service.

Handles messy data cleaning: inconsistent capitalization, whitespace,
sector names, status values, date formats, missing/null values, and
currency parsing. Designed for the specific data patterns found in
the Skylark assignment datasets.
"""

import pandas as pd
import numpy as np
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from services.data_quality_service import DataQualityReport, create_quality_report

logger = logging.getLogger(__name__)

# === Normalization Maps ===

SECTOR_NORMALIZATION = {
    "mining": "Mining",
    "renewables": "Renewables",
    "railways": "Railways",
    "powerline": "Powerline",
    "construction": "Construction",
    "dsp": "DSP",
    "tender": "Tender",
    "others": "Others",
    "security and surveillance": "Security & Surveillance",
    "security & surveillance": "Security & Surveillance",
    "aviation": "Aviation",
    "manufacturing": "Manufacturing",
}

DEAL_STATUS_NORMALIZATION = {
    "open": "Open",
    "won": "Won",
    "dead": "Dead",
    "on hold": "On Hold",
    "onhold": "On Hold",
    "on-hold": "On Hold",
}

EXECUTION_STATUS_NORMALIZATION = {
    "completed": "Completed",
    "ongoing": "Ongoing",
    "not started": "Not Started",
    "pause / struck": "Paused",
    "pause/struck": "Paused",
    "paused": "Paused",
    "struck": "Paused",
    "stuck": "Paused",
    "partial completed": "Partial Completed",
    "partially completed": "Partial Completed",
    "executed until current month": "Executed Current Month",
    "details pending from client": "Pending Client Details",
}

BILLING_STATUS_NORMALIZATION = {
    "fully billed": "Fully Billed",
    "not billed yet": "Not Billed",
    "billed": "Billed",
    "billed": "Billed",  # handles "BIlled" after lowercasing
    "not billable": "Not Billable",
    "stuck": "Stuck",
    "update required": "Update Required",
}

CLOSURE_PROBABILITY_NORMALIZATION = {
    "high": "High",
    "medium": "Medium",
    "low": "Low",
}

NATURE_OF_WORK_NORMALIZATION = {
    "one time project": "One Time Project",
    "monthly contract": "Monthly Contract",
    "annual rate contract": "Annual Rate Contract",
    "proof of concept": "Proof of Concept",
}


def _clean_string(value: Any) -> Optional[str]:
    """Clean a string value: strip whitespace, handle null-like values."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in ("", "none", "nan", "null", "n/a", "na", "-", "#value!"):
        return None
    return s


def _normalize_lookup(value: Optional[str], lookup: Dict[str, str]) -> Optional[str]:
    """Normalize a string using a lookup dictionary."""
    if value is None:
        return None
    key = value.lower().strip()
    return lookup.get(key, value.strip())


def _parse_numeric(value: Any) -> Optional[float]:
    """Parse a numeric value, handling currency symbols and commas."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in ("", "none", "nan", "null", "n/a", "#value!", "0"):
        return None if s.lower() in ("", "none", "nan", "null", "n/a", "#value!") else 0.0
    # Remove currency symbols, commas, spaces
    s = re.sub(r"[₹$,\s]", "", s)
    try:
        val = float(s)
        # Reject clearly invalid values (like very small decimals that are errors)
        if val < 0:
            return None
        return val
    except (ValueError, TypeError):
        return None


def _parse_date(value: Any) -> Optional[str]:
    """Parse a date value into ISO format string (YYYY-MM-DD)."""
    if value is None:
        return None
    s = str(value).strip()
    if s.lower() in ("", "none", "nan", "null", "n/a"):
        return None

    # Try common date formats
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%m/%d/%Y", "%d/%m/%Y", "%Y/%m/%d"]:
        try:
            dt = pd.to_datetime(s, format=fmt)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            continue

    # Fallback: let pandas try to infer
    try:
        dt = pd.to_datetime(s, dayfirst=False)
        return dt.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def normalize_deals(records: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, DataQualityReport]:
    """Normalize deal records into a clean DataFrame.

    Args:
        records: List of raw record dicts from monday.com

    Returns:
        Tuple of (normalized DataFrame, data quality report)
    """
    quality = create_quality_report()

    if not records:
        quality.add_detail("No deal records found in the board.")
        return pd.DataFrame(), quality

    df = pd.DataFrame(records)
    logger.info(f"Normalizing {len(df)} deal records with columns: {list(df.columns)}")

    # Dynamic column mapping - find the best match for expected columns
    col_map = _build_column_map(df.columns, {
        "deal_name": ["name", "deal name", "deal_name"],
        "owner_code": ["owner code", "owner_code", "owner", "bd/kam personnel code"],
        "client_code": ["client code", "client_code", "client"],
        "deal_status": ["deal status", "deal_status", "status"],
        "close_date": ["close date (a)", "close date", "close_date", "actual close date"],
        "closure_probability": ["closure probability", "closure_probability", "probability"],
        "deal_value": ["masked deal value", "deal value", "deal_value", "value", "amount"],
        "tentative_close_date": ["tentative close date", "tentative_close_date", "expected close date"],
        "deal_stage": ["deal stage", "deal_stage", "stage"],
        "product_type": ["product deal", "product_deal", "product type", "product"],
        "sector": ["sector/service", "sector", "sector_service"],
        "created_date": ["created date", "created_date", "creation date"],
    })

    # Create normalized DataFrame
    normalized = pd.DataFrame()
    normalized["item_id"] = df.get("item_id", pd.Series(range(len(df))))

    # --- Name ---
    name_col = col_map.get("deal_name", "name")
    normalized["deal_name"] = df[name_col].apply(_clean_string) if name_col in df.columns else None

    # --- Owner Code ---
    owner_col = col_map.get("owner_code")
    if owner_col and owner_col in df.columns:
        normalized["owner_code"] = df[owner_col].apply(_clean_string)
        missing_owner = normalized["owner_code"].isna().sum()
        if missing_owner > 0:
            quality.add_issue("missing_owner", missing_owner)
    else:
        normalized["owner_code"] = None
        quality.add_detail("Owner code column not found in deals board.")

    # --- Client Code ---
    client_col = col_map.get("client_code")
    if client_col and client_col in df.columns:
        normalized["client_code"] = df[client_col].apply(_clean_string)

    # --- Deal Status ---
    status_col = col_map.get("deal_status")
    if status_col and status_col in df.columns:
        normalized["deal_status"] = df[status_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), DEAL_STATUS_NORMALIZATION)
        )
        missing_status = normalized["deal_status"].isna().sum()
        if missing_status > 0:
            quality.add_issue("missing_status", missing_status)
    else:
        normalized["deal_status"] = None
        quality.add_detail("Deal status column not found.")

    # --- Close Date (Actual) ---
    close_col = col_map.get("close_date")
    if close_col and close_col in df.columns:
        normalized["close_date"] = df[close_col].apply(_parse_date)
        missing = normalized["close_date"].isna().sum()
        if missing > 0:
            quality.add_issue("missing_close_date", missing)

    # --- Closure Probability ---
    prob_col = col_map.get("closure_probability")
    if prob_col and prob_col in df.columns:
        normalized["closure_probability"] = df[prob_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), CLOSURE_PROBABILITY_NORMALIZATION)
        )

    # --- Deal Value ---
    value_col = col_map.get("deal_value")
    if value_col and value_col in df.columns:
        normalized["deal_value"] = df[value_col].apply(_parse_numeric)
        missing_value = normalized["deal_value"].isna().sum()
        if missing_value > 0:
            quality.add_issue("missing_deal_value", missing_value)
    else:
        normalized["deal_value"] = None
        quality.add_detail("Deal value column not found.")

    # --- Tentative Close Date ---
    tent_col = col_map.get("tentative_close_date")
    if tent_col and tent_col in df.columns:
        normalized["tentative_close_date"] = df[tent_col].apply(_parse_date)

    # --- Deal Stage ---
    stage_col = col_map.get("deal_stage")
    if stage_col and stage_col in df.columns:
        normalized["deal_stage"] = df[stage_col].apply(_clean_string)
        missing_stage = normalized["deal_stage"].isna().sum()
        if missing_stage > 0:
            quality.add_issue("missing_deal_stage", missing_stage)

    # --- Product Type ---
    product_col = col_map.get("product_type")
    if product_col and product_col in df.columns:
        normalized["product_type"] = df[product_col].apply(_clean_string)
        missing_product = normalized["product_type"].isna().sum()
        if missing_product > 0:
            quality.add_issue("missing_product_type", missing_product)

    # --- Sector ---
    sector_col = col_map.get("sector")
    if sector_col and sector_col in df.columns:
        normalized["sector"] = df[sector_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), SECTOR_NORMALIZATION)
        )
        missing_sector = normalized["sector"].isna().sum()
        if missing_sector > 0:
            quality.add_issue("missing_sector", missing_sector)
    else:
        normalized["sector"] = None
        quality.add_detail("Sector column not found in deals board.")

    # --- Created Date ---
    created_col = col_map.get("created_date")
    if created_col and created_col in df.columns:
        normalized["created_date"] = df[created_col].apply(_parse_date)
        missing_created = normalized["created_date"].isna().sum()
        if missing_created > 0:
            quality.add_issue("missing_created_date", missing_created)

    logger.info(f"Normalized deals: {len(normalized)} rows, quality issues: {quality.total_issues}")
    return normalized, quality


def normalize_work_orders(records: List[Dict[str, Any]]) -> Tuple[pd.DataFrame, DataQualityReport]:
    """Normalize work order records into a clean DataFrame.

    Args:
        records: List of raw record dicts from monday.com

    Returns:
        Tuple of (normalized DataFrame, data quality report)
    """
    quality = create_quality_report()

    if not records:
        quality.add_detail("No work order records found in the board.")
        return pd.DataFrame(), quality

    df = pd.DataFrame(records)
    logger.info(f"Normalizing {len(df)} work order records with columns: {list(df.columns)}")

    col_map = _build_column_map(df.columns, {
        "deal_name": ["name", "deal name", "deal name masked", "deal_name"],
        "customer_code": ["customer name code", "customer code", "customer_code"],
        "serial_number": ["serial #", "serial number", "serial_number", "serial"],
        "nature_of_work": ["nature of work", "nature_of_work"],
        "execution_status": ["execution status", "execution_status", "status"],
        "data_delivery_date": ["data delivery date", "data_delivery_date", "delivery date"],
        "po_date": ["date of po/loi", "po date", "po_date", "date of po"],
        "document_type": ["document type", "document_type"],
        "start_date": ["probable start date", "start date", "start_date"],
        "end_date": ["probable end date", "end date", "end_date"],
        "bd_personnel": ["bd/kam personnel code", "bd personnel", "bd_personnel", "personnel code"],
        "sector": ["sector", "sector/service"],
        "type_of_work": ["type of work", "type_of_work", "work type"],
        "software_platform": [
            "is any skylark software platform part of the client deliverables in this deal?",
            "skylark software", "software platform", "software_platform",
        ],
        "invoice_amount": [
            "amount in rupees (excl of gst) (masked)", "amount", "invoice amount",
            "invoice_amount", "amount in rupees",
        ],
        "billing_status": ["billing status", "billing_status"],
    })

    normalized = pd.DataFrame()
    normalized["item_id"] = df.get("item_id", pd.Series(range(len(df))))

    # --- Name ---
    name_col = col_map.get("deal_name", "name")
    normalized["deal_name"] = df[name_col].apply(_clean_string) if name_col in df.columns else None

    # --- Customer Code ---
    cust_col = col_map.get("customer_code")
    if cust_col and cust_col in df.columns:
        normalized["customer_code"] = df[cust_col].apply(_clean_string)

    # --- Serial Number ---
    serial_col = col_map.get("serial_number")
    if serial_col and serial_col in df.columns:
        normalized["serial_number"] = df[serial_col].apply(_clean_string)
        missing = normalized["serial_number"].isna().sum()
        if missing > 0:
            quality.add_issue("missing_serial_number", missing)

    # --- Nature of Work ---
    nature_col = col_map.get("nature_of_work")
    if nature_col and nature_col in df.columns:
        normalized["nature_of_work"] = df[nature_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), NATURE_OF_WORK_NORMALIZATION)
        )
        missing = normalized["nature_of_work"].isna().sum()
        if missing > 0:
            quality.add_issue("missing_nature_of_work", missing)

    # --- Execution Status ---
    exec_col = col_map.get("execution_status")
    if exec_col and exec_col in df.columns:
        normalized["execution_status"] = df[exec_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), EXECUTION_STATUS_NORMALIZATION)
        )
        missing = normalized["execution_status"].isna().sum()
        if missing > 0:
            quality.add_issue("missing_execution_status", missing)
    else:
        normalized["execution_status"] = None
        quality.add_detail("Execution status column not found.")

    # --- Dates ---
    for field, mapped_col in [
        ("data_delivery_date", col_map.get("data_delivery_date")),
        ("po_date", col_map.get("po_date")),
        ("start_date", col_map.get("start_date")),
        ("end_date", col_map.get("end_date")),
    ]:
        if mapped_col and mapped_col in df.columns:
            normalized[field] = df[mapped_col].apply(_parse_date)
            missing = normalized[field].isna().sum()
            if missing > 0 and field in ("start_date", "end_date"):
                quality.add_issue(f"missing_{field}", missing)
        else:
            normalized[field] = None

    # --- BD Personnel ---
    bd_col = col_map.get("bd_personnel")
    if bd_col and bd_col in df.columns:
        normalized["bd_personnel"] = df[bd_col].apply(_clean_string)

    # --- Sector ---
    sector_col = col_map.get("sector")
    if sector_col and sector_col in df.columns:
        normalized["sector"] = df[sector_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), SECTOR_NORMALIZATION)
        )
        missing = normalized["sector"].isna().sum()
        if missing > 0:
            quality.add_issue("missing_sector", missing)

    # --- Type of Work ---
    type_col = col_map.get("type_of_work")
    if type_col and type_col in df.columns:
        normalized["type_of_work"] = df[type_col].apply(_clean_string)

    # --- Software Platform ---
    sw_col = col_map.get("software_platform")
    if sw_col and sw_col in df.columns:
        normalized["software_platform"] = df[sw_col].apply(_clean_string)

    # --- Invoice Amount ---
    amt_col = col_map.get("invoice_amount")
    if amt_col and amt_col in df.columns:
        normalized["invoice_amount"] = df[amt_col].apply(_parse_numeric)
        invalid = df[amt_col].apply(
            lambda x: str(x).strip().upper() == "#VALUE!" if x else False
        ).sum()
        if invalid > 0:
            quality.add_issue("invalid_amount", invalid)

    # --- Billing Status ---
    bill_col = col_map.get("billing_status")
    if bill_col and bill_col in df.columns:
        normalized["billing_status"] = df[bill_col].apply(
            lambda x: _normalize_lookup(_clean_string(x), BILLING_STATUS_NORMALIZATION)
        )

    # --- Document Type ---
    doc_col = col_map.get("document_type")
    if doc_col and doc_col in df.columns:
        normalized["document_type"] = df[doc_col].apply(_clean_string)

    logger.info(f"Normalized work orders: {len(normalized)} rows, quality issues: {quality.total_issues}")
    return normalized, quality


def _build_column_map(actual_columns: pd.Index, expected_map: Dict[str, List[str]]) -> Dict[str, str]:
    """Build a mapping from logical field names to actual column names.

    Uses fuzzy matching: lowercased, stripped comparison against possible names.
    """
    col_map = {}
    actual_lower = {col.lower().strip(): col for col in actual_columns}

    for field_name, possible_names in expected_map.items():
        for possible in possible_names:
            possible_lower = possible.lower().strip()
            if possible_lower in actual_lower:
                col_map[field_name] = actual_lower[possible_lower]
                break

    logger.debug(f"Column mapping: {col_map}")
    return col_map
