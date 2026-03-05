"""
Analytics service for Claude Code usage metrics.

Computes aggregations, hourly usage, event distributions,
and anomaly detection on token usage.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
from sqlalchemy import func, and_
from sqlalchemy.orm import Session
from sklearn.ensemble import IsolationForest

from backend.database import get_db, IS_SQLITE
from backend.models import TelemetryEvent

logger = logging.getLogger(__name__)


def _hour_trunc(column):
    """Hour truncation compatible with SQLite and PostgreSQL."""
    if IS_SQLITE:
        return func.strftime("%Y-%m-%d %H:00:00", column)
    return func.date_trunc("hour", column)


def get_overview(db: Session, hours: Optional[int] = 24) -> Dict[str, Any]:
    """
    Compute overview metrics for the dashboard.
    
    Args:
        db: Database session.
        hours: Optional time window in hours (default 24). None = all time.
        
    Returns:
        Dict with total_input_tokens, total_output_tokens, total_cache_read,
        cache_efficiency, cost_per_1k_output, productivity_ratio, peak_leverage,
        avg_tokens_per_session, most_common_event_type.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours) if hours else None
    q = db.query(TelemetryEvent).filter(TelemetryEvent.event_type == "api_request")
    if cutoff:
        q = q.filter(TelemetryEvent.timestamp >= cutoff)
    
    events = q.all()
    
    total_input = sum(e.input_tokens for e in events)
    total_output = sum(e.output_tokens for e in events)
    total_cache_read = sum(e.cache_read_tokens for e in events)
    total_cache_create = sum(e.cache_creation_tokens for e in events)
    total_cost = sum(e.cost_usd for e in events)
    
    # Cache efficiency: cache_read / (cache_read + input) when denominator > 0
    total_without_cache = total_input + total_output
    cache_denom = total_cache_read + total_input
    cache_efficiency = (total_cache_read / cache_denom * 100) if cache_denom > 0 else 0.0
    
    # Cost per 1K output tokens
    cost_per_1k = (total_cost / (total_output / 1000)) if total_output > 0 else 0.0
    
    # Productivity ratio: output / input (how much output per input)
    productivity_ratio = (total_output / total_input) if total_input > 0 else 0.0
    
    # Peak leverage: max single-event output/input ratio
    peak_leverage = 0.0
    for e in events:
        if e.input_tokens > 0 and (e.output_tokens / e.input_tokens) > peak_leverage:
            peak_leverage = e.output_tokens / e.input_tokens
    
    # Sessions
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours) if hours else None
    q_sessions = db.query(TelemetryEvent.session_id).distinct()
    if cutoff:
        q_sessions = q_sessions.filter(TelemetryEvent.timestamp >= cutoff)
    session_count = q_sessions.count()
    total_tokens_all = (
        db.query(
            func.sum(TelemetryEvent.input_tokens + TelemetryEvent.output_tokens +
                     TelemetryEvent.cache_read_tokens + TelemetryEvent.cache_creation_tokens)
        )
        .filter(TelemetryEvent.event_type == "api_request")
    )
    if cutoff:
        total_tokens_all = total_tokens_all.filter(TelemetryEvent.timestamp >= cutoff)
    total_tokens_val = total_tokens_all.scalar() or 0
    avg_tokens_per_session = (total_tokens_val / session_count) if session_count > 0 else 0
    
    # Most common event type (all events, not just api_request)
    q_ev = db.query(TelemetryEvent.event_type, func.count(TelemetryEvent.id)).group_by(
        TelemetryEvent.event_type
    )
    if hours:
        q_ev = q_ev.filter(TelemetryEvent.timestamp >= cutoff)
    ev_counts = q_ev.all()
    most_common = max(ev_counts, key=lambda x: x[1])[0] if ev_counts else "api_request"
    
    return {
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_cache_read": total_cache_read,
        "total_cache_creation": total_cache_create,
        "cache_efficiency_pct": round(cache_efficiency, 2),
        "cost_per_1k_output": round(cost_per_1k, 4),
        "productivity_ratio": round(productivity_ratio, 2),
        "peak_leverage": round(peak_leverage, 2),
        "avg_tokens_per_session": int(avg_tokens_per_session),
        "most_common_event_type": most_common,
        "total_cost_usd": round(total_cost, 4),
        "session_count": session_count,
    }


