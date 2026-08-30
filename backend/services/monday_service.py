"""Monday.com GraphQL API integration service.

Handles authentication, board fetching, pagination, column mapping,
and error handling for read-only access to monday.com boards.
"""

import httpx
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)

MONDAY_API_URL = "https://api.monday.com/v2"


class MondayServiceError(Exception):
    """Custom exception for Monday.com service errors."""
    pass


class MondayService:
    """Client for monday.com GraphQL API."""

    def __init__(self, api_token: str):
        if not api_token:
            raise MondayServiceError("Monday.com API token is not configured.")
        self.api_token = api_token
        self.headers = {
            "Authorization": api_token,
            "Content-Type": "application/json",
            "API-Version": "2024-10",
        }

    async def _execute_query(self, query: str, variables: Optional[Dict] = None) -> Dict:
        """Execute a GraphQL query against monday.com API."""
        payload: Dict[str, Any] = {"query": query}
        if variables:
            payload["variables"] = variables

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    MONDAY_API_URL,
                    json=payload,
                    headers=self.headers,
                )
                response.raise_for_status()
                data = response.json()

                if "errors" in data:
                    error_msgs = [e.get("message", "Unknown error") for e in data["errors"]]
                    raise MondayServiceError(f"Monday.com API errors: {'; '.join(error_msgs)}")

                if "error_message" in data:
                    raise MondayServiceError(f"Monday.com API error: {data['error_message']}")

                return data.get("data", {})

        except httpx.TimeoutException:
            raise MondayServiceError("Monday.com API request timed out. Please try again.")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                raise MondayServiceError("Invalid Monday.com API token. Please check your configuration.")
            elif e.response.status_code == 429:
                raise MondayServiceError("Monday.com API rate limit exceeded. Please wait and try again.")
            raise MondayServiceError(f"Monday.com API HTTP error: {e.response.status_code}")
        except httpx.RequestError as e:
            raise MondayServiceError(f"Network error connecting to Monday.com: {str(e)}")

    async def verify_connection(self) -> bool:
        """Verify that the API token is valid."""
        try:
            query = "query { me { id name } }"
            result = await self._execute_query(query)
            return "me" in result and result["me"] is not None
        except MondayServiceError:
            return False

    async def get_board_columns(self, board_id: str) -> List[Dict[str, str]]:
        """Fetch column definitions for a board.

        Returns list of dicts with 'id', 'title', and 'type' keys.
        """
        query = """
        query ($boardId: [ID!]!) {
            boards(ids: $boardId) {
                name
                columns {
                    id
                    title
                    type
                }
            }
        }
        """
        result = await self._execute_query(query, {"boardId": [board_id]})

        boards = result.get("boards", [])
        if not boards:
            raise MondayServiceError(f"Board with ID {board_id} not found. Please check your board ID.")

        return boards[0].get("columns", [])

    async def get_board_items(self, board_id: str, limit: int = 500) -> Tuple[List[Dict], List[Dict]]:
        """Fetch all items from a board with pagination.

        Returns:
            Tuple of (items, columns) where items are the board rows
            and columns are the column definitions.
        """
        all_items = []
        cursor = None
        columns = []

        # First query to get columns + first page of items
        first_query = """
        query ($boardId: [ID!]!, $limit: Int!) {
            boards(ids: $boardId) {
                name
                columns {
                    id
                    title
                    type
                }
                items_page(limit: $limit) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
        }
        """
        result = await self._execute_query(first_query, {"boardId": [board_id], "limit": limit})

        boards = result.get("boards", [])
        if not boards:
            raise MondayServiceError(f"Board with ID {board_id} not found.")

        board = boards[0]
        columns = board.get("columns", [])
        items_page = board.get("items_page", {})
        all_items.extend(items_page.get("items", []))
        cursor = items_page.get("cursor")

        # Paginate through remaining items
        while cursor:
            next_query = """
            query ($limit: Int!, $cursor: String!) {
                next_items_page(limit: $limit, cursor: $cursor) {
                    cursor
                    items {
                        id
                        name
                        column_values {
                            id
                            text
                            value
                            type
                        }
                    }
                }
            }
            """
            result = await self._execute_query(next_query, {"limit": limit, "cursor": cursor})
            next_page = result.get("next_items_page", {})
            all_items.extend(next_page.get("items", []))
            cursor = next_page.get("cursor")

        logger.info(f"Fetched {len(all_items)} items from board {board_id}")
        return all_items, columns

    async def check_board_exists(self, board_id: str) -> bool:
        """Check if a board exists and is accessible."""
        try:
            query = """
            query ($boardId: [ID!]!) {
                boards(ids: $boardId) {
                    id
                    name
                }
            }
            """
            result = await self._execute_query(query, {"boardId": [board_id]})
            boards = result.get("boards", [])
            return len(boards) > 0
        except MondayServiceError:
            return False

    @staticmethod
    def items_to_records(items: List[Dict], columns: List[Dict]) -> List[Dict[str, Any]]:
        """Convert monday.com items to flat dictionary records.

        Dynamically maps column IDs to column titles for readable keys.
        """
        # Build column ID -> title mapping
        col_map = {col["id"]: col["title"] for col in columns}

        records = []
        for item in items:
            record: Dict[str, Any] = {"item_id": item["id"], "name": item["name"]}

            for cv in item.get("column_values", []):
                col_title = col_map.get(cv["id"], cv["id"])
                # Use the 'text' field which is the human-readable value
                record[col_title] = cv.get("text", "")

            records.append(record)

        return records
