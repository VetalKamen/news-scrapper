from __future__ import annotations

import logging
import typer

from pathlib import Path
from typing import Optional

from news_scraper.config import settings
from news_scraper.logging_utils import setup_logging
from news_scraper.scrape import scrape_urls_to_jsonl
from news_scraper.analyze import analyze_raw_to_ai_jsonl
from news_scraper.index import index_ai_jsonl_to_chroma
from news_scraper.search import semantic_search
from news_scraper.ingest import ingest_url


app = typer.Typer(add_completion=False, help="News Scraper prototype CLI")


@app.command()
def health() -> None:
    """Health check to verify config + logging works."""
    setup_logging(settings.log_level)
    log = logging.getLogger("news_scraper.health")

    log.info("Health check OK.")
    log.info("Model: %s", settings.openai_model)
    log.info("Embedding model: %s", settings.openai_embedding_model)
    log.info("Chroma dir: %s", settings.chroma_dir)
    log.info("Raw data dir: %s", settings.data_raw_dir)
    log.info("Processed data dir: %s", settings.data_processed_dir)

    typer.echo("OK")


@app.command()
def version() -> None:
    """Print version and exit."""
    typer.echo("news-scraper 0.1.0")


@app.command()
def scrape(
        urls_file: Path = typer.Option(..., "--urls-file", help="Path to file with URLs (one per line)"),
        out_file: Optional[Path] = typer.Option(
            None,
            "--out",
            help="Output JSONL file (default: data/raw/articles_raw.jsonl)",
        ),
        limit: Optional[int] = typer.Option(None, help="Limit number of URLs"),
        sleep_s: float = typer.Option(0.0, help="Sleep seconds between requests"),
        min_chars: int = typer.Option(500, help="Minimum extracted text length"),
) -> None:
    """
    Scrape news articles and write raw content to JSONL.
    """
    setup_logging(settings.log_level)

    if out_file is None:
        out_file = settings.data_raw_dir / "articles_raw.jsonl"

    summary = scrape_urls_to_jsonl(
        urls_file=urls_file,
        out_file=out_file,
        limit=limit,
        sleep_s=sleep_s,
        min_chars=min_chars,
    )

    typer.echo(summary)


@app.command()
def analyze(
    raw_file: Path = typer.Option(
        None,
        "--raw",
        help="Input raw JSONL file (default: data/raw/articles_raw.jsonl)",
    ),
    out_file: Path = typer.Option(
        None,
        "--out",
        help="Output AI JSONL file (default: data/processed/articles_ai.jsonl)",
    ),
    limit: Optional[int] = typer.Option(None, help="Limit number of eligible articles to analyze"),
) -> None:
    """
    Generate LLM summaries and topics for scraped articles.
    """
    setup_logging(settings.log_level)

    if raw_file is None:
        raw_file = settings.data_raw_dir / "articles_raw.jsonl"
    if out_file is None:
        out_file = settings.data_processed_dir / "articles_ai.jsonl"

    summary = analyze_raw_to_ai_jsonl(raw_file=raw_file, out_file=out_file, limit=limit)
    typer.echo(summary)


@app.command()
def index(
    ai_file: Path = typer.Option(
        None,
        "--ai",
        help="Input AI JSONL file (default: data/processed/articles_ai.jsonl)",
    ),
    limit: Optional[int] = typer.Option(None, help="Limit number of records to index"),
) -> None:
    """
    Index AI-enriched articles into Chroma vector database.
    """
    setup_logging(settings.log_level)

    if ai_file is None:
        ai_file = settings.data_processed_dir / "articles_ai.jsonl"

    summary = index_ai_jsonl_to_chroma(ai_file=ai_file, limit=limit)
    typer.echo(summary)


@app.command()
def search(
    query: str = typer.Argument(..., help="Search query (natural language)"),
    top_k: int = typer.Option(5, help="Number of results to return"),
) -> None:
    """
    Semantic search over indexed news articles.
    """
    setup_logging(settings.log_level)

    results = semantic_search(query=query, top_k=top_k)

    if not results:
        typer.echo("No results found.")
        return

    for r in results:
        typer.echo("=" * 80)
        typer.echo(f"Rank: {r['rank']} | Score: {r['score']:.4f}")
        meta = r["metadata"]
        typer.echo(f"Title: {meta.get('title')}")
        typer.echo(f"URL:   {meta.get('url')}")
        typer.echo(f"Topics:{meta.get('topics')}")
        typer.echo()
        typer.echo(r["document"][:500] + ("..." if len(r["document"]) > 500 else ""))


@app.command()
def ingest(
    url: str = typer.Argument(..., help="Direct article URL to ingest (scrape -> analyze -> index)"),
    min_chars: int = typer.Option(300, "--min-chars", help="Minimum extracted characters to accept an article"),
    sleep_s: float = typer.Option(0.0, "--sleep-s", help="Sleep between requests (seconds)"),
) -> None:
    """
    Ingest a single URL end-to-end: scrape -> analyze -> index.
    """
    res = ingest_url(url, min_chars=min_chars, scrape_sleep_s=sleep_s)

    if res.get("skipped"):
        typer.secho("SKIPPED", fg=typer.colors.YELLOW)
        typer.echo(f"URL: {res.get('url')}")
        typer.echo(f"Reason: {res.get('reason')}")
        raise typer.Exit(code=0)

    if res["status"] != "ok":
        typer.secho(f"FAILED stage={res['stage']} url={res['url']}", fg=typer.colors.RED)
        typer.echo(str(res.get("detail", "")))
        raise typer.Exit(code=1)

    typer.secho("OK", fg=typer.colors.GREEN)
    typer.echo(f"URL: {res['url']}")
    typer.echo(f"Scrape: {res['scrape']}")
    typer.echo(f"Analyze: {res['analyze']}")
    typer.echo(f"Index: {res['index']}")