def get_token_by_role(db: Session, hours: Optional[int] = 24) -> List[Dict[str, Any]]:
    """
    Aggregate token consumption by role (practice).
    
    Args:
        db: Database session.
        hours: Optional time window. None = all time.
        
    Returns:
        List of {role, total_tokens, input_tokens, output_tokens, cache_read, cache_create}.
    """
    q = (
        db.query(
            TelemetryEvent.role,
            func.sum(TelemetryEvent.input_tokens + TelemetryEvent.output_tokens +
                     TelemetryEvent.cache_read_tokens + TelemetryEvent.cache_creation_tokens).label("total"),
            func.sum(TelemetryEvent.input_tokens).label("input"),
            func.sum(TelemetryEvent.output_tokens).label("output"),
            func.sum(TelemetryEvent.cache_read_tokens).label("cache_read"),
            func.sum(TelemetryEvent.cache_creation_tokens).label("cache_create"),
        )
        .filter(TelemetryEvent.event_type == "api_request")
        .group_by(TelemetryEvent.role)
    )
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = q.filter(TelemetryEvent.timestamp >= cutoff)
    
    rows = q.all()
    return [
        {
            "role": r.role or "Unknown",
            "total_tokens": r.total or 0,
            "input_tokens": r.input or 0,
            "output_tokens": r.output or 0,
            "cache_read_tokens": r.cache_read or 0,
            "cache_creation_tokens": r.cache_create or 0,
        }
        for r in rows
    ]


def get_hourly_usage(db: Session, hours: int = 168) -> List[Dict[str, Any]]:
    """
    Aggregate token usage by hour for line charts.
    
    Args:
        db: Database session.
        hours: Number of hours to look back (default 168 = 1 week).
        
    Returns:
        List of {hour, total_tokens, input_tokens, output_tokens, cache_read, cache_create}.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    hour_expr = _hour_trunc(TelemetryEvent.timestamp)
    q = (
        db.query(
            hour_expr.label("hour"),
            func.sum(TelemetryEvent.input_tokens + TelemetryEvent.output_tokens +
                     TelemetryEvent.cache_read_tokens + TelemetryEvent.cache_creation_tokens).label("total"),
            func.sum(TelemetryEvent.input_tokens).label("input"),
            func.sum(TelemetryEvent.output_tokens).label("output"),
            func.sum(TelemetryEvent.cache_read_tokens).label("cache_read"),
            func.sum(TelemetryEvent.cache_creation_tokens).label("cache_create"),
        )
        .filter(TelemetryEvent.event_type == "api_request", TelemetryEvent.timestamp >= cutoff)
        .group_by(hour_expr)
        .order_by(hour_expr)
    )
    rows = q.all()
    return [
        {
            "hour": r.hour.isoformat() if hasattr(r.hour, "isoformat") else str(r.hour) if r.hour else None,
            "total_tokens": r.total or 0,
            "input_tokens": r.input or 0,
            "output_tokens": r.output or 0,
            "cache_read_tokens": r.cache_read or 0,
            "cache_creation_tokens": r.cache_create or 0,
        }
        for r in rows
    ]


def get_event_type_distribution(db: Session, hours: Optional[int] = 24) -> List[Dict[str, Any]]:
    """
    Event type distribution for pie chart.
    
    Returns list of {event_type, count, percentage}.
    """
    q = db.query(TelemetryEvent.event_type, func.count(TelemetryEvent.id)).group_by(
        TelemetryEvent.event_type
    )
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = q.filter(TelemetryEvent.timestamp >= cutoff)
    rows = q.all()
    total = sum(r[1] for r in rows)
    return [
        {
            "event_type": r[0],
            "count": r[1],
            "percentage": round(r[1] / total * 100, 2) if total > 0 else 0,
        }
        for r in rows
    ]


def get_tokens_by_type(db: Session, hours: Optional[int] = 24) -> List[Dict[str, Any]]:
    """
    Token breakdown by type (input, output, cacheRead, cacheCreation) for donut chart.
    """
    q = db.query(
        func.sum(TelemetryEvent.input_tokens).label("input"),
        func.sum(TelemetryEvent.output_tokens).label("output"),
        func.sum(TelemetryEvent.cache_read_tokens).label("cache_read"),
        func.sum(TelemetryEvent.cache_creation_tokens).label("cache_create"),
    ).filter(TelemetryEvent.event_type == "api_request")
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = q.filter(TelemetryEvent.timestamp >= cutoff)
    row = q.first()
    if not row:
        return []
    total = (row.input or 0) + (row.output or 0) + (row.cache_read or 0) + (row.cache_create or 0)
    if total == 0:
        return []
    result = []
    for name, val in [
        ("input", row.input or 0),
        ("output", row.output or 0),
        ("cacheRead", row.cache_read or 0),
        ("cacheCreation", row.cache_create or 0),
    ]:
        if val > 0:
            result.append({
                "type": name,
                "count": val,
                "percentage": round(val / total * 100, 2),
            })
    return result


def get_tokens_by_model(db: Session, hours: Optional[int] = 24) -> List[Dict[str, Any]]:
    """
    Token consumption by model for donut chart.
    """
    q = (
        db.query(
            TelemetryEvent.model,
            func.sum(TelemetryEvent.input_tokens + TelemetryEvent.output_tokens +
                     TelemetryEvent.cache_read_tokens + TelemetryEvent.cache_creation_tokens).label("total"),
        )
        .filter(TelemetryEvent.event_type == "api_request", TelemetryEvent.model.isnot(None))
        .group_by(TelemetryEvent.model)
    )
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = q.filter(TelemetryEvent.timestamp >= cutoff)
    rows = q.all()
    total = sum(r.total for r in rows)
    return [
        {
            "model": r.model,
            "count": r.total,
            "percentage": round(r.total / total * 100, 2) if total > 0 else 0,
        }
        for r in rows
    ]


def get_hourly_usage_by_model(db: Session, hours: int = 168) -> List[Dict[str, Any]]:
    """
    Hourly token usage broken down by model for stacked line chart.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    hour_expr = _hour_trunc(TelemetryEvent.timestamp)
    q = (
        db.query(
            hour_expr.label("hour"),
            TelemetryEvent.model,
            func.sum(
                TelemetryEvent.input_tokens + TelemetryEvent.output_tokens +
                TelemetryEvent.cache_read_tokens + TelemetryEvent.cache_creation_tokens
            ).label("total"),
        )
        .filter(
            TelemetryEvent.event_type == "api_request",
            TelemetryEvent.model.isnot(None),
            TelemetryEvent.timestamp >= cutoff,
        )
        .group_by(hour_expr, TelemetryEvent.model)
        .order_by(hour_expr)
    )
    return [{"hour": r.hour.isoformat() if hasattr(r.hour, "isoformat") else str(r.hour) if r.hour else None, "model": r.model, "total_tokens": r.total or 0} for r in q.all()]


