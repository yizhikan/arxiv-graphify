"""Command-line interface for arxiv-graphify."""
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import click

from .config import Config, load_config
from .qwen_client import QwenClient
from .arxiv_client import ArxivClient
from .metadata import ArxivMetadata, initialize_metadata, save_metadata, update_metadata_timestamp, load_metadata
from .downloader import download_papers


@click.group()
@click.option(
    "--config", "-c",
    type=click.Path(exists=True),
    help="Path to config file",
)
@click.pass_context
def cli(ctx, config: Optional[str]):
    """arXiv Graphify - Build knowledge graphs from arXiv papers."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = load_config(config)


@cli.command()
@click.option(
    "--keyword", "-k",
    required=True,
    help="Domain keyword to initialize (e.g., 'graph neural network')",
)
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory for papers and metadata",
)
@click.option(
    "--max-papers", "-m",
    default=200,
    help="Maximum number of papers to fetch per keyword (default: 200)",
)
@click.option(
    "--page-size",
    default=100,
    help="Results per page for pagination (max 100, default: 100)",
)
@click.pass_context
def init(ctx, keyword: str, output_dir: str, max_papers: int, page_size: int):
    """Initialize a new arXiv knowledge graph project.

    Uses Semantic Scholar API for better availability in China.
    """
    config: Config = ctx.obj["config"]

    if not config.qwen_api_key:
        click.echo("Error: QWEN_API_KEY environment variable not set.")
        click.echo("Please set it with: export QWEN_API_KEY=your-key")
        sys.exit(1)

    output_path = Path(output_dir)
    papers_dir = output_path / config.papers_dir
    meta_path = output_path / config.meta_file

    # Check if already initialized
    if meta_path.exists():
        click.echo(f"Warning: {meta_path} already exists.")
        if not click.confirm("Overwrite?"):
            sys.exit(0)

    # Step 1: Expand keywords using Qwen API
    click.echo(f"Expanding keywords for domain: {keyword}")
    qwen_client = QwenClient(api_key=config.qwen_api_key)
    expanded = qwen_client.expand_keywords(keyword)

    if not expanded:
        click.echo("Error: Failed to expand keywords.")
        sys.exit(1)

    click.echo("\nSuggested arXiv categories:")
    for i, item in enumerate(expanded, 1):
        click.echo(f"  {i}. {item['keyword']} - {item['description']}")

    if not click.confirm("\nConfirm these categories?"):
        sys.exit(0)

    arxiv_keywords = [item["keyword"] for item in expanded]

    # Step 2: Ask for time range
    click.echo("\nSelect time range:")
    click.echo("  1. Last 1 year")
    click.echo("  2. Last 3 years")
    click.echo("  3. Last 5 years")
    click.echo("  4. Custom range")

    choice = click.prompt("Choice", type=click.Choice(["1", "2", "3", "4"]), default="2")

    end_date = datetime.utcnow().strftime("%Y-%m-%d")

    if choice == "1":
        start_date = (datetime.utcnow() - timedelta(days=365)).strftime("%Y-%m-%d")
    elif choice == "2":
        start_date = (datetime.utcnow() - timedelta(days=365*3)).strftime("%Y-%m-%d")
    elif choice == "3":
        start_date = (datetime.utcnow() - timedelta(days=365*5)).strftime("%Y-%m-%d")
    else:
        start_date = click.prompt("Start date (YYYY-MM-DD)")
        end_date = click.prompt("End date (YYYY-MM-DD)", default=end_date)

    click.echo(f"\nFetching papers from Semantic Scholar (arXiv mirror)...")
    click.echo(f"  Categories: {', '.join(arxiv_keywords)}")
    click.echo(f"  Time range: {start_date} to {end_date}")

    # Step 3: Search and download papers
    # Use OpenAlex backend for better China access
    arxiv_client = ArxivClient(backend="openalex")
    papers = arxiv_client.search_by_keywords(
        keywords=arxiv_keywords,
        start_date=start_date,
        end_date=end_date,
        max_results_per_keyword=max_papers,
        page_size=min(page_size, 100),
    )

    click.echo(f"Found {len(papers)} papers.")

    if not papers:
        click.echo("No papers found. Exiting.")
        sys.exit(0)

    # Step 4: Save papers
    click.echo(f"Saving papers to {papers_dir}...")
    papers_dir.mkdir(parents=True, exist_ok=True)
    download_papers(papers, str(papers_dir))

    # Step 5: Save metadata
    meta = initialize_metadata(
        domain_keyword=keyword,
        arxiv_keywords=arxiv_keywords,
        start_date=start_date,
        end_date=end_date,
    )
    meta.paper_count = len(papers)
    save_metadata(meta, str(meta_path))

    click.echo(f"\nInitialization complete!")
    click.echo(f"  Papers: {len(papers)}")
    click.echo(f"  Categories: {', '.join(arxiv_keywords)}")
    click.echo(f"  Time range: {start_date} to {end_date}")
    click.echo("\nNext step: Run 'python -m arxiv_graphify build' to build the graph.")


@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory for papers and metadata",
)
@click.option(
    "--max-papers", "-m",
    default=100,
    help="Maximum number of papers to fetch per keyword (default: 100)",
)
@click.pass_context
def update(ctx, output_dir: str, max_papers: int):
    """Incrementally update an existing arXiv knowledge graph."""
    config: Config = ctx.obj["config"]

    output_path = Path(output_dir)
    papers_dir = output_path / config.papers_dir
    meta_path = output_path / config.meta_file

    # Load existing metadata
    meta = load_metadata(str(meta_path))
    if meta is None:
        click.echo(f"Error: No metadata found at {meta_path}")
        click.echo("Run 'python -m arxiv_graphify init' first to initialize.")
        sys.exit(1)

    click.echo(f"Updating from {meta.last_updated} to now...")

    # Search for new papers since last update
    arxiv_client = ArxivClient()
    papers = arxiv_client.search_by_keywords(
        keywords=meta.arxiv_keywords,
        start_date=meta.end_date,  # Continue from last end date
        end_date=None,  # Up to now
        max_results_per_keyword=max_papers,
    )

    click.echo(f"Found {len(papers)} new papers.")

    if not papers:
        click.echo("No new papers found.")
        sys.exit(0)

    # Save new papers
    papers_dir.mkdir(parents=True, exist_ok=True)
    download_papers(papers, str(papers_dir))

    # Update metadata
    meta.end_date = datetime.utcnow().strftime("%Y-%m-%d")
    meta.paper_count += len(papers)
    save_metadata(meta, str(meta_path))

    click.echo(f"\nUpdate complete!")
    click.echo(f"  New papers: {len(papers)}")
    click.echo(f"  Total papers: {meta.paper_count}")
    click.echo(f"  Updated range: {meta.start_date} to {meta.end_date}")


@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory",
)
@click.pass_context
def status(ctx, output_dir: str):
    """Show project status and metadata."""
    config: Config = ctx.obj["config"]

    output_path = Path(output_dir)
    meta_path = output_path / config.meta_file

    meta = load_metadata(str(meta_path))
    if meta is None:
        click.echo("No arxiv-graphify project found.")
        click.echo("Run 'python -m arxiv_graphify init' to initialize.")
        sys.exit(0)

    click.echo(f"Domain: {meta.domain_keyword}")
    click.echo(f"Keywords: {', '.join(meta.arxiv_keywords)}")
    click.echo(f"Papers: {meta.paper_count}")
    click.echo(f"Time range: {meta.start_date} to {meta.end_date}")
    click.echo(f"Initialized: {meta.initialized_at}")
    click.echo(f"Last updated: {meta.last_updated}")


@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory",
)
@click.pass_context
def build(ctx, output_dir: str):
    """Build graphify knowledge graph from collected papers."""
    import subprocess

    output_path = Path(output_dir)

    click.echo("Running graphify update...")
    result = subprocess.run(
        ["graphify", "update", str(output_path)],
        capture_output=True,
        text=True,
    )

    if result.returncode == 0:
        click.echo("Graph build complete!")
        click.echo(f"Output: {output_path}/graphify-out/")
    else:
        click.echo(f"Error: {result.stderr}")
        sys.exit(1)
