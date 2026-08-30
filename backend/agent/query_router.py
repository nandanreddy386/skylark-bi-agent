"""Query router for intent detection and classification.

Uses the LLM to classify user questions into specific intents,
then routes to the appropriate analytics functions.
"""

import json
import logging
from typing import Dict, Any, Optional
from openai import AsyncOpenAI
from agent.prompts import QUERY_CLASSIFICATION_PROMPT

logger = logging.getLogger(__name__)


class QueryRouter:
    """Classifies user questions and routes to appropriate analytics."""

    def __init__(self, openai_client: AsyncOpenAI, model: str = "gpt-4o-mini"):
        self.client = openai_client
        self.model = model

    async def classify_query(self, user_message: str) -> Dict[str, Any]:
        """Classify a user's question into an intent with optional filters.

        Returns:
            Dict with 'intent', 'sector_filter', 'time_filter', 'reasoning'
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": QUERY_CLASSIFICATION_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0,
                max_tokens=200,
                response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            result = json.loads(content)

            # Validate required fields
            if "intent" not in result:
                result["intent"] = "general"

            # Normalize sector filter
            if result.get("sector_filter") in (None, "null", "None", ""):
                result["sector_filter"] = None

            if result.get("time_filter") in (None, "null", "None", ""):
                result["time_filter"] = None

            logger.info(f"Query classified: intent={result['intent']}, sector={result.get('sector_filter')}")
            return result

        except json.JSONDecodeError:
            logger.warning("Failed to parse query classification response as JSON")
            return {"intent": "general", "sector_filter": None, "time_filter": None}
        except Exception as e:
            logger.warning(f"OpenAI API classification error ({e}). Using keyword-based fallback classifier...")
            msg_lower = user_message.lower()

            # Rule-based fallback classification
            intent = "general"
            sector = None

            # Detect sectors
            for s in ["mining", "renewables", "railways", "powerline", "construction", "dsp", "aviation", "manufacturing"]:
                if s in msg_lower:
                    sector = s.capitalize()
                    break

            if "leadership" in msg_lower or "executive" in msg_lower or "summary" in msg_lower:
                intent = "leadership_update"
            elif "highest" in msg_lower and "sector" in msg_lower or "top sector" in msg_lower:
                intent = "top_sector"
            elif "sector" in msg_lower and ("pipeline" in msg_lower or "deal" in msg_lower):
                intent = "pipeline_sector"
            elif "quarter" in msg_lower or "this q" in msg_lower:
                intent = "pipeline_quarter"
            elif "closing" in msg_lower or "close soon" in msg_lower:
                intent = "deals_closing"
            elif "high value" in msg_lower or "biggest deal" in msg_lower:
                intent = "high_value_deals"
            elif "sales risk" in msg_lower or "risk" in msg_lower and "deal" in msg_lower:
                intent = "sales_risks"
            elif "operational risk" in msg_lower or "risk" in msg_lower:
                intent = "operational_risks"
            elif "delayed" in msg_lower or "overdue" in msg_lower:
                intent = "delayed_orders"
            elif "work order" in msg_lower or "order" in msg_lower:
                intent = "work_order_status"
            elif "pipeline" in msg_lower or "deal" in msg_lower:
                intent = "pipeline_overview"

            return {"intent": intent, "sector_filter": sector, "time_filter": None}

    @staticmethod
    def get_required_boards(intent: str) -> Dict[str, bool]:
        """Determine which boards are needed for a given intent."""
        deals_intents = {
            "pipeline_overview", "pipeline_sector", "pipeline_quarter",
            "pipeline_value", "top_sector", "deals_closing", "high_value_deals",
            "deal_status", "sales_risks",
        }
        wo_intents = {
            "work_order_status", "delayed_orders", "operational_risks",
            "work_order_sector",
        }
        both_intents = {
            "leadership_update", "cross_board", "general",
        }

        if intent in both_intents:
            return {"deals": True, "work_orders": True}
        elif intent in deals_intents:
            return {"deals": True, "work_orders": False}
        elif intent in wo_intents:
            return {"deals": False, "work_orders": True}
        else:
            return {"deals": True, "work_orders": True}
