"""
Main TUI implementation for NewsBetter

Author: Shawn Ayotte
Created:
"""
# Todo: Add option to get an AI summary of the article using whatever AI service they like, local or cloud-based, allowing users to quickly understand the main points of an article without reading the entire content.

import json
import os
import textwrap
import requests
import re
import feedparser
from pathlib import Path
from markdownify import markdownify as md
from readability import Document
from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll, Container
from textual.widgets import Header, Footer, Input, OptionList, Label, Markdown, TextArea, RadioButton, RadioSet, Button
from textual.widgets.option_list import Option
from textual.screen import ModalScreen
import strip_markdown
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer

home_dir = Path.home()
FEEDS_FILE = home_dir / ".nbfeeds.json"
SETTINGS_FILE = home_dir / ".nbsettings.json"
JOPLIN_PORT = 41184

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

def save_feeds(feeds):
    """Save feeds to the JSON file."""
    with open(FEEDS_FILE, "w") as f:
        json.dump(feeds, f, indent=4)

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

def save_settings(settings):
    """Save settings to the JSON file."""
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

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
        background: #242424;
        border: thick #3a3a3a;
        padding: 1 2;
    }
    .label {
        margin-top: 1;
        text-style: bold;
    }
    #title-input {
        width: 1fr;
        border: solid $primary;
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

