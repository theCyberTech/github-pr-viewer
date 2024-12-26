# GitHub PR CLI

A command-line interface for fetching GitHub Pull Requests using a Personal Access Token.

## Requirements

- Python 3.7+
- GitHub Personal Access Token

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Configuration

Set your GitHub Personal Access Token as an environment variable:
```bash
export GITHUB_TOKEN='your-token-here'
```

Optionally, set a custom GitHub API URL:
```bash
export GITHUB_API_URL='https://api.github.com'
```

## Usage

```bash
python github_pr.py OWNER/REPO [--status STATUS] [--limit LIMIT]
```

Arguments:
- `OWNER/REPO`: Repository in format owner/repo (required)
- `--status`: PR status: open, closed, or all (default: open)
- `--limit`: Limit number of results (optional)

Examples:
```bash
# Fetch open PRs
python github_pr.py octocat/Hello-World

# Fetch closed PRs
python github_pr.py octocat/Hello-World --status closed

# Fetch all PRs with limit
python github_pr.py octocat/Hello-World --status all --limit 10
```
