"""
API client for fetching analytics data from FastAPI backend.
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from dashboard.config import API_BASE_URL

logger = logging.getLogger(__name__)


def _get(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """GET request to analytics API."""
    url = f"{API_BASE_URL}{path}"
    try:
        resp = requests.get(url, params=params or {}, timeout=30)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        logger.error("API request failed: %s", e)
        raise


def fetch_overview(hours: int = 24) -> Dict[str, Any]:
    """Fetch overview metrics."""
    return _get("/analytics/overview", {"hours": hours})


def fetch_token_by_role(hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch token consumption by role."""
    return _get("/analytics/token-by-role", {"hours": hours})


def fetch_hourly_usage(hours: int = 168) -> List[Dict[str, Any]]:
    """Fetch hourly token usage."""
    return _get("/analytics/hourly-usage", {"hours": hours})


def fetch_event_type_distribution(hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch event type distribution."""
    return _get("/analytics/event-type-distribution", {"hours": hours})


def fetch_tokens_by_type(hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch token breakdown by type."""
    return _get("/analytics/tokens-by-type", {"hours": hours})


def fetch_tokens_by_model(hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch token consumption by model."""
    return _get("/analytics/tokens-by-model", {"hours": hours})


def fetch_hourly_usage_by_model(hours: int = 168) -> List[Dict[str, Any]]:
    """Fetch hourly token usage by model."""
    return _get("/analytics/hourly-usage-by-model", {"hours": hours})


def fetch_cost_by_model(hours: int = 24) -> List[Dict[str, Any]]:
    """Fetch cost by model."""
    return _get("/analytics/cost-by-model", {"hours": hours})


def fetch_anomalies(hours: int = 168, contamination: float = 0.05) -> Dict[str, Any]:
    """Fetch anomaly detection results."""
    return _get("/analytics/anomalies", {"hours": hours, "contamination": contamination})


def load_sample_data() -> Dict[str, Any]:
    """Load existing telemetry from data/ or output/ into database."""
    url = f"{API_BASE_URL}/ingest/load"
    resp = requests.post(url, params={"clear_existing": True}, timeout=120)
    resp.raise_for_status()
    return resp.json()


def generate_and_load_sample_data(
    num_users: int = 30, num_sessions: int = 500, days: int = 30
) -> Dict[str, Any]:
    """Generate fake data and load into database in one call."""
    url = f"{API_BASE_URL}/ingest/generate-and-load"
    resp = requests.post(
        url,
        params={"num_users": num_users, "num_sessions": num_sessions, "days": days},
        timeout=300,
    )
    resp.raise_for_status()
    return resp.json()
