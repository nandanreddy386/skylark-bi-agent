"""Deterministic business analytics service.

All calculations are done with Pandas — no LLM involvement.
The LLM is only used to explain these pre-computed results.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from services.data_quality_service import DataQualityReport

import logging

logger = logging.getLogger(__name__)


def _current_quarter_range() -> Tuple[str, str]:
    """Get start and end dates for the current quarter."""
    now = datetime.now()
    q = (now.month - 1) // 3
    start = datetime(now.year, q * 3 + 1, 1)
    if q == 3:
        end = datetime(now.year + 1, 1, 1) - timedelta(days=1)
    else:
        end = datetime(now.year, (q + 1) * 3 + 1, 1) - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _format_inr(value: float) -> str:
    """Format a number as Indian Rupees (lakhs/crores)."""
    if value >= 1e7:
        return f"₹{value / 1e7:.2f} Cr"
    elif value >= 1e5:
        return f"₹{value / 1e5:.2f} L"
    else:
        return f"₹{value:,.0f}"


# ============================================================
# DEAL ANALYTICS
# ============================================================

def calculate_total_pipeline(deals: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Calculate total pipeline value for active deals (Open + On Hold)."""
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]
    with_value = active[active["deal_value"].notna() & (active["deal_value"] > 0)]

    total_value = with_value["deal_value"].sum()
    deal_count = len(active)
    valued_count = len(with_value)

    return {
        "total_pipeline_value": total_value,
        "total_pipeline_formatted": _format_inr(total_value),
        "active_deal_count": deal_count,
        "deals_with_value": valued_count,
        "deals_without_value": deal_count - valued_count,
        "average_deal_size": with_value["deal_value"].mean() if valued_count > 0 else 0,
        "average_deal_formatted": _format_inr(with_value["deal_value"].mean()) if valued_count > 0 else "N/A",
        "median_deal_size": with_value["deal_value"].median() if valued_count > 0 else 0,
    }


def pipeline_by_sector(deals: pd.DataFrame, quality: DataQualityReport, sector_filter: Optional[str] = None) -> Dict[str, Any]:
    """Break down pipeline by sector."""
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]
    if "sector" not in active.columns:
        return {"error": "Sector data not available"}

    if sector_filter:
        active = active[active["sector"].str.lower() == sector_filter.lower()]
        if active.empty:
            return {"error": f"No active deals found for sector: {sector_filter}"}

    sector_stats = []
    for sector, group in active.groupby("sector"):
        if sector is None or pd.isna(sector):
            continue
        with_value = group[group["deal_value"].notna() & (group["deal_value"] > 0)]
        sector_stats.append({
            "sector": sector,
            "deal_count": len(group),
            "total_value": with_value["deal_value"].sum(),
            "total_value_formatted": _format_inr(with_value["deal_value"].sum()),
            "avg_value": with_value["deal_value"].mean() if len(with_value) > 0 else 0,
            "deals_with_value": len(with_value),
        })

    sector_stats.sort(key=lambda x: x["total_value"], reverse=True)

    return {
        "sectors": sector_stats,
        "top_sector": sector_stats[0]["sector"] if sector_stats else "N/A",
        "top_sector_value": sector_stats[0]["total_value_formatted"] if sector_stats else "N/A",
        "total_sectors": len(sector_stats),
    }


