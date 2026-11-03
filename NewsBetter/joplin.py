# Call this from a Screen https://textual.textualize.io/guide/screens/

import json
import os
from pathlib import Path
import requests
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.widgets import Button, Footer, Header, Input, Label, TextArea

home_dir = Path.home()
CONFIG_FILE = home_dir / ".nbjoplin_settings.json"

JOPLIN_PORT = 41184


class JoplinClippingApp(App):
    """A Textual TUI for saving Markdown notes directly to Joplin with persistent settings."""

    CSS = """
    Screen {
        background: $surface;
    }
    Container {
        padding: 1;
    }
    .form-group {
        margin-bottom: 1;
        height: auto;
    }
    .label {
        width: 15;
    }
    Input {
        width: 1fr;
    }
    TextArea {
        height: 1fr;
        border: solid $primary;
        margin-top: 1;
    }
    #status-bar {
        background: #1a1a1a;
        color: $text;
        padding: 0 1;
        margin-top: 1;
        height: 3;
        content-align: center middle;
        text-align: center;
    }
    Button {
        width: 100%;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("ctrl+s", "save_note", "Save Note"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container():
            # Configuration Row (Token)
            with Horizontal(classes="form-group"):
                yield Label("Joplin Token:", classes="label")
                yield Input(placeholder="Paste your Joplin Web Clipper authorization token here...", id="token-input", password=True)
            
            # Notebook ID Row (Persistent)
            with Horizontal(classes="form-group"):
                yield Label("Notebook ID:", classes="label")
                yield Input(placeholder="Optional: Parent Notebook ID folder string...", id="parent-input")

            # Note Title Row
            with Horizontal(classes="form-group"):
                yield Label("Note Title:", classes="label")
                yield Input(placeholder="Enter note title...", id="title-input")

            # Markdown Content Body
            yield Label("Markdown Body (Ctrl+S to save):", id="body-label")
            yield TextArea(language="markdown", id="body-input")

            # Actions
            yield Button("Save Note to Joplin", variant="success", id="save-btn")
            yield Label("Ready", id="status-bar")
            
        yield Footer()

    def on_mount(self) -> None:
        """Load saved configuration settings (Token & Notebook ID) upon launching the TUI."""
        settings = self.load_settings()
        
        if "joplin_token" in settings:
            token_input = self.query_one("#token-input", Input)
            token_input.value = settings["joplin_token"]
            self.verify_token(settings["joplin_token"])
        
        # Pull Notebook ID from settings if it exists
        if "parent_id" in settings:
            self.query_one("#parent-input", Input).value = settings["parent_id"]

    def load_settings(self) -> dict:
        """Reads configuration settings from the local JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {}

    def save_settings(self, token: str, parent_id: str) -> None:
        """Saves both the Token and the Notebook ID to the JSON config file."""
        settings = {"joplin_token": token, "parent_id": parent_id}
        with open(CONFIG_FILE, "w") as f:
            json.dump(settings, f, indent=4)

    def verify_token(self, token: str) -> bool:
        """Pings the Joplin clipper service to see if the token is valid."""
        status_bar = self.query_one("#status-bar", Label)
        if not token.strip():
            status_bar.update("[b red]Error: Token cannot be blank.[/]")
            return False

        url = f"http://localhost:{JOPLIN_PORT}/ping"
        try:
            response = requests.get(url, params={"token": token}, timeout=3)
            if response.status_code == 200 and response.text == "JoplinClipperServer":
                status_bar.update("[b green]Connected to Joplin successfully![/]")
                return True
            else:
                status_bar.update("[b red]Error: Stored token is unauthorized or invalid.[/]")
                return False
        except requests.exceptions.ConnectionError:
            status_bar.update("[b orange3]Error: Cannot connect to Joplin. Ensure Joplin is open & Clipper is enabled.[/]")
            return False

    def action_save_note(self) -> None:
        """Triggered via Ctrl+S shortcut key."""
        self.process_note_submission()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Triggered via the Save UI Button click."""
        if event.button.id == "save-btn":
            self.process_note_submission()

    def process_note_submission(self, title: str, body: str) -> None:
        """Handles validation and sending data over to the Joplin API endpoints."""
        token = self.query_one("#token-input", Input).value.strip()
        parent_id = self.query_one("#parent-input", Input).value.strip()
        #title = self.query_one("#title-input", Input).value.strip()
        #body = self.query_one("#body-input", TextArea).text

        status_bar = self.query_one("#status-bar", Label)

        # Persist both fields immediately on submission
        self.save_settings(token, parent_id)

        # Verify API endpoint status
        if not self.verify_token(token):
            return

        if not title:
            status_bar.update("[b red]Error: Note Title cannot be empty![/]")
            return

        status_bar.update("Sending note data to Joplin...")
        
        # Build API payload
        url = f"http://localhost:{JOPLIN_PORT}/notes"
        payload = {"title": title, "body": body}
        if parent_id:
            payload["parent_id"] = parent_id

        try:
            response = requests.post(url, json=payload, params={"token": token})
            if response.status_code == 200:
                note_id = response.json().get("id")
                status_bar.update(f"[b green]Success! Note clipped safely (ID: {note_id})[/]")
                # Clear title and body workspace, but retain token and notebook ID configs
                self.query_one("#title-input", Input).value = ""
                self.query_one("#body-input", TextArea).text = ""
            else:
                status_bar.update(f"[b red]Failed ({response.status_code}): {response.text}[/]")
        except Exception as e:
            status_bar.update(f"[b red]Error sending request: {str(e)}[/]")


if __name__ == "__main__":
    app = JoplinClippingApp()
    app.run()
