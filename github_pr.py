#!/usr/bin/env python3
import os
import sys
from typing import Optional
import re
from datetime import datetime
import aiohttp
import aiohttp_client_cache
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.box import ROUNDED
import argparse
from dotenv import load_dotenv

# Constants
DEFAULT_API_URL = "https://api.github.com"
REPO_PATTERN = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"

# Initialize console
console = Console()



def validate_token() -> str:
    """Validate GitHub token from environment variables."""
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        console.print("[red]Error: GITHUB_TOKEN environment variable not set[/red]")
        console.print("Please set your GitHub Personal Access Token:")
        console.print("export GITHUB_TOKEN='your-token-here'")
        sys.exit(1)
    return token


def validate_repository(repository: str) -> bool:
    """Validate repository format (owner/repo)."""
    if not re.match(REPO_PATTERN, repository):
        console.print("[red]Error: Invalid repository format[/red]")
        console.print("Format should be: owner/repository")
        return False
    return True


def validate_date(date_str: str) -> bool:
    """Validate date string format (YYYY-MM-DD)."""
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


async def create_session():
    """Create and return a cached aiohttp session."""
    return aiohttp_client_cache.CachedSession(
        cache_name="github_cache",
        backend="sqlite",
        expire_after=300,  # 5 minutes
        allowable_methods=("GET",)
    )

async def fetch_pull_requests(
    repository: str,
    status: str,
    token: str,
    limit: Optional[int] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
) -> list:
    """Fetch pull requests from GitHub API with pagination support.

    Args:
        repository: Repository name in format 'owner/repo'
        status: PR status ('open', 'closed', or 'all')
        token: GitHub API token
        limit: Maximum number of PRs to return
        created_after: Only include PRs created after this date (YYYY-MM-DD)
        created_before: Only include PRs created before this date (YYYY-MM-DD)
    """
    if created_after and not validate_date(created_after):
        raise ValueError("created_after must be in YYYY-MM-DD format")
    if created_before and not validate_date(created_before):
        raise ValueError("created_before must be in YYYY-MM-DD format")

    api_url = os.getenv("GITHUB_API_URL", DEFAULT_API_URL)
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    session = await create_session()
    pulls = []
    page = 1

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
        ) as progress:
            progress.add_task(description="Fetching pull requests...", total=None)

        while True:
            url = f"{api_url}/repos/{repository}/pulls"
            params = {"state": status, "page": page, "per_page": 100}
            if created_after:
                params["created"] = f">={created_after}"
            if created_before:
                params["created"] = f"<={created_before}"
            if created_after and created_before:
                params["created"] = f"{created_after}..{created_before}"

            try:
                async with session.get(url, headers=headers, params=params) as response:
                    response.raise_for_status()
                    batch = await response.json()
                if not batch:
                    break

                pulls.extend(batch)
                if limit and len(pulls) >= limit:
                    pulls = pulls[:limit]
                    break

                if len(batch) < 100:
                    break

                page += 1

            except requests.exceptions.RequestException as e:
                if response.status_code == 401:
                    console.print("[red]Error: Invalid GitHub token[/red]")
                elif response.status_code == 403:
                    console.print("[red]Error: API rate limit exceeded[/red]")
                elif response.status_code == 404:
                    console.print("[red]Error: Repository not found[/red]")
                else:
                    console.print(f"[red]Error: {str(e)}[/red]")
                sys.exit(1)

        return pulls
    finally:
        await session.close()


