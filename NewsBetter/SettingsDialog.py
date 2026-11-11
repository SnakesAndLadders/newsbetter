from NewsBetter.save_settings import save_settings


from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.screen import ModalScreen
from textual.widgets import Input, Label, RadioButton, RadioSet

from NewsBetter.load_settings import load_settings


class SettingsDialog(ModalScreen[dict[str, str] | None]):
    """A modal dialog for configuring application settings."""
    CSS = """
    Container {
        width: 45%;
        background: #242424;
        border: thick #3a3a3a;
        padding: 1 2;
        content-align: center middle;
        }
    """

    BINDINGS = [
        ("escape", "quit", "Cancel"),
        ("ctrl+s", "save_now", "Save Settings")
    ]

    def compose(self) -> ComposeResult:
        """Compose the settings dialog layout."""
        with Container():
            with Vertical(id="dialog_box"):
                yield Label("Select Export Option:")
                with RadioSet(id="focus_me"):
                    yield RadioButton("Joplin", id="joplin_radio")
                    yield RadioButton("Markdown", id="markdown_radio")
                    yield RadioButton("Obsidian", id="obsidian_radio")
                    yield RadioButton("HTML", id="HTML_path")
                with Vertical():
                    yield Label("Configure Export Settings:")
                    yield Label("Joplin Token:")
                    yield Input(placeholder="Enter Joplin Token", id="joplin_token_input", password=True)
                    yield Label("Joplin Notebook ID:")
                    yield Input(placeholder="Enter Joplin Notebook ID", id="joplin_notebook_input")
                    yield Label("Markdown Export Path (It will create the folder if it does not exist):")
                    yield Input(placeholder="Enter Markdown Export Path", id="md_export_path_input")
                    yield Label("Obsidian Vault Path:")
                    yield Input(placeholder="Enter Obsidian Vault Path (It will create the folder if it does not exist)", id="obsidian_vault_path_input")
                yield Label("\nPress ctrl-s to save, or Esc to cancel.", id="hint")

    def action_quit(self) -> None:
        """Triggered via [Esc] key to close the settings dialog."""
        self.dismiss(None)

    def action_save_now(self) -> None:
        """Triggered via Ctrl-s key to save settings and close the dialog."""
        settings = {
            "joplin_enabled": self.query_one("#joplin_radio", RadioButton).value,
            "md_export": self.query_one("#markdown_radio", RadioButton).value,
            "obsidian_enabled": self.query_one("#obsidian_radio", RadioButton).value,
            "joplin_token": self.query_one("#joplin_token_input", Input).value,
            "joplin_notebook_id": self.query_one("#joplin_notebook_input", Input).value,
            "md_export_path": self.query_one("#md_export_path_input", Input).value,
            "obsidian_vault_path": self.query_one("#obsidian_vault_path_input", Input).value,
        }
        save_settings(settings)
        self.dismiss(settings)

    def on_mount(self) -> None:
        """Load current settings when the dialog is mounted."""
        settings = load_settings()
        if settings.get("joplin_enabled"):
            self.query_one("#joplin_radio", RadioButton).value = True
        elif settings.get("md_export"):
            self.query_one("#markdown_radio", RadioButton).value = True
        elif settings.get("obsidian_enabled"):
            self.query_one("#obsidian_radio", RadioButton).value = True

        if settings.get("joplin_token"):
            self.query_one("#joplin_token_input", Input).value = settings["joplin_token"]
        if settings.get("joplin_notebook_id"):
            self.query_one("#joplin_notebook_input", Input).value = settings["joplin_notebook_id"]
        if settings.get("md_export_path"):
            self.query_one("#md_export_path_input", Input).value = settings["md_export_path"]
        if settings.get("obsidian_vault_path"):
            self.query_one("#obsidian_vault_path_input", Input).value = settings["obsidian_vault_path"]