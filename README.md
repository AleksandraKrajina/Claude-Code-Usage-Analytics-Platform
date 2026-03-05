# Claude Code Usage Analytics Platform

A full-stack analytics platform for processing Claude Code telemetry, computing metrics, detecting anomalies, and visualizing usage on an interactive dashboard.

## Data Format

The platform expects telemetry data from `claude_code_telemetry/generate_fake_data.py`:

- **telemetry_logs.jsonl**: Each line is a JSON object with `logEvents` (CloudWatch-style batches). Each `logEvent` has a `message` field containing a JSON string with:
  - `body`: Event type (e.g. `claude_code.api_request`, `claude_code.tool_decision`)
  - `attributes`: `event.timestamp`, `user.id`, `session.id`, `input_tokens`, `output_tokens`, `cache_read_tokens`, `cache_creation_tokens`, `model`, `cost_usd`, etc.
  - `resource`: `user.practice` (role/practice)
- **employees.csv**: `email,full_name,practice,level,location`

---

## Prerequisites

- **Python 3.11+**
- No database setup required (SQLite is used by default)

---

## Quick Start (3 Steps)

### 1. Install Dependencies

```bash
cd "Claude Code Usage Analytics Platform"
pip install -r requirements.txt
```

### 2. Generate Sample Data

```bash
python claude_code_telemetry/generate_fake_data.py --num-users 30 --num-sessions 500 --days 30 --output-dir data
```

This creates:
- `data/telemetry_logs.jsonl` (telemetry events)
- `data/employees.csv` (employee directory)

### 3. Start Backend and Dashboard

**Terminal 1 – Backend:**
```bash
python -m uvicorn backend.main:app --reload --port 8000
```

**Terminal 2 – Dashboard:**
```bash
python -m streamlit run dashboard/app.py
```

Open **http://localhost:8501** in your browser.

### 4. Load Data into the Dashboard

1. Click **Load Existing** at the top of the dashboard.
2. Data is loaded from `data/` or `output/`.
3. Charts and metrics will populate with data.

---

## Step-by-Step Setup (Detailed)

### 1. Clone or Navigate to Project

```bash
cd "Claude Code Usage Analytics Platform"
```

### 2. Create Virtual Environment (Recommended)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
# or: source venv/bin/activate  # macOS/Linux
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Generate Telemetry Data

```bash
python claude_code_telemetry/generate_fake_data.py --num-users 30 --num-sessions 500 --days 30 --output-dir data
```

**Options:**
| Flag | Default | Description |
|------|---------|-------------|
| `--num-users` | 30 | Number of fake users |
| `--num-sessions` | 500 | Total coding sessions |
| `--days` | 30 | Time span in days |
| `--output-dir` | output | Output directory (use `data` for this project) |

### 5. Start the Backend

```bash
python -m uvicorn backend.main:app --reload --port 8000
```

- API docs: http://localhost:8000/docs
- Database: SQLite at `data/claude_analytics.db` (created automatically)

### 6. Start the Dashboard

```bash
python -m streamlit run dashboard/app.py
```

- Dashboard: http://localhost:8501

### 7. Load Data

1. Open the dashboard.
2. Click **Load Existing** above the charts.
3. Wait for the success message.
4. Adjust the **Time range** slider in the sidebar (e.g. 720 hours = 30 days) to include your data.

---

## Troubleshooting

### 500 Error on "Load Existing"

**Cause:** Database or path issues.

**Fix:**
1. Ensure the backend is running (`python -m uvicorn backend.main:app --reload --port 8000`).
2. Ensure `data/telemetry_logs.jsonl` exists (run `generate_fake_data.py` first).
3. Start the backend before the dashboard so tables are created.

### No Data in Charts

**Cause:** Data not loaded or time range too narrow.

**Fix:**
1. Click **Load Existing** to ingest from `data/` or `output/`.
2. Set **Time range** in the sidebar to **720** or **8760** hours (data is from Jan–Feb 2026, so a wide range is needed).

### Backend Won't Start

**Cause:** Port in use or wrong working directory.

**Fix:**
1. Run from the project root: `cd "Claude Code Usage Analytics Platform"`.
2. Use a different port: `python -m uvicorn backend.main:app --reload --port 8001`.

### Database Location

- **SQLite (default):** `data/claude_analytics.db`
- **PostgreSQL:** Set `DATABASE_URL` before starting:

```bash
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/claude_analytics
python -m uvicorn backend.main:app --reload --port 8000
```

---
See LLM_USAGE_LOG.md for details on how AI tools were used during development.
----

## Project Structure

```
Claude Code Usage Analytics Platform/
├── backend/
│   ├── config.py           # Settings (SQLite default)
│   ├── database.py         # SQLAlchemy + SQLite/PostgreSQL
│   ├── main.py             # FastAPI app
│   ├── models.py           # TelemetryEvent, Employee
│   ├── routers/
│   │   ├── analytics.py    # Analytics endpoints
│   │   └── ingestion.py    # Load / generate / stream
│   └── services/
│       ├── analytics.py    # Metrics, anomaly detection
│       └── ingestion.py    # Parse JSONL, load CSV
├── claude_code_telemetry/
│   └── generate_fake_data.py  # Synthetic data generator
├── dashboard/
│   ├── app.py              # Streamlit dashboard
│   ├── api_client.py       # Backend API client
│   └── components/         # UI components
├── data/                   # telemetry_logs.jsonl, employees.csv, claude_analytics.db
├── scripts/
│   ├── generate_and_ingest.py
│   └── ingest_existing.py
├── .streamlit/
│   └── config.toml         # Streamlit config
├── docker-compose.yml     # PostgreSQL (optional)
├── requirements.txt
└── README.md
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/v1/analytics/overview` | Overview metrics |
| `GET /api/v1/analytics/token-by-role` | Token consumption by role |
| `GET /api/v1/analytics/hourly-usage` | Hourly token aggregation |
| `GET /api/v1/analytics/hourly-usage-by-model` | Hourly usage by model |
| `GET /api/v1/analytics/event-type-distribution` | Event type counts |
| `GET /api/v1/analytics/tokens-by-type` | Token breakdown by type |
| `GET /api/v1/analytics/tokens-by-model` | Token consumption by model |
| `GET /api/v1/analytics/cost-by-model` | Cost by model |
| `GET /api/v1/analytics/anomalies` | Anomaly detection results |
| `POST /api/v1/ingest/load` | Ingest from data/ or output/ |
| `POST /api/v1/ingest/generate-and-load` | Generate and ingest in one call |

---

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./data/claude_analytics.db` | Database URL |
| `ANALYTICS_API_URL` | `http://localhost:8000/api/v1` | Backend URL (for dashboard) |

---

## Optional: PostgreSQL

For PostgreSQL instead of SQLite:

```bash
docker-compose up -d postgres
set DATABASE_URL=postgresql://postgres:postgres@localhost:5432/claude_analytics
python -m uvicorn backend.main:app --reload --port 8000
```

---

## Bonus Features

- **Anomaly detection:** IsolationForest on hourly usage; anomalies on charts
- **Real-time streaming:** `POST /api/v1/ingest/stream` for live event batches
- **Advanced stats:** Cache efficiency, productivity ratio, peak leverage, hourly aggregations