def display_results(pulls: list) -> None:
    """Display pull requests with enhanced statistics and formatting."""
    # Calculate statistics
    total_prs = len(pulls)
    open_prs = len([pr for pr in pulls if pr["state"] == "open"])
    closed_prs = len([pr for pr in pulls if pr["state"] == "closed"])
    oldest_pr = min(pulls, key=lambda x: x["created_at"])["created_at"].split("T")[0]
    newest_pr = max(pulls, key=lambda x: x["created_at"])["created_at"].split("T")[0]
    
    # Create statistics panel
    stats_panel = Panel(
        Columns([
            Text(f"Total PRs: {total_prs}", style="bold"),
            Text(f"Open: {open_prs}", style="green"),
            Text(f"Closed: {closed_prs}", style="red"),
            Text(f"Oldest: {oldest_pr}"),
            Text(f"Newest: {newest_pr}")
        ]),
        title="[bold]PR Statistics[/bold]",
        border_style="blue",
        box=ROUNDED
    )
    
    # Create PR table
    table = Table(show_header=True, header_style="bold", box=ROUNDED)
    table.add_column("Number", justify="right")
    table.add_column("Title", style="cyan")
    table.add_column("Author", style="magenta")
    table.add_column("Status", justify="center")
    table.add_column("Created", justify="right")
    table.add_column("Updated", justify="right")

    for pr in pulls:
        status_style = "green" if pr["state"] == "open" else "red"
        table.add_row(
            str(pr["number"]),
            pr["title"],
            pr["user"]["login"],
            f"[{status_style}]{pr['state']}[/{status_style}]",
            pr["created_at"].split("T")[0],
            pr["updated_at"].split("T")[0],
        )

    # Display results
    console.print(stats_panel)
    console.print("\n")
    console.print(table)


def export_to_csv(pulls: list, file_path: str) -> None:
    """Export pull requests to CSV file."""
    import csv
    
    with open(file_path, "w", newline="") as csvfile:
        fieldnames = ["number", "title", "author", "status", "created", "updated"]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        
        writer.writeheader()
        for pr in pulls:
            writer.writerow({
                "number": pr["number"],
                "title": pr["title"],
                "author": pr["user"]["login"],
                "status": pr["state"],
                "created": pr["created_at"].split("T")[0],
                "updated": pr["updated_at"].split("T")[0]
            })

def export_to_json(pulls: list, file_path: str) -> None:
    """Export pull requests to JSON file."""
    import json
    
    data = [{
        "number": pr["number"],
        "title": pr["title"],
        "author": pr["user"]["login"],
        "status": pr["state"],
        "created": pr["created_at"].split("T")[0],
        "updated": pr["updated_at"].split("T")[0]
    } for pr in pulls]
    
    with open(file_path, "w") as jsonfile:
        json.dump(data, jsonfile, indent=2)

async def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub Pull Requests for a specified repository.")
    parser.add_argument("repository", help="Repository in format owner/repo")
    parser.add_argument("--status", default="open", help="PR status: open, closed, or all")
    parser.add_argument("--limit", type=int, help="Limit number of results")
    parser.add_argument("--created-after", help="Only include PRs created after this date (YYYY-MM-DD)")
    parser.add_argument("--created-before", help="Only include PRs created before this date (YYYY-MM-DD)")
    parser.add_argument("--export-format", choices=["csv", "json"], help="Export format: csv or json")
    parser.add_argument("--output-file", help="Output file path for export")
    
    args = parser.parse_args()
    """
    Fetch GitHub Pull Requests for a specified repository.
    """
    # Load environment variables
    load_dotenv()

    # Validate inputs
    if not validate_repository(args.repository):
        sys.exit(1)

    if args.status not in ["open", "closed", "all"]:
        console.print(
            "[red]Error: Invalid status. Use 'open', 'closed', or 'all'[/red]"
        )
        sys.exit(1)

    token = validate_token()

    # Fetch results
    pulls = await fetch_pull_requests(
        args.repository, 
        args.status, 
        token, 
        args.limit, 
        args.created_after, 
        args.created_before
    )
    
    # Handle export if requested
    if args.export_format and args.output_file:
        if args.export_format == "csv":
            export_to_csv(pulls, args.output_file)
            console.print(f"[green]Exported results to {args.output_file} (CSV)[/green]")
        elif args.export_format == "json":
            export_to_json(pulls, args.output_file)
            console.print(f"[green]Exported results to {args.output_file} (JSON)[/green]")
        else:
            console.print("[red]Error: Invalid export format. Use 'csv' or 'json'[/red]")
            sys.exit(1)
    
    # Display results if no export requested
    if not args.export_format or not args.output_file:
        display_results(pulls)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
