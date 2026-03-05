"""
Analytics API endpoints.

Provides programmatic access to Claude Code usage metrics,
hourly aggregations, and anomaly detection results.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services import analytics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])


def get_db_session():
    """Dependency to get database session."""
    from backend.database import SessionLocal
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/overview")
def get_overview(
    hours: Optional[int] = Query(default=24, ge=1, le=720, description="Time window in hours"),
    db: Session = Depends(get_db_session),
):
    """
    Get overview metrics: token counts, cache efficiency, cost, productivity.
    """
    return analytics.get_overview(db, hours=hours)


@router.get("/token-by-role")
def token_by_role(
    hours: Optional[int] = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get total token consumption aggregated by role (practice).
    """
    return analytics.get_token_by_role(db, hours=hours)


@router.get("/hourly-usage")
def hourly_usage(
    hours: int = Query(default=168, ge=1, le=720, description="Lookback hours (default 1 week)"),
    db: Session = Depends(get_db_session),
):
    """
    Get hourly token usage aggregation for line charts.
    """
    return analytics.get_hourly_usage(db, hours=hours)


@router.get("/event-type-distribution")
def event_type_distribution(
    hours: Optional[int] = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get event type distribution for pie chart.
    """
    return analytics.get_event_type_distribution(db, hours=hours)


@router.get("/tokens-by-type")
def tokens_by_type(
    hours: Optional[int] = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get token breakdown by type: input, output, cacheRead, cacheCreation.
    """
    return analytics.get_tokens_by_type(db, hours=hours)


@router.get("/tokens-by-model")
def tokens_by_model(
    hours: Optional[int] = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get token consumption by model for donut chart.
    """
    return analytics.get_tokens_by_model(db, hours=hours)


@router.get("/hourly-usage-by-model")
def hourly_usage_by_model(
    hours: int = Query(default=168, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get hourly token usage by model for stacked line chart.
    """
    return analytics.get_hourly_usage_by_model(db, hours=hours)


@router.get("/tool-usage-distribution")
def tool_usage_distribution(
    hours: Optional[int] = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get tool usage distribution for pie/bar chart (tool_decision + tool_result).
    """
    return analytics.get_tool_usage_distribution(db, hours=hours)


@router.get("/cost-by-model")
def cost_by_model(
    hours: Optional[int] = Query(default=24, ge=1, le=720),
    db: Session = Depends(get_db_session),
):
    """
    Get cost by model for bar chart.
    """
    return analytics.get_cost_by_model(db, hours=hours)


@router.get("/anomalies")
def get_anomalies(
    hours: int = Query(default=168, ge=24, le=720),
    contamination: float = Query(default=0.05, ge=0.01, le=0.2),
    db: Session = Depends(get_db_session),
):
    """
    Detect anomalies in hourly token usage using IsolationForest.
    Returns hourly data with anomaly flags and list of anomaly hours for chart highlighting.
    """
    records, anomaly_hours = analytics.detect_anomalies(
        db, hours=hours, contamination=contamination
    )
    return {
        "hourly_data": records,
        "anomaly_hours": anomaly_hours,
    }
