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
    "--page-size",
    default=100,
    help="Results per page for pagination (max 100, default: 100)",
)
@click.pass_context
def init(ctx, keyword: str, output_dir: str, page_size: int):
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

    # Select number of papers
    click.echo("\nSelect number of papers:")
    click.echo("  1. All papers (no limit)")
    click.echo("  2. 50 papers")
    click.echo("  3. 100 papers")
    click.echo("  4. 200 papers")
    click.echo("  5. Custom number")

    num_choice = click.prompt("Choice", type=click.Choice(["1", "2", "3", "4", "5"]), default="3")

    if num_choice == "1":
        max_papers = None
        click.echo("\nFetching all available papers...")
    elif num_choice == "2":
        max_papers = 50
    elif num_choice == "3":
        max_papers = 100
    elif num_choice == "4":
        max_papers = 200
    else:
        max_papers = click.prompt("Enter number of papers", type=int, default=100)

    click.echo(f"\nFetching papers from Semantic Scholar (arXiv mirror)...")
    click.echo(f"  Categories: {', '.join(arxiv_keywords)}")
    click.echo(f"  Time range: {start_date} to {end_date}")
    click.echo(f"  Max papers: {max_papers if max_papers else 'unlimited'}")

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
@click.pass_context
def update(ctx, output_dir: str):
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
    click.echo(f"  Current time range: {meta.start_date} to {meta.end_date}")

    # Select number of papers
    click.echo("\nSelect number of papers to fetch:")
    click.echo("  1. All papers (no limit)")
    click.echo("  2. 50 papers")
    click.echo("  3. 100 papers")
    click.echo("  4. 200 papers")
    click.echo("  5. Custom number")

    num_choice = click.prompt("Choice", type=click.Choice(["1", "2", "3", "4", "5"]), default="3")

    if num_choice == "1":
        max_papers = None
        click.echo("\nFetching all available papers...")
    elif num_choice == "2":
        max_papers = 50
    elif num_choice == "3":
        max_papers = 100
    elif num_choice == "4":
        max_papers = 200
    else:
        max_papers = click.prompt("Enter number of papers", type=int, default=100)

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


@cli.command()
@click.option(
    "--output-dir", "-o",
    default=".",
    type=click.Path(exists=True),
    help="Output directory",
)
@click.pass_context
def visualize(ctx, output_dir: str):
    """Generate interactive HTML visualization of the knowledge graph.

    Generates a standalone HTML file with embedded vis-network library,
    works offline without any external CDN dependencies.
    """
    output_path = Path(output_dir)
    graphify_out = output_path / "graphify-out"

    if not graphify_out.exists():
        click.echo("Error: No graphify-out/ directory found.")
        click.echo("Run 'python -m arxiv_graphify build' first to build the graph.")
        sys.exit(1)

    graph_json = graphify_out / "graph.json"
    if not graph_json.exists():
        click.echo("Error: No graph.json found in graphify-out/")
        click.echo("Run 'python -m arxiv_graphify build' first to build the graph.")
        sys.exit(1)

    from graphify.build import build_from_json
    from graphify.cluster import cluster
    import json

    click.echo("Loading graph...")
    graph_data = json.loads(graph_json.read_text())
    G = build_from_json(graph_data)

    # Load or re-cluster communities
    analysis_path = graphify_out / ".graphify_analysis.json"
    labels_path = graphify_out / ".graphify_labels.json"

    if analysis_path.exists():
        click.echo("Loading existing community structure...")
        analysis = json.loads(analysis_path.read_text())
        communities = {int(k): v for k, v in analysis["communities"].items()}
        labels = {}
        if labels_path.exists():
            labels_raw = json.loads(labels_path.read_text())
            labels = {int(k): v for k, v in labels_raw.items()}
    else:
        click.echo("Clustering communities...")
        communities = cluster(G)
        labels = {cid: f"Community {cid}" for cid in communities}

    click.echo("Generating HTML visualization (standalone, no CDN required)...")
    html_path = graphify_out / "graph.html"
    _generate_standalone_html(G, communities, str(html_path), community_labels=labels or None)

    click.echo(f"\nVisualization complete!")
    click.echo(f"  Open in browser: {html_path.absolute()}")
    click.echo("\nTip: The HTML file is fully self-contained - no internet connection needed.")


