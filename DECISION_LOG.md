# Decision Log: Skylark Drones Monday.com BI Agent

**Candidate / Author:** Full Stack Developer & AI Agent Architect  
**Project:** Skylark Drones Technical Assignment — Monday.com BI Agent  
**Date:** August 2026  

---

## 1. Executive Summary & Problem Interpretation

Founders and executives require instant, deterministic business intelligence from operational and sales data stored in Monday.com. In real-world enterprise environments, raw data imported into Monday.com boards (such as Deal Funnel trackers and Work Order trackers) contains severe data quality issues: inconsistent date formats, missing fields, sector typos, `#VALUE!` formula errors, and fragmented multi-column layouts.

To address this challenge, we architected the **Skylark Monday.com BI Agent** — a full-stack, dual-board conversational analytics engine that enforces **Zero AI Calculation Hallucination** by separating analytical computation (Pandas) from natural language summary generation (LLM / Executive Templates).

---

## 2. Key Assumptions Made

1. **Board Structure & Column Types**:
   - **Deals Board**: Expected standard columns for `Deal Name`, `Sector/Industry`, `Deal Stage`, `Deal Value (INR)`, `Close Date`, `Deal Status (Won/Lost/Open)`.
   - **Work Order Tracker Board**: Expected columns for `Order ID / Serial Number`, `Customer Code`, `Execution Status`, `Planned Delivery Date`, `Actual Delivery Date`, `Delay Reason`, `Sector`.
2. **Data Normalization & Cleaning Rules**:
   - Deal values containing text currency symbols (e.g., `₹`, `Cr`, `Lakhs`, `,`) are parsed into standardized numeric INR float values.
   - Dates in mixed formats (`DD/MM/YYYY`, `YYYY-MM-DD`, `DD-MMM-YY`) are parsed into ISO 8601 timestamps.
   - Missing sectors default to `"Unassigned"` to prevent data loss during aggregation.
3. **Closing Window & Delays**:
   - "Deals closing soon" defaults to an analytical window of **30 calendar days**.
   - Work order delays are computed whenever `Actual Delivery Date > Planned Delivery Date` or when an active order is past its planned delivery date.

---

## 3. Key Architectural Trade-offs & Rationale

| Architecture Choice | Trade-off Made | Why This Decision Was Chosen |
| :--- | :--- | :--- |
| **Deterministic Pandas Math vs. LLM Math** | Calculated metrics using Pandas in Python instead of letting the LLM compute numbers. | **Zero Hallucination Guarantee**: LLMs frequently miscalculate multi-row sums or averages. By calculating all metrics deterministically in Pandas, 100% of reported figures are guaranteed accurate. |
| **Monday.com GraphQL API vs. MCP** | Built a custom Monday.com GraphQL client with cursor pagination instead of relying solely on MCP. | **Granular Control & Speed**: GraphQL allows precise query field selection, cursor pagination for large boards (>300 items), and exact error code handling. |
| **Dual-Mode Execution (Live + Local Fallback)** | Implemented automatic CSV fallback when Monday.com API credentials are not configured. | **Graceful Resilience & Demo Reliability**: Evaluation reviewers can immediately test the fully functional UI without setting up live Monday.com API keys. |
| **Rule-Based Keyword Fallback for Intent Router** | Added keyword fallback alongside LLM intent classification (`query_router.py`). | **High Availability**: If OpenAI API limits are exceeded or network connectivity drops, query intent routing continues working seamlessly. |

---

## 4. Interpretation of "Leadership Updates"

We interpreted **"Leadership Updates"** as a holistic, cross-board executive report designed for C-level decision-makers. Rather than querying a single board, a Leadership Update:
1. **Aggregates Pipeline & Win Rate**: Summarizes total active pipeline value (INR), total deal count, top revenue sector, and historical win rate from the Deals Board.
2. **Audits High-Value Risks**: Identifies high-severity sales risks (e.g., stalled high-value deals in negotiation).
3. **Tracks Operational Delivery**: Cross-references active work order execution rates, completion percentages, and critical operational bottlenecks from the Work Order Tracker Board.
4. **Delivers Actionable Insights**: Highlights key revenue drivers and operational risks requiring immediate intervention.

---

## 5. What We Would Do Differently With More Time

1. **Automated Monday.com Schema Migration Script**: Build a one-click CLI script using the Monday.com Mutation API to automatically create board columns, options, and import extracted CSVs directly into a user's Monday.com workspace.
2. **Interactive Visual Charts**: Add Recharts / Chart.js components to the React frontend for visual pipeline funnel visualization and sector distribution pie charts.
3. **Conversational Memory**: Implement multi-turn conversational session history to support follow-up questions like *"Break down the top sector by deal stage"*.
4. **Role-Based Access Control (RBAC)**: Add authentication layers to restrict sensitive financial metrics based on user role (e.g. Sales Manager vs. Founder).
