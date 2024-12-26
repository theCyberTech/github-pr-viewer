#!/usr/bin/env python3
import os
import sys
from typing import Optional
import re
import requests
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import typer
from dotenv import load_dotenv

# Constants
DEFAULT_API_URL = "https://api.github.com"
REPO_PATTERN = r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"

# Initialize console and app
console = Console()
app = typer.Typer()


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


def fetch_pull_requests(
    repository: str, status: str, token: str, limit: Optional[int] = None
) -> list:
    """Fetch pull requests from GitHub API with pagination support."""
    api_url = os.getenv("GITHUB_API_URL", DEFAULT_API_URL)
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    pulls = []
    page = 1

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        progress.add_task(description="Fetching pull requests...", total=None)

        while True:
            url = f"{api_url}/repos/{repository}/pulls"
            params = {"state": status, "page": page, "per_page": 100}

            try:
                response = requests.get(url, headers=headers, params=params)
                response.raise_for_status()

                batch = response.json()
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


def display_results(pulls: list) -> None:
    """Display pull requests in a formatted table."""
    table = Table(show_header=True, header_style="bold")
    table.add_column("Number")
    table.add_column("Title")
    table.add_column("Author")
    table.add_column("Status")
    table.add_column("Created")
    table.add_column("Updated")

    for pr in pulls:
        table.add_row(
            str(pr["number"]),
            pr["title"],
            pr["user"]["login"],
            pr["state"],
            pr["created_at"].split("T")[0],
            pr["updated_at"].split("T")[0],
        )

    console.print(table)


@app.command()
def main(
    repository: str = typer.Argument(..., help="Repository in format owner/repo"),
    status: str = typer.Option(
        "open", "--status", help="PR status: open, closed, or all"
    ),
    limit: Optional[int] = typer.Option(
        None, "--limit", help="Limit number of results"
    ),
):
    """
    Fetch GitHub Pull Requests for a specified repository.
    """
    # Load environment variables
    load_dotenv()

    # Validate inputs
    if not validate_repository(repository):
        sys.exit(1)

    if status not in ["open", "closed", "all"]:
        console.print(
            "[red]Error: Invalid status. Use 'open', 'closed', or 'all'[/red]"
        )
        sys.exit(1)

    token = validate_token()

    # Fetch and display results
    pulls = fetch_pull_requests(repository, status, token, limit)
    display_results(pulls)


if __name__ == "__main__":
    app()