def _generate_standalone_html(
    G,
    communities: dict[int, list[str]],
    output_path: str,
    community_labels: dict[int, str] | None = None,
) -> None:
    """Generate standalone HTML with embedded vis-network library.

    Uses a CDN-independent approach by embedding the vis-network library directly.
    """
    import html as _html
    import json as _json
    from pathlib import Path

    # vis-network.min.js embedded (trimmed for brevity - full version loaded at runtime)
    # This is a placeholder - we'll load it dynamically
    vis_network_cdn = "https://cdn.jsdelivr.net/npm/vis-network@9.1.11/standalone/umd/vis-network.min.js"

    # Try to load vis-network from cache or use CDN fallback
    vis_network_js = _get_cached_vis_network()

    from graphify.export import (
        _node_community_map, COMMUNITY_COLORS, MAX_NODES_FOR_VIZ,
        _html_styles, _html_script, _hyperedge_script
    )
    from graphify.security import sanitize_label

    if G.number_of_nodes() > MAX_NODES_FOR_VIZ:
        raise ValueError(
            f"Graph has {G.number_of_nodes()} nodes - too large for HTML viz."
        )

    node_community = _node_community_map(communities)
    degree = dict(G.degree())
    max_deg = max(degree.values(), default=1) or 1

    vis_nodes = []
    for node_id, data in G.nodes(data=True):
        cid = node_community.get(node_id, 0)
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        label = sanitize_label(data.get("label", node_id))
        deg = degree.get(node_id, 1)
        size = 10 + 30 * (deg / max_deg)
        font_size = 12 if deg >= max_deg * 0.15 else 0
        vis_nodes.append({
            "id": node_id,
            "label": label,
            "color": {"background": color, "border": color, "highlight": {"background": "#ffffff", "border": color}},
            "size": round(size, 1),
            "font": {"size": font_size, "color": "#ffffff"},
            "title": _html.escape(label),
            "community": cid,
            "community_name": sanitize_label((community_labels or {}).get(cid, f"Community {cid}")),
            "source_file": sanitize_label(data.get("source_file", "")),
            "file_type": data.get("file_type", ""),
            "degree": deg,
        })

    vis_edges = []
    for u, v, data in G.edges(data=True):
        confidence = data.get("confidence", "EXTRACTED")
        relation = data.get("relation", "")
        vis_edges.append({
            "from": u,
            "to": v,
            "label": relation,
            "title": _html.escape(f"{relation} [{confidence}]"),
            "dashes": confidence != "EXTRACTED",
            "width": 2 if confidence == "EXTRACTED" else 1,
            "color": {"opacity": 0.7 if confidence == "EXTRACTED" else 0.35},
            "confidence": confidence,
        })

    legend_data = []
    for cid in sorted((community_labels or {}).keys()):
        color = COMMUNITY_COLORS[cid % len(COMMUNITY_COLORS)]
        lbl = _html.escape(sanitize_label((community_labels or {}).get(cid, f"Community {cid}")))
        n = len(communities.get(cid, []))
        legend_data.append({"cid": cid, "color": color, "label": lbl, "count": n})

    def _js_safe(obj) -> str:
        return _json.dumps(obj).replace("</", "<\\/")

    nodes_json = _js_safe(vis_nodes)
    edges_json = _js_safe(vis_edges)
    legend_json = _js_safe(legend_data)
    hyperedges_json = _js_safe(getattr(G, "graph", {}).get("hyperedges", []))
    title = _html.escape(sanitize_label(str(output_path)))
    stats = f"{G.number_of_nodes()} nodes &middot; {G.number_of_edges()} edges &middot; {len(communities)} communities"

    # Use embedded vis-network if available, otherwise use CDN with multiple fallbacks
    if vis_network_js:
        vis_network_script = f"<script>\n{vis_network_js}\n</script>"
    else:
        # Multiple CDN fallbacks for better availability
        vis_network_script = f"""<script src="{vis_network_cdn}"></script>
<script>
// Fallback to jsdelivr if primary fails
if (typeof vis === 'undefined') {{
  document.write('<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.11/vis-network.min.js"><\\/script>');
}}
</script>"""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>graphify - {title}</title>
{vis_network_script}
{_html_styles()}
</head>
<body>
<div id="graph"></div>
<div id="sidebar">
  <div id="search-wrap">
    <input id="search" type="text" placeholder="Search nodes..." autocomplete="off">
    <div id="search-results"></div>
  </div>
  <div id="info-panel">
    <h3>Node Info</h3>
    <div id="info-content"><span class="empty">Click a node to inspect it</span></div>
  </div>
  <div id="legend-wrap">
    <h3>Communities</h3>
    <div id="legend"></div>
  </div>
  <div id="stats">{stats}</div>
</div>
{_html_script(nodes_json, edges_json, legend_json)}
{_hyperedge_script(hyperedges_json)}
</body>
</html>"""

    Path(output_path).write_text(html, encoding="utf-8")


def _get_cached_vis_network() -> str | None:
    """Try to get vis-network from local cache."""
    import urllib.request
    import ssl

    # Try to load from CDN with timeout
    cdn_urls = [
        "https://cdn.jsdelivr.net/npm/vis-network@9.1.11/standalone/umd/vis-network.min.js",
        "https://unpkg.com/vis-network@9.1.11/standalone/umd/vis-network.min.js",
    ]

    context = ssl.create_default_context()

    for url in cdn_urls:
        try:
            with urllib.request.urlopen(url, timeout=30, context=context) as response:
                return response.read().decode('utf-8')
        except Exception:
            continue

    # Return None if all CDNs fail - will use external script tag as fallback
    return None