def pipeline_by_stage(deals: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Break down pipeline by deal stage."""
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]
    if "deal_stage" not in active.columns:
        return {"error": "Deal stage data not available"}

    stage_stats = []
    for stage, group in active.groupby("deal_stage"):
        if stage is None or pd.isna(stage):
            continue
        with_value = group[group["deal_value"].notna() & (group["deal_value"] > 0)]
        stage_stats.append({
            "stage": stage,
            "deal_count": len(group),
            "total_value": with_value["deal_value"].sum(),
            "total_value_formatted": _format_inr(with_value["deal_value"].sum()),
        })

    stage_stats.sort(key=lambda x: x["total_value"], reverse=True)

    return {
        "stages": stage_stats,
        "total_stages": len(stage_stats),
    }


def deals_closing_soon(deals: pd.DataFrame, quality: DataQualityReport, days: int = 30) -> Dict[str, Any]:
    """Find deals expected to close within the specified number of days."""
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]
    now = datetime.now().strftime("%Y-%m-%d")
    cutoff = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

    # Use tentative_close_date or close_date
    date_col = "tentative_close_date" if "tentative_close_date" in active.columns else "close_date"
    if date_col not in active.columns:
        return {"error": "No close date data available"}

    closing = active[
        (active[date_col].notna()) &
        (active[date_col] >= now) &
        (active[date_col] <= cutoff)
    ]

    deal_list = []
    for _, row in closing.iterrows():
        deal_list.append({
            "name": row.get("deal_name", "Unknown"),
            "value": _format_inr(row["deal_value"]) if pd.notna(row.get("deal_value")) else "N/A",
            "close_date": row.get(date_col, "N/A"),
            "sector": row.get("sector", "N/A"),
            "stage": row.get("deal_stage", "N/A"),
        })

    total_value = closing["deal_value"].sum() if "deal_value" in closing.columns else 0

    return {
        "deals_closing_soon": deal_list,
        "count": len(deal_list),
        "total_value": total_value,
        "total_value_formatted": _format_inr(total_value),
        "within_days": days,
    }


def high_value_deals(deals: pd.DataFrame, quality: DataQualityReport, top_n: int = 10) -> Dict[str, Any]:
    """Identify the highest value active deals."""
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]
    with_value = active[active["deal_value"].notna() & (active["deal_value"] > 0)]
    top = with_value.nlargest(top_n, "deal_value")

    deal_list = []
    for _, row in top.iterrows():
        deal_list.append({
            "name": row.get("deal_name", "Unknown"),
            "value": _format_inr(row["deal_value"]),
            "raw_value": row["deal_value"],
            "sector": row.get("sector", "N/A"),
            "stage": row.get("deal_stage", "N/A"),
            "probability": row.get("closure_probability", "N/A"),
        })

    return {
        "top_deals": deal_list,
        "count": len(deal_list),
    }


def deal_status_summary(deals: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Overall deal status breakdown."""
    status_counts = deals["deal_status"].value_counts().to_dict()
    total = len(deals)

    won_deals = deals[deals["deal_status"] == "Won"]
    won_value = won_deals["deal_value"].sum() if "deal_value" in won_deals.columns else 0

    return {
        "total_deals": total,
        "status_breakdown": {k: int(v) for k, v in status_counts.items() if k is not None},
        "won_value": won_value,
        "won_value_formatted": _format_inr(won_value),
        "win_rate": f"{(status_counts.get('Won', 0) / total * 100):.1f}%" if total > 0 else "N/A",
    }


def pipeline_this_quarter(deals: pd.DataFrame, quality: DataQualityReport, sector_filter: Optional[str] = None) -> Dict[str, Any]:
    """Pipeline analysis for the current quarter."""
    q_start, q_end = _current_quarter_range()
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]

    if sector_filter and "sector" in active.columns:
        active = active[active["sector"].str.lower() == sector_filter.lower()]

    # Filter by tentative close date within this quarter
    date_col = "tentative_close_date" if "tentative_close_date" in active.columns else "close_date"
    if date_col in active.columns:
        this_q = active[
            (active[date_col].notna()) &
            (active[date_col] >= q_start) &
            (active[date_col] <= q_end)
        ]
    else:
        this_q = active  # If no date, show all active

    with_value = this_q[this_q["deal_value"].notna() & (this_q["deal_value"] > 0)]
    total_value = with_value["deal_value"].sum()

    # Probability-weighted pipeline
    weighted_value = 0
    if "closure_probability" in with_value.columns:
        prob_weights = {"High": 0.75, "Medium": 0.5, "Low": 0.25}
        for _, row in with_value.iterrows():
            weight = prob_weights.get(row.get("closure_probability"), 0.5)
            weighted_value += row["deal_value"] * weight

    # Stage breakdown for this quarter
    stage_breakdown = {}
    if "deal_stage" in this_q.columns:
        for stage, group in this_q.groupby("deal_stage"):
            if stage and not pd.isna(stage):
                v = group[group["deal_value"].notna()]["deal_value"].sum()
                stage_breakdown[stage] = {
                    "count": len(group),
                    "value": v,
                    "value_formatted": _format_inr(v),
                }

    return {
        "quarter": f"Q{((datetime.now().month - 1) // 3) + 1} {datetime.now().year}",
        "quarter_start": q_start,
        "quarter_end": q_end,
        "total_deals": len(this_q),
        "deals_with_value": len(with_value),
        "total_pipeline_value": total_value,
        "total_pipeline_formatted": _format_inr(total_value),
        "weighted_pipeline_value": weighted_value,
        "weighted_pipeline_formatted": _format_inr(weighted_value),
        "stage_breakdown": stage_breakdown,
        "sector_filter": sector_filter,
    }


