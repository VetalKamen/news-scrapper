# News Scraper with GenAI Summarization & Semantic Search

## Overview

This project is a prototype news-processing pipeline that demonstrates:

1. Scraping full news articles from provided URLs
2. Using Generative AI (LLM) to:
   - Generate concise summaries
   - Identify key topics
3. Storing AI-enriched articles in a vector database
4. Performing semantic search over the articles using natural-language queries

The focus of the project is **effective integration of GenAI tools**, clean architecture, and robustness, rather than building NLP logic from scratch.

---
## Architecture (High-Level)
```text
URLs
↓
Scraper (httpx + trafilatura)
↓
Raw Articles (JSONL)
↓
LLM Analysis (summary + topics)
↓
AI Articles (JSONL)
↓
Embeddings (OpenAI)
↓
Vector DB (Chroma)
↓
Semantic Search (CLI)
```
---

## Tech Stack

- **Python** 3.11+
- **httpx** – HTTP fetching
- **trafilatura + BeautifulSoup** – article extraction
- **OpenAI API** – summaries, topics, embeddings
- **ChromaDB** – vector storage
- **Typer** – CLI interface
- **Pydantic** – data validation

---

## Setup Instructions

### 1. Create virtual environment
`python -m venv .venv
source .venv/bin/activate`
### 2. Install dependencies
`pip install -r requirements.txt`
### 3. Configure environment variables
`cp .env.example .env`

Edit .env and set:

`OPENAI_API_KEY=<your_openai_api_key_here>`
### 4. Verify setup
`PYTHONPATH=src python -m news_scraper health`

Expected output:

```text  
Logging initialized
Config values printed
OK
```

## Usage
The application is designed as a step-by-step pipeline.
Each step produces artifacts that are consumed by the next one.

⚠️ Important
Use direct article URLs, not homepages or live feeds.
Some publishers (e.g. Reuters) block programmatic access and will return HTTP 401.
This project handles such failures gracefully but they will not produce usable content.

### Step 1 — Scrape Articles
**Purpose**
* Fetch HTML pages
* Extract headline and main article text
* Store results as raw, auditable JSONL records

Command:

```text
 PYTHONPATH=src python -m news_scraper scrape \
  --urls-file urls.sample.txt \
  --min-chars 300
 ```

Input:

`urls.sample.txt — one article URL per line`

Output:

`data/raw/articles_raw.jsonl`

Each URL produces one JSON record, even if scraping fails.

Example (success):

```text
{
  "url": "https://www.bbc.com/news/articles/...",
  "title": "Article title",
  "text": "Full article text...",
  "status": "ok",
  "chars": 1845
}
```

### Step 2 — Analyze with GenAI (Summaries & Topics)
**Purpose**
* Generate concise summaries
* Identify main topics
* Enrich scraped data using an LLM

Command:

```text
PYTHONPATH=src python -m news_scraper analyze
```

Input:

`data/raw/articles_raw.jsonl`

Only records with status == "ok" are analyzed.

Output:

`data/processed/articles_ai.jsonl`

Example:
```text
{
  "url": "https://www.bbc.com/news/articles/...",
  "title": "Article title",
  "summary": "Concise 3–5 sentence summary...",
  "topics": ["corruption", "politics", "investigation"],
  "llm_model": "gpt-4o-mini",
  "status": "ok"
}
```

### Step 3 — Index Articles into Vector Database
**Purpose**
* Convert AI-enriched articles into embeddings
* Store them in a persistent vector database
* Enable semantic (meaning-based) search

Command:

```text
PYTHONPATH=src python -m news_scraper index
```

Input:

`data/processed/articles_ai.jsonl`

Output:

`data/vectorstore/ (persistent ChromaDB directory)`

Notes:
* Indexing is idempotent
* Re-running will not duplicate documents
* Only successfully analyzed articles are indexed

### Step 4 — Semantic Search
**Purpose**
* Search articles using natural language
* Retrieve results by semantic similarity (not keywords)

Command:

```text
PYTHONPATH=src python -m news_scraper search "corruption investigation real estate"
```

Example output:

```text
Rank: 1 | Score: 0.18
Title: UK police investigate property deal linked to royal family
URL: https://www.bbc.com/news/articles/...
Topics: corruption, real estate, investigation
```

You can use synonyms and paraphrases:

`PYTHONPATH=src python -m news_scraper search "financial crime and bribery"`

### Extra Step — Single Article Ingestion
**Purpose**
* Ingest a single article URL into the system end-to-end (without manually editing URL files):
* Scrape the article (raw JSONL)
* Analyze it with GenAI (summary + topics → AI JSONL)
* Index it into the vector DB (Chroma)

Command:

```text
PYTHONPATH=src python -m news_scraper ingest "<article_url>" --min-chars 300
```

_What it does / Outputs_: 

Appends (if not already present) to:

`data/raw/articles_raw.jsonl`
   
`data/processed/articles_ai.jsonl`

_Indexes into:_

`data/vectorstore/ (Chroma persistent directory)`

**Notes:**
**No duplicates policy:**
* If the URL already exists in AI JSONL (normalized), ingest skips GenAI + indexing (already ingested).
* If the URL already exists in Chroma, indexing is skipped.
* Raw scraping is also idempotent (already-scraped URLs are skipped).

Example output:

```text
Ingest finished:
status=ok
url=https://www.bbc.com/news/articles/c8d09qd6zn2o
scrape: { total: 1, ok: 1, failed: 0, skipped_existing: 0 }
analyze: { processed: 1, failed: 0 }
index: { added: 1, skipped_existing: 0 }
```

Verify it was added (search after ingest):
```text
PYTHONPATH=src python -m news_scraper search "keyword1 keyword2 keyword3"
```

### CLI Command Summary
| Command   | Description                                      |
| --------- |--------------------------------------------------|
| `health`  | Verify configuration and logging                 |
| `scrape`  | Fetch and extract raw articles                   |
| `analyze` | Generate summaries and topics using GenAI        |
| `index`   | Create embeddings and store them in ChromaDB     |
| `search`  | Perform semantic search                          |
| `ingest`  | Runs pipeline on an article provided by the user |

All commands are executed as:

`PYTHONPATH=src python -m news_scraper <command>`

### Project Structure
```text
src/news_scraper/
├── cli.py                 # CLI entry point
├── config.py              # Environment-based configuration
├── scrape.py              # Scraping pipeline
├── analyze.py             # GenAI analysis pipeline
├── index.py               # Vector indexing
├── search.py              # Semantic search
├── llm_client.py          # OpenAI LLM wrapper
├── embeddings_client.py   # OpenAI embeddings wrapper
├── vectorstore_chroma.py  # ChromaDB integration
├── models.py              # Pydantic data models
├── prompts.py             # LLM prompt templates
├── ingest.py              # Single article handler
```