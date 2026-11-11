import json
import os

from NewsBetter.save_settings import save_settings

from pathlib import Path
home_dir = Path.home()
SETTINGS_FILE = home_dir / ".nbsettings.json"

def load_settings():
    """Load settings from the JSON file, or return default settings if the file doesn't exist or is invalid."""
    default_settings = {
        "joplin_enabled": False,
        "joplin_token": "",
        "joplin_url": "http://localhost:41184",
        "joplin_notebook": "",
        "md_export": False,
        "md_export_path": str(home_dir / "NewsBetter_Articles"),
        "obsidian_enabled": False,
        "obsidian_vault_path": str(home_dir / "ObsidianVault"),
    }
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            # If there's an error reading the file, return default settings
            return default_settings
    else:
        # If the file doesn't exist, create it with default settings and return them
        save_settings(default_settings)
        return default_settings