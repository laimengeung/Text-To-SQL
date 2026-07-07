# 🤖 Text-to-SQL Agentic AI

> Query your data in plain English. No SQL knowledge required.

A multi-agent AI system that converts natural language questions into SQL queries, executes them against your DuckDB database, and returns human-readable answers — with optional interactive visualizations.

Built with **Python**, **Agno**, **DuckDB**, and **Gemini**.

---

## ✨ Demo

> 📸 *Screenshot / GIF coming soon*

<!-- Replace with an actual screenshot or GIF of the Streamlit UI -->
<!-- ![Demo](docs/demo.gif) -->

---

## 🧠 Why This is Agentic AI

This is not a simple "prompt → SQL" wrapper. The system is genuinely agentic:

- **Autonomous schema introspection** — agents explore your database without being told the structure
- **Retry loops** — if SQL fails, the Validator Agent diagnoses the error and rewrites the query (up to 3 attempts)
- **Multi-step reasoning** — Schema → SQL Writer → Validator → Response → Visualization, all coordinated by a Dedicated Orchestrator
- **Persistent memory** — conversation history stored in Supabase, enabling follow-up questions across sessions
- **Intent classification** — routes `sql_query`, `sql_only`, and `general` questions to the right agents automatically

---

## 🏗️ Agent Architecture

```
User Question
    ↓
Orchestrator (intent classification)
    ↓
Schema Agent → SQL Writer Agent → Validator Agent (retry loop)
    ↓
Response Agent
    ↓ (if chart requested)
Visualization Agent
    ↓
User
```

| Agent | Role |
|---|---|
| **Orchestrator** | Routes the pipeline, manages memory, classifies intent |
| **Schema Agent** | Introspects DuckDB tables, columns, and types |
| **SQL Writer Agent** | Writes DuckDB-compatible SQL from the user's question |
| **Validator Agent** | Executes SQL, retries with error feedback on failure |
| **Response Agent** | Formats raw results into a natural language answer |
| **Visualization Agent** | Generates interactive Plotly charts on request |

---

## 🛠️ Tech Stack

| Tool | Purpose |
|---|---|
| [Python](https://python.org) | Core language |
| [Agno](https://docs.agno.com) | Multi-agent framework |
| [Gemini](https://ai.google.dev) | LLM (free tier) |
| [DuckDB](https://duckdb.org) | Analytical SQL engine |
| [Supabase](https://supabase.com) | Persistent session memory |
| [Plotly](https://plotly.com/python) | Interactive visualizations |
| [Streamlit](https://streamlit.io) | Web UI |
| [uv](https://docs.astral.sh/uv) | Package manager |
| [pytest](https://pytest.org) | Testing |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/getting-started/installation/) installed
- A [Google AI Studio](https://aistudio.google.com) API key (free)
- A [Supabase](https://supabase.com) project (free tier)

### 1. Clone the repo

```bash
git clone https://github.com/your-username/text-to-sql-agent.git
cd text-to-sql-agent
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Configure environment

Copy the example env file and fill in your values:

```bash
cp .env.example .env
```

Edit `.env`:

```env
GOOGLE_API_KEY=your-google-api-key
GEMINI_DEFAULT_MODEL=gemini-2.0-flash
SUPABASE_CONNECTION_STRING=postgresql://postgres.xxx:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
DUCKDB_FILE_PATH=data/data.duckdb
VISUALIZATION_MODE=structured
MAX_SQL_RETRIES=3
DEBUG_MODE=false
LOG_LEVEL=INFO
```

### 4. Run

**CLI:**
```bash
uv run python main.py
```

**Streamlit UI:**
```bash
uv run streamlit run app.py
```

---

## 💬 Example Queries

Once running, try asking:

```
What is the total revenue by region?
Show me the top 5 products by quantity sold.
Which employees earn more than their manager?
Plot a bar chart of revenue by category.
Give me the SQL to find all orders placed in 2024.
```

The agent automatically classifies your intent and routes accordingly.

---

## 📁 Project Structure

```
text_to_sql/
├── agents/          # All agent definitions
├── tools/           # Raw tool functions (schema, DuckDB, Plotly)
├── memory/          # Supabase memory integration
├── database/        # DuckDB connection and file registry
├── visualization/   # Structured and code-gen chart implementations
├── core/            # Exceptions, config, logger
├── tests/
│   ├── unit/        # Tool-level tests (no LLM)
│   └── e2e/         # Full pipeline tests with real Gemini calls
├── fixtures/
│   ├── clean/       # Clean test datasets (sales, employees, products)
│   └── dirty/       # Edge case datasets (V2)
├── data/            # Persistent DuckDB file (gitignored)
├── app.py           # Streamlit UI
├── main.py          # CLI entry point
└── .env.example     # Environment variable template
```

---

## 🧪 Testing

**Unit tests** (fast, no LLM, no API calls):
```bash
uv run pytest tests/unit/ -v
```

**E2E tests** (real Gemini API calls — uses quota):
```bash
uv run pytest tests/e2e/ -v
```

**Single test:**
```bash
uv run pytest tests/e2e/test_pipeline.py::TestSalesPipeline::test_total_revenue_by_region -v
```

---

## ⚙️ Customize for Your Use

### Swap the LLM model

In `.env`, change:
```env
GEMINI_DEFAULT_MODEL=gemini-2.5-flash
```

Any Gemini model with tool-calling support works. Stronger models = better SQL accuracy.

### Change the visualization mode

```env
VISUALIZATION_MODE=structured   # safe, deterministic (default)
VISUALIZATION_MODE=code_gen     # flexible, agent writes raw Plotly code
```

### Adjust retry attempts

```env
MAX_SQL_RETRIES=3   # increase for harder queries, decrease for speed
```

### Use your own data

Upload any `.csv` or `.parquet` file via the Streamlit sidebar — the agent introspects the schema automatically. No configuration needed.

### Enable verbose agent logging

```env
DEBUG_MODE=true
LOG_LEVEL=DEBUG
```

This enables Agno's full agent trace — every LLM call, tool invocation, and retry is logged.

### Bring your own database

Point `DUCKDB_FILE_PATH` at an existing `.duckdb` file:
```env
DUCKDB_FILE_PATH=path/to/your/database.duckdb
```

---

## 🗺️ Roadmap

| Version | Status | Highlights |
|---|---|---|
| **V1** | ✅ Complete | 6-agent pipeline, CLI + Streamlit, Supabase memory, Plotly viz, pytest |
| **V2** | 🔄 Planned | Edge case fixtures, robustness tests, improved error messages |
| **V3** | 💡 Ideas | Multi-model strategy, LangFuse observability, query history UI |

---

## 📄 License

See [LICENSE](LICENSE) for details.