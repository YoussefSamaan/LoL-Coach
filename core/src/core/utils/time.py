from datetime import datetime


def get_date_str() -> str:
    """Returns current date in YYYY-MM-DD format."""
    return datetime.now().strftime("%Y-%m-%d")
