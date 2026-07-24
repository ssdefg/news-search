# news-search

An automated end-to-end news analytics web application built with Streamlit, Google Gemini API, and Supabase (PostgreSQL). It leverages real-time Google Search grounding to extract, verify, summarize, and archive news articles with an anti-hallucination URL verification pipeline.

---

## Key Features

* Real-Time Grounded News Search: Integrates `gemini-2.5-flash` with active `google_search` tools to query and summarize the top 5 latest articles for any keyword.
* Anti-Hallucination Pipeline: Programmatically parses `grounding_metadata` to map LLM outputs against actual Google Search reference chunks, replacing generated/hallucinated URLs with verified web URIs.
* Automated Database Archiving: Automatically stores structured records in **Supabase** while gracefully handling PostgreSQL unique key constraint violations (`23505`) for duplicate prevention.
* Analytics Dashboard: Visualizes cumulative search counts per keyword (Bar Chart) and daily collection trends (Line Chart) using Pandas.
* Data Filtering & CSV Export: Filter saved history by keyword/title and export the customized dataset to CSV.

---

## 🛠️ Tech Stack & Architecture

| Layer | Technology | Role |
| :--- | :--- | :--- |
| Frontend UI | `Streamlit` | Interactive 3-tab web layout (Search, History, Analytics) |
| AI & Grounding Engine | `Google Gemini API` (`gemini-2.5-flash`) | Web search grounding, 3-line summarization, JSON parsing |
| Database | `Supabase` (`PostgreSQL`) | Persistent data storage with `UNIQUE` constraint enforcement on URLs |
| Data Processing | `Pandas`, `re` | Metadata extraction, URL matching, CSV export, trend aggregation |

---

## 📂 Repository Structure

```text
.
├── app.py              # Main Streamlit application source code
├── requirements.txt    # Python library dependencies
├── sql_schema.sql      # Database schema creation query
└── README.md           # Project documentation
