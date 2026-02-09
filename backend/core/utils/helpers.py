from datetime import datetime
from zoneinfo import ZoneInfo
import json

def get_curr_time() -> str:
    """Returns current time in LA as a formatted string."""
    return datetime.now(ZoneInfo("America/Los_Angeles")).strftime("%Y-%m-%d %H:%M:%S")

def load_json(filepath: str):
    with open(filepath, "r") as f:
        data = json.load(f)
    return data