"""Dashboard configuration."""

import os

# Backend API URL - change if running on different host/port
API_BASE_URL = os.getenv("ANALYTICS_API_URL", "http://localhost:8000/api/v1")
