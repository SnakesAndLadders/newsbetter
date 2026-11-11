from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label


class AddFeedDialog(ModalScreen[tuple[str, str] | None]):
    """A modal dialog for adding a new RSS feed."""
    CSS = """
    AddFeedDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #dialog_box {
        width: 60;
        height: auto;
        background: #242424;
        border: thick #3a3a3a;
        padding: 1 2;
    }
    Label {
        margin-top: 1;
        text-style: bold;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the dialog layout."""
        with Vertical(id="dialog_box"):
            yield Label("Feed Name:")
            yield Input(placeholder="e.g., Slashdot", id="feed_name")
            yield Label("Feed URL:")
            yield Input(placeholder="https://example.com", id="feed_url")
            yield Label("\nPress Enter on URL to save, or Esc to cancel.", id="hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle the submission of the feed name and URL."""
        name_input = self.query_one("#feed_name", Input)
        url_input = self.query_one("#feed_url", Input)

        if event.input.id == "feed_name":
            url_input.focus()
            return

        name = name_input.value.strip()
        url = url_input.value.strip()
        if name and url:
            self.dismiss((name, url))
        elif not name:
            name_input.focus()
        else:
            url_input.focus()

    def action_quit(self) -> None:
        """Triggered via [Esc] key to cancel the dialog."""
        self.dismiss(None)

    BINDINGS = [("escape", "quit", "Cancel")]