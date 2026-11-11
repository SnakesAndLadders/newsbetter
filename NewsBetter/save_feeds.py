import json
from pathlib import Path
home_dir = Path.home()
FEEDS_FILE = home_dir / ".nbfeeds.json"
def save_feeds(feeds):
    """Save feeds to the JSON file."""
    with open(FEEDS_FILE, "w") as f:
        json.dump(feeds, f, indent=4)