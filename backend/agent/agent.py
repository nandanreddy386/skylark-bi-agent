"""AI Agent orchestrator.

Coordinates the full pipeline:
User Question → Query Understanding → Data Fetching → Normalization
→ Deterministic Analytics → LLM Explanation → Response

The LLM interprets questions and explains results.
Python/Pandas calculates the actual numbers.
"""

import json
import logging
from typing import Dict, Any, Optional, List
from openai import AsyncOpenAI

from agent.query_router import QueryRouter
from agent.prompts import BUSINESS_EXPLANATION_PROMPT, LEADERSHIP_UPDATE_PROMPT
from services.monday_service import MondayService, MondayServiceError
from services.data_normalizer import normalize_deals, normalize_work_orders
from services.data_quality_service import DataQualityReport, create_quality_report
from services import analytics_service as analytics
from config import get_settings

logger = logging.getLogger(__name__)


class BIAgent:
    """Business Intelligence agent that orchestrates the analysis pipeline."""

    def __init__(self):
        settings = get_settings()
        self.monday = MondayService(settings.monday_api_token)
        self.openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.router = QueryRouter(self.openai_client, self.model)

        # Cache for board data (simple in-memory TTL cache)
        self._deals_cache = None
        self._wo_cache = None
        self._deals_quality = None
        self._wo_quality = None
        self._cache_valid = False

    async def process_question(self, user_message: str) -> Dict[str, Any]:
        """Process a user's business question end-to-end.

        Returns:
            Dict with 'answer', 'metrics', 'data_quality_notes', 'assumptions'
        """
        try:
            # Step 1: Classify the query
            classification = await self.router.classify_query(user_message)
            intent = classification["intent"]
            sector_filter = classification.get("sector_filter")
            assumptions = []

            logger.info(f"Processing question: intent={intent}, sector={sector_filter}")

            # Step 2: Determine which boards we need
            required = self.router.get_required_boards(intent)

            # Step 3: Fetch and normalize data
            deals_df = None
            wo_df = None
            deal_quality = create_quality_report()
            wo_quality = create_quality_report()

            if required["deals"]:
                deals_df, deal_quality = await self._get_normalized_deals()
            if required["work_orders"]:
                wo_df, wo_quality = await self._get_normalized_work_orders()

            # Step 4: Run deterministic analytics
            metrics = await self._run_analytics(
                intent, deals_df, wo_df, deal_quality, wo_quality,
                sector_filter=sector_filter,
            )

            # Track assumptions
            if sector_filter:
                assumptions.append(f"Filtering by sector: {sector_filter}")
            if intent == "pipeline_overview" and not sector_filter:
                assumptions.append("Showing overall pipeline across all sectors and active deals (Open + On Hold).")
            if intent == "pipeline_quarter":
                from services.analytics_service import _current_quarter_range
                q_start, q_end = _current_quarter_range()
                assumptions.append(f"Analyzing deals with tentative close dates in current quarter ({q_start} to {q_end}).")

            # Step 5: Generate business explanation using LLM
            answer = await self._explain_results(
                user_message, intent, metrics, deal_quality, wo_quality, assumptions
            )

            # Step 6: Collect relevant data quality notes
            quality_notes = []
            context = self._intent_to_quality_context(intent)
            if required["deals"]:
                quality_notes.extend(deal_quality.get_relevant_notes(context))
            if required["work_orders"]:
                quality_notes.extend(wo_quality.get_relevant_notes(context))

            # Deduplicate notes
            quality_notes = list(dict.fromkeys(quality_notes))

            return {
                "answer": answer,
                "metrics": metrics,
                "data_quality_notes": quality_notes,
                "assumptions": assumptions,
            }

        except MondayServiceError as e:
            logger.error(f"Monday.com error: {e}")
            return {
                "answer": f"I couldn't retrieve data from Monday.com: {str(e)}. Please check your API configuration.",
                "metrics": None,
                "data_quality_notes": [],
                "assumptions": [],
            }
        except Exception as e:
            logger.error(f"Agent error: {e}", exc_info=True)
            return {
                "answer": "I encountered an error processing your question. Please try rephrasing or check the system configuration.",
                "metrics": None,
                "data_quality_notes": [],
                "assumptions": [],
            }

    async def _get_normalized_deals(self):
        """Fetch and normalize deals data (with simple caching and CSV fallback)."""
        if self._deals_cache is not None and self._deals_quality is not None:
            return self._deals_cache, self._deals_quality

        settings = get_settings()
        try:
            items, columns = await self.monday.get_board_items(settings.deals_board_id)
            records = self.monday.items_to_records(items, columns)
            df, quality = normalize_deals(records)
        except Exception as e:
            logger.warning(f"Monday.com API unavailable ({e}). Falling back to local dataset (tools/deals_monday_import.csv)...")
            import os
            import pandas as pd
            csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "deals_monday_import.csv")
            if os.path.exists(csv_path):
                raw_df = pd.read_csv(csv_path)
                records = raw_df.to_dict(orient="records")
                df, quality = normalize_deals(records)
                quality.add_detail("Data loaded from local fallback CSV (Monday.com API key not configured).")
            else:
                raise e

        self._deals_cache = df
        self._deals_quality = quality
        return df, quality

    async def _get_normalized_work_orders(self):
        """Fetch and normalize work order data (with simple caching and CSV fallback)."""
        if self._wo_cache is not None and self._wo_quality is not None:
            return self._wo_cache, self._wo_quality

        settings = get_settings()
        try:
            items, columns = await self.monday.get_board_items(settings.work_orders_board_id)
            records = self.monday.items_to_records(items, columns)
            df, quality = normalize_work_orders(records)
        except Exception as e:
            logger.warning(f"Monday.com API unavailable ({e}). Falling back to local dataset (tools/work_orders_monday_import.csv)...")
            import os
            import pandas as pd
            csv_path = os.path.join(os.path.dirname(__file__), "..", "..", "tools", "work_orders_monday_import.csv")
            if os.path.exists(csv_path):
                raw_df = pd.read_csv(csv_path)
                records = raw_df.to_dict(orient="records")
                df, quality = normalize_work_orders(records)
                quality.add_detail("Data loaded from local fallback CSV (Monday.com API key not configured).")
            else:
                raise e

        self._wo_cache = df
        self._wo_quality = quality
        return df, quality

    def clear_cache(self):
        """Clear the data cache to force a fresh fetch."""
        self._deals_cache = None
        self._wo_cache = None
        self._deals_quality = None
        self._wo_quality = None

    async def _run_analytics(
        self, intent: str,
        deals_df, wo_df,
        deal_quality, wo_quality,
        sector_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Run the appropriate analytics functions based on intent."""

        metrics: Dict[str, Any] = {}

        if deals_df is not None and len(deals_df) > 0:
            if intent == "pipeline_overview":
                metrics["pipeline"] = analytics.calculate_total_pipeline(deals_df, deal_quality)
                metrics["by_sector"] = analytics.pipeline_by_sector(deals_df, deal_quality, sector_filter)
                metrics["by_stage"] = analytics.pipeline_by_stage(deals_df, deal_quality)
                metrics["deal_status"] = analytics.deal_status_summary(deals_df, deal_quality)

            elif intent == "pipeline_sector":
                metrics["by_sector"] = analytics.pipeline_by_sector(deals_df, deal_quality, sector_filter)
                if sector_filter:
                    metrics["pipeline_quarter"] = analytics.pipeline_this_quarter(deals_df, deal_quality, sector_filter)

            elif intent == "pipeline_quarter":
                metrics["pipeline_quarter"] = analytics.pipeline_this_quarter(deals_df, deal_quality, sector_filter)
                metrics["closing_soon"] = analytics.deals_closing_soon(deals_df, deal_quality, days=90)

            elif intent == "pipeline_value":
                metrics["pipeline"] = analytics.calculate_total_pipeline(deals_df, deal_quality)

            elif intent == "top_sector":
                metrics["by_sector"] = analytics.pipeline_by_sector(deals_df, deal_quality)

            elif intent == "deals_closing":
                metrics["closing_soon"] = analytics.deals_closing_soon(deals_df, deal_quality, days=30)

            elif intent == "high_value_deals":
                metrics["high_value"] = analytics.high_value_deals(deals_df, deal_quality)

            elif intent == "deal_status":
                metrics["deal_status"] = analytics.deal_status_summary(deals_df, deal_quality)

            elif intent == "sales_risks":
                metrics["sales_risks"] = analytics.sales_risks(deals_df, deal_quality)

        if wo_df is not None and len(wo_df) > 0:
            if intent == "work_order_status":
                metrics["wo_status"] = analytics.work_order_status_summary(wo_df, wo_quality)
                metrics["wo_by_sector"] = analytics.work_order_by_sector(wo_df, wo_quality)

            elif intent == "delayed_orders":
                metrics["delayed"] = analytics.delayed_work_orders(wo_df, wo_quality)

            elif intent == "operational_risks":
                metrics["op_risks"] = analytics.operational_risks(wo_df, wo_quality)
                metrics["delayed"] = analytics.delayed_work_orders(wo_df, wo_quality)

            elif intent == "work_order_sector":
                metrics["wo_by_sector"] = analytics.work_order_by_sector(wo_df, wo_quality)

        if intent == "leadership_update" and deals_df is not None and wo_df is not None:
            metrics["leadership"] = analytics.leadership_update_metrics(
                deals_df, wo_df, deal_quality, wo_quality
            )

        if intent == "cross_board" and deals_df is not None and wo_df is not None:
            metrics["cross_board"] = analytics.cross_board_analysis(
                deals_df, wo_df, deal_quality, wo_quality
            )
            metrics["pipeline"] = analytics.calculate_total_pipeline(deals_df, deal_quality)
            metrics["wo_status"] = analytics.work_order_status_summary(wo_df, wo_quality)

        if intent == "general":
            # Provide a broad overview
            if deals_df is not None and len(deals_df) > 0:
                metrics["pipeline"] = analytics.calculate_total_pipeline(deals_df, deal_quality)
                metrics["deal_status"] = analytics.deal_status_summary(deals_df, deal_quality)
            if wo_df is not None and len(wo_df) > 0:
                metrics["wo_status"] = analytics.work_order_status_summary(wo_df, wo_quality)

        return metrics

    async def _explain_results(
        self, user_message: str, intent: str,
        metrics: Dict[str, Any],
        deal_quality: DataQualityReport,
        wo_quality: DataQualityReport,
        assumptions: List[str],
    ) -> str:
        """Use the LLM to explain pre-computed analytics results."""

        # Choose the appropriate prompt
        if intent == "leadership_update":
            system_prompt = LEADERSHIP_UPDATE_PROMPT
        else:
            system_prompt = BUSINESS_EXPLANATION_PROMPT

        # Build context for the LLM
        context_parts = [
            f"User Question: {user_message}",
            f"Query Intent: {intent}",
            f"\nPre-computed Analytics Results (use these exact numbers):",
            json.dumps(metrics, indent=2, default=str),
        ]

        if assumptions:
            context_parts.append(f"\nAssumptions made: {'; '.join(assumptions)}")

        quality_notes = deal_quality.get_summary() + wo_quality.get_summary()
        if quality_notes:
            context_parts.append(f"\nData Quality Notes: {'; '.join(quality_notes[:5])}")

        context = "\n".join(context_parts)

        try:
            response = await self.openai_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": context},
                ],
                temperature=0.3,
                max_tokens=1500,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"LLM explanation error: {e}")
            # Fallback: return raw metrics summary
            return self._fallback_explanation(metrics, intent)

    @staticmethod
    def _fallback_explanation(metrics: Dict[str, Any], intent: str) -> str:
        """Generate a clean, structured executive Markdown summary without requiring LLM keys."""
        lines = []

        # 1. Closing Soon Deals
        if "closing_soon" in metrics:
            cs = metrics["closing_soon"]
            days = cs.get("within_days", 30)
            count = cs.get("count", 0)
            val = cs.get("total_value_formatted", "₹0")
            lines.append(f"## Deals Expected to Close Soon (Next {days} Days)\n")
            lines.append(f"* **Total Upcoming Closing Deals:** **{count}**")
            lines.append(f"* **Combined Deal Pipeline Value:** **{val}**\n")
            
            deals_list = cs.get("deals", [])
            if deals_list:
                lines.append("| Deal Name | Sector | Value | Expected Close Date | Stage |")
                lines.append("|---|---|---|---|---|")
                for d in deals_list[:8]:
                    lines.append(f"| **{d.get('deal_name', 'N/A')}** | {d.get('sector', 'N/A')} | {d.get('value_formatted', 'N/A')} | {d.get('close_date', 'N/A')} | {d.get('deal_stage', 'N/A')} |")
            else:
                lines.append("> ℹ️ *No active deals are currently scheduled to close within the specified timeframe.*")
            lines.append("")

        # 2. Sector Pipeline Breakdown
        if "by_sector" in metrics and "sectors" in metrics["by_sector"]:
            sec = metrics["by_sector"]
            lines.append("## Sector Pipeline Breakdown\n")
            if "top_sector" in sec:
                lines.append(f"🏆 **Highest Value Sector:** **{sec.get('top_sector', 'N/A')}** with **{sec.get('top_sector_value', 'N/A')}** in active pipeline.\n")
            lines.append("| Sector | Deal Count | Total Pipeline | Avg Deal Size |")
            lines.append("|---|---|---|---|")
            for s in sec.get("sectors", []):
                lines.append(f"| **{s['sector']}** | {s['deal_count']} | {s['total_value_formatted']} | ₹{s['avg_value']:,.0f} |")
            lines.append("")

        # 3. Overall Pipeline Overview
        if "pipeline" in metrics:
            p = metrics["pipeline"]
            lines.append("## Executive Sales Pipeline Overview\n")
            lines.append(f"* **Total Active Pipeline Value:** **{p.get('total_pipeline_formatted', 'N/A')}**")
            lines.append(f"* **Active Deals Count:** **{p.get('active_deal_count', 0)}**")
            lines.append(f"* **Average Deal Size:** **{p.get('average_deal_formatted', 'N/A')}**")
            if "win_rate" in metrics:
                lines.append(f"* **Historical Win Rate:** **{metrics.get('win_rate', {}).get('win_rate', 'N/A')}**")
            lines.append("")

        # 4. Work Order Status & Delayed Orders
        if "wo_status" in metrics:
            wo = metrics["wo_status"]
            lines.append("## Work Order Operational Performance\n")
            lines.append(f"* **Total Tracked Orders:** **{wo.get('total_work_orders', 0)}**")
            lines.append(f"* **Completion Rate:** **{wo.get('completion_rate', '0%')}**")
            lines.append(f"* **Active Ongoing Orders:** **{wo.get('active_count', 0)}**")
            lines.append(f"* **Paused / Struck Orders:** **{wo.get('paused_count', 0)}**")
            lines.append("")

        if "delayed_orders" in metrics:
            del_wo = metrics["delayed_orders"]
            lines.append("## Operational Delay Tracker\n")
            lines.append(f"⚠️ **Total Overdue / Delayed Orders:** **{del_wo.get('overdue_count', 0)}**\n")
            orders = del_wo.get("orders", [])
            if orders:
                lines.append("| Order ID / Name | Customer | Delayed Days | Delay Reason | Status |")
                lines.append("|---|---|---|---|---|")
                for o in orders[:8]:
                    lines.append(f"| **{o.get('serial_number') or o.get('deal_name', 'Order')}** | {o.get('customer_code', 'N/A')} | **{o.get('delayed_days', 0)} days** | {o.get('delay_reason', 'Under Review')} | {o.get('execution_status', 'Ongoing')} |")
                lines.append("")

        # 5. Sales Risks
        if "sales_risks" in metrics:
            sr = metrics["sales_risks"]
            lines.append("## Sales Risk Audit\n")
            lines.append(f"🚨 **Total Sales Risks Identified:** **{sr.get('total_risk_count', 0)}**")
            lines.append(f"🔴 **High Severity Risks:** **{sr.get('high_severity_count', 0)}**\n")
            r_list = sr.get("risks", [])
            if r_list:
                for r in r_list:
                    lines.append(f"* **{r.get('type', 'Risk')}** ({r.get('severity', 'Medium')} Severity): {r.get('description', '')} — *Impact: {r.get('impact_value_formatted', 'N/A')}*")
                lines.append("")

        # 6. Operational Risks
        if "operational_risks" in metrics:
            op_r = metrics["operational_risks"]
            lines.append("## Operational & Delivery Risks\n")
            lines.append(f"⚠️ **Total Delivery Risks:** **{op_r.get('total_risk_count', 0)}**\n")
            r_list = op_r.get("risks", [])
            if r_list:
                for r in r_list:
                    lines.append(f"* **{r.get('type', 'Operational Risk')}** ({r.get('severity', 'Medium')} Severity): {r.get('description', '')}")
                lines.append("")

        # 7. High Value Deals
        if "high_value_deals" in metrics:
            hvd = metrics["high_value_deals"]
            lines.append("## High Value Deal Opportunities\n")
            deals = hvd.get("deals", [])
            if deals:
                lines.append("| Deal Name | Sector | Value | Status | Stage |")
                lines.append("|---|---|---|---|---|")
                for d in deals[:8]:
                    lines.append(f"| **{d.get('deal_name', 'N/A')}** | {d.get('sector', 'N/A')} | **{d.get('value_formatted', 'N/A')}** | {d.get('deal_status', 'N/A')} | {d.get('deal_stage', 'N/A')} |")
                lines.append("")

        # 8. Leadership Summary
        if "leadership" in metrics:
            lead = metrics["leadership"]
            lines.append("# Skylark Drones — Executive Leadership Update\n")
            lines.append("### Executive Overview")
            p_val = lead.get('pipeline', {}).get('total_pipeline_formatted', 'N/A')
            lines.append(f"The active sales pipeline currently stands at **{p_val}** across active sector opportunities.\n")
            lines.append("### Top Sector Pipeline")
            for s in lead.get('sector_breakdown', {}).get('sectors', [])[:4]:
                lines.append(f"* **{s['sector']}**: **{s['total_value_formatted']}** ({s['deal_count']} deals)")
            lines.append("")

        if not lines:
            lines.append("## Analytics Overview\n")
            for key, value in metrics.items():
                if isinstance(value, dict):
                    lines.append(f"### {key.replace('_', ' ').title()}\n")
                    for k, v in value.items():
                        if not isinstance(v, (dict, list)):
                            lines.append(f"* **{k.replace('_', ' ').title()}:** {v}")

        return "\n".join(lines)

    @staticmethod
    def _intent_to_quality_context(intent: str) -> str:
        """Map intent to data quality context."""
        mapping = {
            "pipeline_overview": "pipeline",
            "pipeline_sector": "sector",
            "pipeline_quarter": "pipeline",
            "pipeline_value": "pipeline_value",
            "top_sector": "sector",
            "deals_closing": "deals",
            "high_value_deals": "deal_value",
            "deal_status": "deals",
            "sales_risks": "deals",
            "work_order_status": "work_orders",
            "delayed_orders": "work_orders",
            "operational_risks": "work_orders",
            "work_order_sector": "work_orders",
            "leadership_update": "leadership",
            "cross_board": "leadership",
        }
        return mapping.get(intent, "deals")
