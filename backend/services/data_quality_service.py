"""Data quality tracking service.

Collects and reports data quality issues found during normalization
and analysis. Only surfaces issues relevant to the user's query.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class DataQualityReport:
    """Tracks data quality issues across a dataset."""

    issues: Dict[str, int] = field(default_factory=dict)
    details: List[str] = field(default_factory=list)

    def add_issue(self, issue_type: str, count: int = 1):
        """Record a data quality issue."""
        self.issues[issue_type] = self.issues.get(issue_type, 0) + count

    def add_detail(self, detail: str):
        """Add a specific detail about a data quality issue."""
        self.details.append(detail)

    @property
    def total_issues(self) -> int:
        return sum(self.issues.values())

    @property
    def has_issues(self) -> bool:
        return self.total_issues > 0

    def get_summary(self) -> List[str]:
        """Get human-readable summary of data quality issues."""
        summary = []
        issue_labels = {
            "missing_deal_value": "deals with missing monetary value",
            "missing_owner": "records with missing owner code",
            "missing_sector": "records with missing sector",
            "missing_status": "records with missing status",
            "missing_close_date": "deals with missing close date",
            "invalid_date": "records with invalid/unparseable dates",
            "missing_execution_status": "work orders with missing execution status",
            "missing_nature_of_work": "work orders with missing nature of work",
            "missing_serial_number": "work orders with missing serial number",
            "missing_start_date": "work orders with missing start date",
            "missing_end_date": "work orders with missing end date",
            "invalid_amount": "records with invalid monetary amounts",
            "missing_deal_stage": "deals with missing deal stage",
            "missing_product_type": "deals with missing product type",
            "missing_created_date": "deals with missing creation date",
            "duplicate_records": "potential duplicate records detected",
        }

        for issue_type, count in sorted(self.issues.items(), key=lambda x: -x[1]):
            label = issue_labels.get(issue_type, issue_type.replace("_", " "))
            summary.append(f"{count} {label}")

        return summary

    def get_relevant_notes(self, context: Optional[str] = None) -> List[str]:
        """Get data quality notes relevant to a specific analysis context.

        Only returns notes that materially affect the answer.
        """
        notes = []

        if context == "pipeline_value" or context == "deal_value":
            if "missing_deal_value" in self.issues:
                count = self.issues["missing_deal_value"]
                notes.append(
                    f"Note: {count} deals have no monetary value and are excluded from value calculations."
                )

        if context == "sector":
            if "missing_sector" in self.issues:
                count = self.issues["missing_sector"]
                notes.append(f"Note: {count} records have no sector assigned.")

        if context == "deals" or context == "pipeline":
            if "missing_deal_value" in self.issues:
                count = self.issues["missing_deal_value"]
                notes.append(f"Note: {count} deals have no monetary value assigned.")
            if "missing_close_date" in self.issues and self.issues["missing_close_date"] > 5:
                count = self.issues["missing_close_date"]
                notes.append(f"Note: {count} deals have no close date specified.")

        if context == "work_orders":
            if "missing_execution_status" in self.issues:
                count = self.issues["missing_execution_status"]
                notes.append(f"Note: {count} work orders have no execution status.")

        if context == "leadership":
            # Surface the most impactful issues
            notes = self.get_summary()[:3]  # Top 3 issues

        # Always include specific details if they exist
        for detail in self.details[:3]:
            notes.append(detail)

        return notes


def create_quality_report() -> DataQualityReport:
    """Factory function to create a new quality report."""
    return DataQualityReport()
