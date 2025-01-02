import pytest
import os
import sys
from pathlib import Path
from unittest.mock import patch

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
from github_pr import validate_repository, validate_token


@pytest.mark.parametrize(
    "repo,expected",
    [
        ("owner/repo", True),
        ("owner/repo-name", True),
        ("owner/repo.name", True),
        ("owner/repo_name", True),
        ("owner/repo.name-with-dash", True),
        ("invalid", False),
        ("owner/", False),
        ("/repo", False),
        ("owner/repo/extra", False),
        ("owner@repo", False),
    ],
)
def test_validate_repository(repo, expected):
    assert validate_repository(repo) == expected


@patch.dict(os.environ, {}, clear=True)
def test_validate_token_missing():
    with pytest.raises(SystemExit):
        validate_token()


@patch.dict(os.environ, {"GITHUB_TOKEN": "test-token"})
def test_validate_token_present():
    assert validate_token() == "test-token"


def test_cache_initialization():
    """Test that the cache is properly initialized"""
    from github_pr import session
    from requests_cache import CachedSession

    assert isinstance(session, CachedSession)
