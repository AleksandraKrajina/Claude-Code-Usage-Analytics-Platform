# LLM Usage Log

## Overview

This project was developed using an AI-assisted workflow.  
LLM tools were used to accelerate development, generate code scaffolding, assist with debugging, and explore data analysis approaches.

The final architecture, implementation decisions, and validation were performed manually.

---

## Tools Used

- Cursor (primary AI coding assistant)
- ChatGPT / GPT models

---
## Cursor Usage

Cursor was used as the primary development environment with inline AI assistance for:

- code refactoring
- quick debugging suggestions
- generating API helpers
- improving Streamlit components

## Use Cases

### 1. Project Architecture

LLMs were used to brainstorm the initial architecture for the analytics platform.

Example prompt:

"Design a simple analytics platform architecture for telemetry data with FastAPI backend and Streamlit dashboard."

Outcome:

- FastAPI for analytics endpoints
- SQLite/PostgreSQL for telemetry storage
- Streamlit for visualization dashboard

---

### 2. API Development

LLMs helped generate initial FastAPI endpoint templates.

Example prompt:

"Create a FastAPI endpoint that returns token usage grouped by model from telemetry logs."

Outcome:

- Generated base API structure
- Adjusted SQL queries manually

---

### 3. Debugging

LLMs assisted in debugging runtime errors.

Example prompt:

"Why does Streamlit st.metric() throw 'unexpected keyword argument key'?"

Outcome:

- Identified Streamlit version mismatch
- Adjusted metric implementation

---

### 4. Data Analysis

LLMs were used to explore telemetry patterns and anomaly detection ideas.

Example prompt:

"Suggest a simple anomaly detection approach for token usage spikes."

Outcome:

- Implemented IsolationForest based anomaly detection
- Added configurable contamination parameter

---

### 5. UI Improvements

LLMs suggested improvements for the Streamlit dashboard layout.

Example prompt:

"How to center buttons and improve layout in Streamlit dashboard?"

Outcome:

- Updated layout using Streamlit columns
- Improved usability of data ingestion controls

---

## Approximate AI Usage

Estimated prompts during development:

~30–50 prompts

AI tools were primarily used for:

- code scaffolding
- debugging
- architecture brainstorming
- UI layout suggestions

---

## Development Approach

AI tools were used as assistants rather than autonomous developers.

The workflow typically followed this pattern:

1. Define the problem manually
2. Use AI to generate possible implementation
3. Review and modify generated code
4. Integrate and test manually

---

## Conclusion

LLMs significantly accelerated development by reducing boilerplate coding and assisting with debugging and design exploration, while final implementation and validation remained developer-driven.