from core.utils.time import get_date_str
from datetime import datetime
from unittest.mock import patch


def test_get_date_str():
    with patch("core.utils.time.datetime") as mock_datetime:
        mock_datetime.now.return_value = datetime(2025, 1, 1)
        assert get_date_str() == "2025-01-01"
