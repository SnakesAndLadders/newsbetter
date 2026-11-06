import json
import os
from pathlib import Path
import requests
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, TextArea
from textual.screen import ModalScreen

home_dir = Path.home()
CONFIG_FILE = home_dir / ".nbjoplin_settings.json"

JOPLIN_PORT = 41184


class JoplinClippingApp(ModalScreen[tuple[str, str] | None]):
    """A Textual TUI for saving Markdown notes directly to Joplin with persistent settings."""
    def __init__(self, title: str, body: str) -> None:
        """Initialize the Joplin Clipping App with a note title and body."""
        super().__init__()
        self.note_title = title
        self.note_body = body

    CSS = """
    Screen {
        background: $surface;
    }
    Container {
        width: 75%;
        height: 95%;
        background: #242424;
        border: thick #3a3a3a;
        padding: 1 2;
        content-align: center middle;
    }
    .form-group {
        width: 50%;
        background: #242424;
        border: thick #3a3a3a;
        padding: 1 2;
    }
    .form-container {
        width: 100%;
        height: 7;
        content-align: center middle;
    }
    .title-group {
        width: 100%;
        background: #242424;
        border: thick #3a3a3a;
        padding: 1 2;
    }
    .body-group {
            width: 1fr;
            background: #242424;
            border: thick #3a3a3a;
            padding: 1 2;
    }
    .button-group {
        width: 100%;
        content-align: center middle;
        padding: 1 2;
    }
    .label {
        margin-top: 1;
        text-style: bold;
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
        background: transparent;
        text-align: center;
        width: 100%;
        content-align: center middle;
    }
    #token-input {
        width: 1fr;
    }
    #title-input {
        width: 1fr;
        border: solid $primary;
        margin-top: 1;
    }
    Button {
        width: 20;
        margin-top: 1;
        border: thick #3a3a3a;
    }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("ctrl+s", "save_note", "Save Note"),
    ]

    def compose(self) -> ComposeResult:
        """Compose the UI layout for the Joplin Clipping App."""
        yield Header(show_clock=True)
        with Container():
            # Configuration Row (Token)
            with Horizontal(classes="form-container"):
                with Horizontal(classes="form-group"):
                    yield Label("Joplin Token:", classes="label")
                    yield Input(placeholder="Paste your Joplin Web Clipper authorization token here...", id="token-input", password=True)
                
                # Notebook ID Row (Persistent)
                with Horizontal(classes="form-group"):
                    yield Label("Notebook ID:", classes="label")
                    yield Input(placeholder="Optional: Parent Notebook ID folder string...", id="parent-input")
            

            # Note Title Row
            with Vertical(classes="title-group"):
                yield Label("Note Title:", classes="label")
                yield Label(self.note_title, id="title-input")

            # Markdown Content Body
            with Vertical(classes="body-group"):
                yield Label("Markdown Body (Ctrl+S to save):", classes="label")
                yield TextArea(self.note_body, language="markdown", id="body-input")

            # Actions
            with Horizontal(classes="button-group"):
                yield Button("Save to Joplin", variant="success", id="save-btn")
                yield Button("Cancel", variant="error", id="cancel-btn")
            
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

    def action_quit(self) -> None:
        """Triggered via Ctrl+q shortcut key."""
        status = "[b red]Note clipping canceled by user.[/]"
        self.dismiss(("Cancel", status))

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Triggered via the Save UI Button click."""
        if event.button.id == "save-btn":
            self.process_note_submission()
        elif event.button.id == "cancel-btn":
            status = "[b red]Note clipping canceled by user.[/]"
            self.dismiss(("Cancel", status))

    def process_note_submission(self) -> None:
        """Handles validation and sending data over to the Joplin API endpoints."""
        token = self.query_one("#token-input", Input).value.strip()
        parent_id = self.query_one("#parent-input", Input).value.strip()
        title = self.note_title.strip()
        body = self.note_body.strip()
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
                status_bar.update(f"[b green]Success! Note clipped (ID: {note_id})[/]")
                # Clear title and body workspace, but retain token and notebook ID configs
                self.query_one("#title-input", Label).update("")
                self.query_one("#body-input", TextArea).text = ""
                status = f"[b green]Success! Note clipped (ID: {note_id}).[/]"
                self.dismiss(("Success", status))
                
            else:
                status_bar.update(f"[b red]Failed ({response.status_code}): {response.text}[/]")
                status = f"[b red]Error: {response.text}[/]"
                self.dismiss(("Error", status))
        except Exception as e:
            status_bar.update(f"[b red]Error sending request: {str(e)}[/]")
            status = f"[b red]Error sending request: {str(e)}[/]"
            self.dismiss(("Error", status))
