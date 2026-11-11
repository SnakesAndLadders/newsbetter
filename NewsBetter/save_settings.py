from pathlib import Path
import json

home_dir = Path.home()
SETTINGS_FILE = home_dir / ".nbsettings.json"

def save_settings(settings):
    """Save settings to the JSON file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)