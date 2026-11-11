
import json
import os

from NewsBetter.save_feeds import save_feeds
from pathlib import Path
home_dir = Path.home()
FEEDS_FILE = home_dir / ".nbfeeds.json"
def load_saved_feeds():
    """Load saved feeds from the JSON file, or return default feeds if the file doesn't exist or is invalid."""
    default_feeds = {
        "Hacker News": "https://news.ycombinator.com/rss",
        "BBC News": "http://feeds.bbci.co.uk/news/rss.xml"
    }
    if os.path.exists(FEEDS_FILE):
        try:
            with open(FEEDS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            # If there's an error reading the file, return default feeds
            return default_feeds
    else:
        # If the file doesn't exist, create it with default feeds and return them
        save_feeds(default_feeds)
        return default_feeds