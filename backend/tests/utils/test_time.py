import pytest
from unittest.mock import patch
from datetime import datetime
from app.utils.time import get_date_str


def test_get_date_str_format():
    """Test that get_date_str returns date in YYYY-MM-DD format."""
    with patch("app.utils.time.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 1, 15, 14, 30, 45)
        
        result = get_date_str()
        
        assert result == "2024-01-15"


def test_get_date_str_single_digit_month():
    """Test formatting with single-digit month."""
    with patch("app.utils.time.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 3, 5, 10, 20, 30)
        
        result = get_date_str()
        
        assert result == "2024-03-05"


def test_get_date_str_december():
    """Test formatting with December (month 12)."""
    with patch("app.utils.time.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 12, 31, 23, 59, 59)
        
        result = get_date_str()
        
        assert result == "2024-12-31"


def test_get_date_str_leap_year():
    """Test formatting with leap year date."""
    with patch("app.utils.time.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2024, 2, 29, 12, 0, 0)
        
        result = get_date_str()
        
        assert result == "2024-02-29"


def test_get_date_str_year_2000():
    """Test formatting with year 2000."""
    with patch("app.utils.time.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2000, 1, 1, 0, 0, 0)
        
        result = get_date_str()
        
        assert result == "2000-01-01"
