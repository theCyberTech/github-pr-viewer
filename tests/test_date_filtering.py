import pytest
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))
from github_pr import fetch_pull_requests, validate_date


def test_validate_date():
    """Test date validation function"""
    assert validate_date("2023-01-01") == True
    assert validate_date("2023-13-01") == False
    assert validate_date("2023-01-32") == False
    assert validate_date("invalid-date") == False


@patch("github_pr.session")
def test_fetch_pull_requests_with_date_filters(mock_session):
    """Test fetching PRs with date filters"""
    # Setup mock response
    mock_response = MagicMock()
    mock_response.json.return_value = [{"id": 1, "title": "Test PR"}]
    mock_response.status_code = 200
    mock_response.raise_for_status.return_value = None
    mock_session.get.return_value = mock_response

    # Test created_after filter
    result = fetch_pull_requests(
        "owner/repo", "open", "test-token", created_after="2023-01-01"
    )
    assert mock_session.get.call_args[1]["params"]["created"] == ">=2023-01-01"

    # Test created_before filter
    result = fetch_pull_requests(
        "owner/repo", "open", "test-token", created_before="2023-12-31"
    )
    assert mock_session.get.call_args[1]["params"]["created"] == "<=2023-12-31"

    # Test both filters
    result = fetch_pull_requests(
        "owner/repo",
        "open",
        "test-token",
        created_after="2023-01-01",
        created_before="2023-12-31",
    )
    assert (
        mock_session.get.call_args[1]["params"]["created"] == "2023-01-01..2023-12-31"
    )


def test_invalid_date_format():
    """Test invalid date format handling"""
    with pytest.raises(ValueError):
        fetch_pull_requests(
            "owner/repo", "open", "test-token", created_after="invalid-date"
        )
    with pytest.raises(ValueError):
        fetch_pull_requests(
            "owner/repo", "open", "test-token", created_before="invalid-date"
        )