def sales_risks(deals: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Identify sales risks in the pipeline."""
    active = deals[deals["deal_status"].isin(["Open", "On Hold"])]
    risks = []

    # Risk 1: High-value deals with low probability
    if "closure_probability" in active.columns and "deal_value" in active.columns:
        high_val_low_prob = active[
            (active["deal_value"].notna()) &
            (active["deal_value"] > active["deal_value"].quantile(0.75)) &
            (active["closure_probability"] == "Low")
        ]
        if len(high_val_low_prob) > 0:
            risks.append({
                "type": "High-value deals with low closure probability",
                "count": len(high_val_low_prob),
                "total_value": _format_inr(high_val_low_prob["deal_value"].sum()),
                "severity": "High",
            })

    # Risk 2: Deals on hold
    on_hold = active[active["deal_status"] == "On Hold"]
    if len(on_hold) > 0:
        on_hold_value = on_hold[on_hold["deal_value"].notna()]["deal_value"].sum()
        risks.append({
            "type": "Deals currently on hold",
            "count": len(on_hold),
            "total_value": _format_inr(on_hold_value),
            "severity": "Medium",
        })

    # Risk 3: Overdue deals (tentative close date in the past)
    if "tentative_close_date" in active.columns:
        now = datetime.now().strftime("%Y-%m-%d")
        overdue = active[
            (active["tentative_close_date"].notna()) &
            (active["tentative_close_date"] < now)
        ]
        if len(overdue) > 0:
            overdue_value = overdue[overdue["deal_value"].notna()]["deal_value"].sum()
            risks.append({
                "type": "Deals past their tentative close date",
                "count": len(overdue),
                "total_value": _format_inr(overdue_value),
                "severity": "High",
            })

    # Risk 4: Concentration risk (>50% pipeline in one sector)
    if "sector" in active.columns:
        sector_values = active.groupby("sector")["deal_value"].sum()
        total = sector_values.sum()
        if total > 0:
            for sector, value in sector_values.items():
                if value / total > 0.5:
                    risks.append({
                        "type": f"Pipeline concentration in {sector} sector ({value/total*100:.0f}%)",
                        "count": 1,
                        "total_value": _format_inr(value),
                        "severity": "Medium",
                    })

    return {
        "risks": risks,
        "total_risk_count": len(risks),
        "high_severity_count": sum(1 for r in risks if r["severity"] == "High"),
    }


# ============================================================
# WORK ORDER ANALYTICS
# ============================================================

def work_order_status_summary(wo: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Summary of work order execution statuses."""
    if "execution_status" not in wo.columns:
        return {"error": "Execution status data not available"}

    status_counts = wo["execution_status"].value_counts().to_dict()
    total = len(wo)

    completed = status_counts.get("Completed", 0)
    ongoing = status_counts.get("Ongoing", 0)
    not_started = status_counts.get("Not Started", 0)
    paused = status_counts.get("Paused", 0)

    return {
        "total_work_orders": total,
        "status_breakdown": {k: int(v) for k, v in status_counts.items() if k is not None},
        "completion_rate": f"{(completed / total * 100):.1f}%" if total > 0 else "N/A",
        "active_count": ongoing + not_started,
        "paused_count": paused,
    }


def delayed_work_orders(wo: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Identify delayed or overdue work orders."""
    now = datetime.now().strftime("%Y-%m-%d")
    delayed = []

    if "end_date" in wo.columns and "execution_status" in wo.columns:
        # Work orders past end date but not completed
        overdue = wo[
            (wo["end_date"].notna()) &
            (wo["end_date"] < now) &
            (~wo["execution_status"].isin(["Completed", None]))
        ]

        for _, row in overdue.iterrows():
            delayed.append({
                "name": row.get("deal_name", "Unknown"),
                "serial": row.get("serial_number", "N/A"),
                "status": row.get("execution_status", "N/A"),
                "end_date": row.get("end_date", "N/A"),
                "sector": row.get("sector", "N/A"),
            })

    # Also include paused/stuck work orders
    paused = wo[wo["execution_status"].isin(["Paused"])] if "execution_status" in wo.columns else pd.DataFrame()

    paused_list = []
    for _, row in paused.iterrows():
        paused_list.append({
            "name": row.get("deal_name", "Unknown"),
            "serial": row.get("serial_number", "N/A"),
            "sector": row.get("sector", "N/A"),
        })

    return {
        "overdue_count": len(delayed),
        "overdue_orders": delayed[:20],  # Limit to top 20
        "paused_count": len(paused_list),
        "paused_orders": paused_list[:10],
    }


def operational_risks(wo: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Identify operational risks from work order data."""
    risks = []

    if "execution_status" in wo.columns:
        # Risk: High number of paused orders
        paused = wo[wo["execution_status"] == "Paused"]
        if len(paused) > 0:
            risks.append({
                "type": "Paused/stuck work orders",
                "count": len(paused),
                "severity": "High" if len(paused) > 5 else "Medium",
                "sectors": paused["sector"].value_counts().to_dict() if "sector" in paused.columns else {},
            })

        # Risk: Work orders not started
        not_started = wo[wo["execution_status"] == "Not Started"]
        if len(not_started) > 0:
            risks.append({
                "type": "Work orders not yet started",
                "count": len(not_started),
                "severity": "Medium",
            })

    # Risk: Overdue work orders
    delayed = delayed_work_orders(wo, quality)
    if delayed["overdue_count"] > 0:
        risks.append({
            "type": "Overdue work orders (past end date)",
            "count": delayed["overdue_count"],
            "severity": "High",
        })

    # Risk: Sector concentration
    if "sector" in wo.columns:
        ongoing = wo[wo["execution_status"].isin(["Ongoing", "Not Started"])] if "execution_status" in wo.columns else wo
        if len(ongoing) > 0:
            sector_counts = ongoing["sector"].value_counts()
            total = len(ongoing)
            for sector, count in sector_counts.items():
                if count / total > 0.5 and total > 5:
                    risks.append({
                        "type": f"Operational concentration in {sector} ({count}/{total} active orders)",
                        "count": count,
                        "severity": "Medium",
                    })

    return {
        "risks": risks,
        "total_risk_count": len(risks),
        "high_severity_count": sum(1 for r in risks if r["severity"] == "High"),
    }


def work_order_by_sector(wo: pd.DataFrame, quality: DataQualityReport) -> Dict[str, Any]:
    """Work order breakdown by sector."""
    if "sector" not in wo.columns:
        return {"error": "Sector data not available"}

    sector_stats = []
    for sector, group in wo.groupby("sector"):
        if sector is None or pd.isna(sector):
            continue

        status_breakdown = {}
        if "execution_status" in group.columns:
            status_breakdown = group["execution_status"].value_counts().to_dict()

        invoice_total = group["invoice_amount"].sum() if "invoice_amount" in group.columns else 0

        sector_stats.append({
            "sector": sector,
            "total_orders": len(group),
            "status_breakdown": {k: int(v) for k, v in status_breakdown.items()},
            "invoice_total": invoice_total,
            "invoice_formatted": _format_inr(invoice_total) if invoice_total > 0 else "N/A",
        })

    sector_stats.sort(key=lambda x: x["total_orders"], reverse=True)

    return {
        "sectors": sector_stats,
        "total_sectors": len(sector_stats),
    }


# ============================================================
# CROSS-BOARD ANALYTICS
# ============================================================

def cross_board_analysis(deals: pd.DataFrame, wo: pd.DataFrame,
                         deal_quality: DataQualityReport,
                         wo_quality: DataQualityReport) -> Dict[str, Any]:
    """Cross-board analysis linking deals and work orders."""
    insights = []

    if "sector" in deals.columns and "sector" in wo.columns:
        # Compare pipeline sectors with operational sectors
        active_deals = deals[deals["deal_status"].isin(["Open", "On Hold"])]
        deal_sectors = active_deals.groupby("sector")["deal_value"].sum().to_dict() if "deal_value" in active_deals.columns else {}
        wo_sectors = wo["execution_status"].groupby(wo["sector"]).value_counts().unstack(fill_value=0) if "execution_status" in wo.columns else pd.DataFrame()

        for sector in deal_sectors:
            if sector in wo_sectors.index:
                paused = wo_sectors.loc[sector].get("Paused", 0)
                overdue_in_sector = 0
                if "end_date" in wo.columns:
                    now = datetime.now().strftime("%Y-%m-%d")
                    sector_wo = wo[(wo["sector"] == sector) & (wo["end_date"].notna()) & (wo["end_date"] < now)]
                    overdue_in_sector = len(sector_wo[~sector_wo["execution_status"].isin(["Completed"])])

                if (paused > 0 or overdue_in_sector > 0) and deal_sectors[sector] > 0:
                    insights.append({
                        "type": "execution_risk",
                        "sector": sector,
                        "pipeline_value": _format_inr(deal_sectors[sector]),
                        "paused_orders": int(paused),
                        "overdue_orders": overdue_in_sector,
                        "message": f"{sector} has {_format_inr(deal_sectors[sector])} in pipeline "
                                   f"but {paused + overdue_in_sector} work orders are paused/overdue — potential execution risk.",
                    })

    return {
        "cross_board_insights": insights,
        "insight_count": len(insights),
    }


# ============================================================
# LEADERSHIP UPDATE
# ============================================================

def leadership_update_metrics(deals: pd.DataFrame, wo: pd.DataFrame,
                              deal_quality: DataQualityReport,
                              wo_quality: DataQualityReport) -> Dict[str, Any]:
    """Compute all metrics needed for a leadership update."""

    # Pipeline summary
    pipeline = calculate_total_pipeline(deals, deal_quality)
    status = deal_status_summary(deals, deal_quality)
    quarter = pipeline_this_quarter(deals, deal_quality)
    sectors = pipeline_by_sector(deals, deal_quality)
    closing = deals_closing_soon(deals, deal_quality, days=30)
    deal_risks = sales_risks(deals, deal_quality)

    # Work order summary
    wo_status = work_order_status_summary(wo, wo_quality)
    wo_delayed = delayed_work_orders(wo, wo_quality)
    wo_risks = operational_risks(wo, wo_quality)

    # Cross-board
    cross = cross_board_analysis(deals, wo, deal_quality, wo_quality)

    # Wins (recently won deals)
    won_deals = deals[deals["deal_status"] == "Won"]
    recent_wins = []
    if "close_date" in won_deals.columns:
        thirty_days_ago = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
        recent = won_deals[won_deals["close_date"].notna() & (won_deals["close_date"] >= thirty_days_ago)]
        for _, row in recent.head(5).iterrows():
            recent_wins.append({
                "name": row.get("deal_name", "Unknown"),
                "value": _format_inr(row["deal_value"]) if pd.notna(row.get("deal_value")) else "N/A",
                "sector": row.get("sector", "N/A"),
            })

    return {
        "pipeline": pipeline,
        "deal_status": status,
        "quarter_pipeline": quarter,
        "sector_breakdown": sectors,
        "closing_soon": closing,
        "sales_risks": deal_risks,
        "work_order_status": wo_status,
        "delayed_orders": wo_delayed,
        "operational_risks": wo_risks,
        "cross_board": cross,
        "recent_wins": recent_wins,
        "deal_quality_notes": deal_quality.get_relevant_notes("leadership"),
        "wo_quality_notes": wo_quality.get_relevant_notes("leadership"),
    }