class SummarizeArticle(ModalScreen[tuple[str, str] | None]):
    def __init__(self, title: str, body: str) -> None:
        """Initialize the Joplin Clipping App with a note title and body."""
        super().__init__()
        self.note_title = title
        self.note_body = body

    CSS = """
    AddFeedDialog {
        align: center middle;
        background: rgba(0, 0, 0, 0.5);
    }
    #dialog_box {
        width: 50%;
        height: 50%;
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
            yield Label(self.note_title, id="dialog_title")
            yield TextArea("Retreiving Summary...", id="dialog_body", disabled=True)
            yield Label("Press any key to go back to the article")

    def on_mount(self) -> None:
        def update_summary() -> None:
            md_to_txt = strip_markdown.strip_markdown(self.note_body)
            parser = PlaintextParser.from_string(md_to_txt, Tokenizer("english"))
            summarizer = LexRankSummarizer()
            summary = summarizer(parser.document, sentences_count=4)
                        
            dialog_body = self.query_one("#dialog_body", TextArea)
            dialog_body.text = "\n\n".join(str(sentence) for sentence in summary)
        update_summary()

    def on_key(self, event: events.Key) -> None:
        self.dismiss(None)
    
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

class ReaderModeApp(App):
    """Main application class for the NewsBetter TUI RSS reader."""
    CSS = """
    #sidebar {
        width: 45;
        background: #1e1e1e;
        border-right: solid #3a3a3a;
    }
    #main_content {
        width: 1fr;
    }
    .sidebar-title {
        padding: 1 1 0 1;
        text-style: bold;
        color: cyan;
    }
    OptionList {
        background: transparent;
        border: none;
    }
    #saved_feeds_list {
        height: 8;
        border-bottom: solid #3a3a3a;
    }
    #feed_menu {
        height: 1fr;
    }
    Markdown {
        background: #1a1a1a;
        color: #e0e0e0;
        padding: 1 2;
    }
    #status-bar {
        content-align: center middle;
        background: transparent;
        text-align: center;
        width: 100%;
        
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add_feed", "Add Feed"),
        ("d", "delete_feed", "Delete Feed"),
        ("b", "back_to_articles", "Focus Articles"),
        ("f", "focus_feeds", "Focus Sidebar"),
        ("left", "focus_previous", "Focus Previous"),
        ("right", "focus_next", "Focus Next"),
        ("e", "export_article", "Export Article"),
        ("s", "generate_summary", "Show Summary of article"),
        ("ctrl+s", "open_settings", "Open Settings")
    ]

    def __init__(self):
        """Initialize the ReaderModeApp with saved feeds and current feed entries."""
        super().__init__()
        self.saved_feeds = load_saved_feeds()
        self.current_feed_entries = []
        self.settings = load_settings()

    def compose(self) -> ComposeResult:
        """Compose the main layout of the application."""
        yield Header(show_clock=True)
        yield Label("Ready", id="status-bar")
        
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label(" Saved Feeds (Press 'a' to add)", classes="sidebar-title")
                yield OptionList(id="saved_feeds_list")
                yield Label(" Articles Menu", classes="sidebar-title")
                yield OptionList(id="feed_menu", compact=True)
            with Vertical(id="main_content"):
                yield VerticalScroll(Markdown(id="viewer"))
                
        yield Footer()

    def on_mount(self) -> None:
        """Called when the app is mounted; sets the title and refreshes the saved feeds UI."""
        self.title = "NewsBetter - TUI RSS Reader"
        self.refresh_saved_feeds_ui()
        self.query_one("#saved_feeds_list", OptionList).focus() 

    def refresh_saved_feeds_ui(self) -> None:
        """Refresh the saved feeds list in the UI."""
        feeds_list = self.query_one("#saved_feeds_list", OptionList)
        feeds_list.clear_options()
        for name in self.saved_feeds.keys():
            feeds_list.add_option(Option(name, id=name))
        feeds_list.focus()

    def action_add_feed(self) -> None:
        """Action to add a new feed; opens the AddFeedDialog and handles the result."""
        status_bar = self.query_one("#status-bar", Label)
        def handle_dialog_result(result: tuple[str, str] | None) -> None:
            if result:
                name, url = result
                self.saved_feeds[name] = url
                save_feeds(self.saved_feeds)
                self.refresh_saved_feeds_ui()
                self.fetch_rss_feed(url)
        try:
            self.push_screen(AddFeedDialog(), handle_dialog_result)
        except Exception as e:
                    status_bar.update(f"[b red]Error adding feed: {str(e)}[/]")

    def action_delete_feed(self) -> None:
        """Action to delete the selected feed from the saved feeds list."""
        feeds_list = self.query_one("#saved_feeds_list", OptionList)
        try:
            if feeds_list.highlighted is not None:
                selected_option = feeds_list.get_option_at_index(feeds_list.highlighted)
            if selected_option:
                feed_name = selected_option.id
                if feed_name is not None and feed_name in self.saved_feeds:
                    del self.saved_feeds[feed_name]
                    save_feeds(self.saved_feeds)
                    self.refresh_saved_feeds_ui()
                    status_bar = self.query_one("#status-bar", Label)
                    status_bar.update(f"[b yellow]Deleted feed: {feed_name}[/]")
        except Exception as e:
                    status_bar.update(f"[b red]Error deleting feed: {str(e)}[/]")
    
    # Enabling the 2 lines below will load the article when you highlight it in the feed menu, 
    #   and it will load the article when you highlight a feed in the saved feeds list.
    #   I thought it was a good idea but it was a bit too much for the user experience, so I commented it out.
    #@on(OptionList.OptionHighlighted, "#saved_feeds_list")
    #@on(OptionList.OptionHighlighted, "#feed_menu")
    
    def on_option_list_option_selected(self, event: OptionList.OptionHighlighted) -> None:
        """Handle the selection of an option in either the saved feeds list or the feed menu."""
        menu_id = event.option_list.id
        status_bar = self.query_one("#status-bar", Label)
        viewer = self.query_one("#viewer", Markdown)
        if menu_id == "saved_feeds_list":
            feed_name = event.option.id
            if feed_name is None:
                return
            feed_url = self.saved_feeds[feed_name]
            status_bar.update("")
            viewer.update("")
            self.fetch_rss_feed(feed_url)
            
        elif menu_id == "feed_menu":
            option_id = event.option.id
            if option_id is None:
                return
            idx = int(option_id)
            entry = self.current_feed_entries[idx]
            article_url = entry.get("link")
            status_bar.update("")
            if article_url:
                self.load_article_reader(article_url)

    def fetch_rss_feed(self, url: str) -> None:
        """Fetch and display the RSS feed entries for the given URL."""
        feed_menu = self.query_one("#feed_menu", OptionList)
        
        feed_menu.clear_options()
        feed_name = next(
            (name for name, feed_url in self.saved_feeds.items() if feed_url == url),
            url,
        )
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"[b green]Syncing feed source: {feed_name}[/]")

        try:
            feed_data = feedparser.parse(url, agent="Mozilla/5.0")
            if feed_data.entries:
                status_bar.update(f"[b green]Loaded  {feed_name} successfully.[/]")
                self.current_feed_entries = feed_data.entries
                
                for idx, entry in enumerate(self.current_feed_entries):
                    title = entry.get("title", f"Article {idx + 1}")
                    feed_menu.add_option(Option(textwrap.shorten(title, width=40, placeholder="..."), id=str(idx)))
                    
                
                feed_menu.focus()
                feed_menu.action_first()
            else:
                self.load_article_reader(url)

        except Exception as e:
            status_bar.update(f"[b red]Error loading feed: {str(e)}[/]")

    def load_article_reader(self, url: str) -> None:
        """Load and display the article content in reader mode for the given URL."""
        viewer = self.query_one("#viewer", Markdown)
        viewer.update(f"# Opening reader mode for: {url}\n")
                    
        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0"})
            response.raise_for_status()

            doc = Document(response.text)
            title = doc.title()
            clean_html = doc.summary()
            markdown_content = md(clean_html, heading_style="ATX")
            viewer.update("")
            viewer.update(f"# {title} \n\n" + f"## [Link to article:]({url}) \n\n" + markdown_content)
            viewer.focus()

        except Exception as e:
            viewer.update(f"# Failed to extract content: {str(e)}")

    def action_focus_feeds(self) -> None:
        """Focus the saved feeds list in the sidebar."""
        self.query_one("#saved_feeds_list", OptionList).focus()

    def action_back_to_articles(self) -> None:
        """Focus the feed menu in the sidebar to view articles."""
        self.query_one("#feed_menu", OptionList).focus()

    def action_focus_previous(self) -> None:
        """Move focus to the previous focusable widget."""
        self.screen.focus_previous()

    def action_focus_next(self) -> None:
        """Move focus to the next focusable widget."""
        self.screen.focus_next()

    def action_open_settings(self) -> None:
        """Open the settings dialog to configure application settings."""
        def handle_dialog_result(result: dict[str, str] | None) -> None:
            if result:
                status_bar = self.query_one("#status-bar", Label)
                self.settings = load_settings()
                status_bar.update(f"[b green]Settings saved successfully.[/]")
        self.push_screen(SettingsDialog(), handle_dialog_result)

    def action_export_article(self) -> None:
        """Export the currently viewed article based on the selected export option (Joplin, Markdown, or Obsidian)."""
        markdown_content = self.query_one("#viewer", Markdown)
        if not markdown_content._markdown.strip():
            status_bar = self.query_one("#status-bar", Label)
            status_bar.update(f"[b red]No article loaded.[/]")
            return
        
        settings = self.settings
        if settings.get("joplin_enabled"):
            self.action_send_to_joplin()
        elif settings.get("md_export"):
            self.action_export_to_markdown()
        elif settings.get("obsidian_enabled"):
            self.action_export_to_obsidian()
        else:
            status_bar = self.query_one("#status-bar", Label)
            status_bar.update(f"[b red]No export option selected, press 'ctrl+s' to set up an export option.[/]")

    def action_export_to_markdown(self) -> None:
        """Export the currently viewed article to a Markdown file."""
        markdown_content = self.query_one("#viewer", Markdown)
        title_md = markdown_content._markdown.split('\n')[0].lstrip("# ").strip()
        title = re.sub(r'[^a-zA-Z0-9\s]', '', title_md)
        body = markdown_content._markdown
        settings = self.settings
        export_path = settings.get("md_export_path", str(home_dir / "NewsBetter_Articles"))
        os.makedirs(export_path, exist_ok=True)
        file_path = os.path.join(export_path, f"{title}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body)
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"[b green]Article exported to Markdown: {file_path}[/]")

    def action_export_to_obsidian(self) -> None:
        """Export the currently viewed article to an Obsidian vault."""
        markdown_content = self.query_one("#viewer", Markdown)
        title = markdown_content._markdown.split('\n')[0].lstrip("# ").strip()
        body = markdown_content._markdown
        settings = self.settings
        vault_path = settings.get("obsidian_vault_path", str(home_dir / "ObsidianVault"))
        os.makedirs(vault_path, exist_ok=True)
        file_path = os.path.join(vault_path, f"{title}.md")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(body)
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"[b green]Article exported to Obsidian: {file_path}[/]")

    def action_send_to_joplin(self) -> None:
        """Send the currently viewed article to Joplin using the Joplin Web Clipper API."""
        def handle_dialog_result(result: tuple[str, str] | None) -> None:
            if result:
                state, status = result
                status_bar = self.query_one("#status-bar", Label)
                status_bar.update(f"[b green]{status}[/]")

        joplin_token = self.settings.get("joplin_token", "")
        parent_id = self.settings.get("joplin_notebook_id", "")
        self.query_one("#viewer", Markdown).focus()
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"[b yellow]Preparing to send article to Joplin...[/]")
        markdown_content = self.query_one("#viewer", Markdown)
        title = markdown_content._markdown.split('\n')[0].lstrip("# ").strip()
        body = markdown_content._markdown
        self.push_screen(JoplinClippingApp(title, body, joplin_token, parent_id), handle_dialog_result)

    def action_generate_summary(self) -> None:
        """Generate a summary of the currently viewed article."""
        markdown_content = self.query_one("#viewer", Markdown)
        if not markdown_content._markdown.strip():
            status_bar = self.query_one("#status-bar", Label)
            status_bar.update(f"[b red]No article loaded.[/]")
            return
        markdown_content = self.query_one("#viewer", Markdown)
        title = markdown_content._markdown.split('\n')[0].lstrip("# ").strip()
        body = markdown_content._markdown
        self.push_screen(SummarizeArticle(title, body))

def main():
    """Entry point for the NewsBetter TUI application."""
    ReaderModeApp().run()

if __name__ == "__main__":
    main()  # 1.1.2, 1.2.5