def get_cost_by_model(db: Session, hours: Optional[int] = 24) -> List[Dict[str, Any]]:
    """
    Cost by model for bar chart.
    """
    q = (
        db.query(
            TelemetryEvent.model,
            func.sum(TelemetryEvent.cost_usd).label("cost"),
        )
        .filter(TelemetryEvent.event_type == "api_request", TelemetryEvent.model.isnot(None))
        .group_by(TelemetryEvent.model)
    )
    if hours:
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        q = q.filter(TelemetryEvent.timestamp >= cutoff)
    rows = q.all()
    return [{"model": r.model, "cost_usd": round(r.cost or 0, 4)} for r in rows]


def detect_anomalies(
    db: Session,
    hours: int = 168,
    contamination: float = 0.05,
) -> Tuple[List[Dict[str, Any]], List[str]]:
    """
    Detect anomalies in hourly token usage using IsolationForest.
    
    Args:
        db: Database session.
        hours: Lookback window in hours.
        contamination: Expected proportion of anomalies (0.01-0.1).
        
    Returns:
        Tuple of (anomaly_records, anomaly_hours).
        anomaly_records: List of {hour, total_tokens, is_anomaly, anomaly_score}.
        anomaly_hours: List of hour strings that are anomalies (for highlighting).
    """
    hourly = get_hourly_usage(db, hours=hours)
    if len(hourly) < 10:
        return hourly, []
    
    df = pd.DataFrame(hourly)
    df["hour"] = pd.to_datetime(df["hour"])
    df = df.sort_values("hour").reset_index(drop=True)
    
    X = df[["total_tokens"]].values
    
    model = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    predictions = model.fit_predict(X)
    scores = model.decision_function(X)
    
    df["is_anomaly"] = predictions == -1
    df["anomaly_score"] = scores
    
    anomaly_hours = df[df["is_anomaly"]]["hour"].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()
    
    records = [
        {
            "hour": r["hour"].isoformat() if hasattr(r["hour"], "isoformat") else str(r["hour"]),
            "total_tokens": int(r["total_tokens"]),
            "input_tokens": int(r["input_tokens"]),
            "output_tokens": int(r["output_tokens"]),
            "cache_read_tokens": int(r["cache_read_tokens"]),
            "cache_creation_tokens": int(r["cache_creation_tokens"]),
            "is_anomaly": bool(r["is_anomaly"]),
            "anomaly_score": float(r["anomaly_score"]),
        }
        for r in df.to_dict("records")
    ]
    
    return records, anomaly_hours
