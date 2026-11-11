
import requests
from textual.app import ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Label, Markdown

JOPLIN_PORT = 41184

class JoplinClippingApp(ModalScreen[tuple[str, str] | None]):
    """A Textual TUI for saving Markdown notes directly to Joplin with persistent settings."""
    def __init__(self, title: str, body: str, joplin_token: str, parent_id: str) -> None:
        """Initialize the Joplin Clipping App with a note title and body."""
        super().__init__()
        #self.settings = load_settings()
        self.joplin_token = joplin_token
        self.parent_id = parent_id
        self.note_title = title
        self.note_body = body

    CSS = """
    .form-group {
        width: 75%;
        height: 95%;
        background: #242424;\
        padding: 1 2;
        margin-top: 1;
    }
    .label {
        margin-top: 1;
        text-style: bold;
    }
    #title-input {
        width: 1fr;
        border: thick #3a3a3a;
        margin-top: 1;
    }
    #body-input {
        border: thick #3a3a3a;
        width: 1fr;
        margin-top: 1;
    }
    #notebook-name {
        border: thick #3a3a3a;
        width: 1fr;
        margin-top: 1;
    }
    """

    BINDINGS = [
            ("escape", "quit", "Cancel"),
            ("ctrl+s", "save_note", "Save Settings")
            ]

    def compose(self) -> ComposeResult:
        """Compose the UI layout for the Joplin Clipping App."""
            # Note Title Row
        with Vertical(classes="form-group"):
            yield Label("Ready", id="status-bar")
            yield Label("Saving to Notebook:", classes="label")
            yield Label("Unknown Notebook", id="notebook-name")
            yield Label("Note Title:", classes="label")
            yield Label(self.note_title, id="title-input")
            yield Label("Body (Ctrl+S to save or Esc to cancel):", classes="label")
            yield VerticalScroll(Markdown(self.note_body, id="body-input"))

    def on_mount(self) -> None:
        """Load saved configuration settings (Token & Notebook ID) upon launching the TUI."""
        # Pull Notebook ID from settings if it exists
        def get_notebook_title(notebook_id: str, token: str) -> str:
            """Fetch the notebook title from Joplin using the notebook ID."""
            url = f"http://localhost:{JOPLIN_PORT}/folders/{notebook_id}"
            try:
                response = requests.get(url, params={"token": token}, timeout=3)
                if response.status_code == 200:
                    return response.json().get("title", "")
                else:
                    return "Cannot connect to joplin Notebook"
            except requests.exceptions.RequestException:
                return "Error Notebook" + str(response.status_code) + " " + str(response.text)
        self.query_one("#notebook-name", Label).update(get_notebook_title(notebook_id=self.parent_id, token=self.joplin_token))

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
        """Triggered via [Esc] key to close the settings dialog."""
        status = "[b red]Note clipping canceled by user.[/]"
        self.dismiss(("Cancel", status))

    def process_note_submission(self) -> None:
        """Handles validation and sending data over to the Joplin API endpoints."""

        token = self.joplin_token
        parent_id = self.parent_id
        title = self.note_title.strip()
        body = self.note_body.strip()
        status_bar = self.query_one("#status-bar", Label)

        # Verify API endpoint status
        if not isinstance(token, str) or not self.verify_token(token):
            status_bar.update("[b red]Error: Invalid or missing token![/]")
            return

        if not title:
            status_bar.update("[b red]Error: Note Title cannot be empty![/]")
            return

        if not body:
            status_bar.update("[b red]Error: Note Body cannot be empty![/]")
            return

        if parent_id and not isinstance(parent_id, str):
            status_bar.update("[b red]Error: Notebook ID must be a string![/]")
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
                self.query_one("#body-input", Markdown).update("")
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