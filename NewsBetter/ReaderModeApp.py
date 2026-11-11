
from NewsBetter.AddFeedDialog import AddFeedDialog
from NewsBetter.JoplinClippingApp import JoplinClippingApp
from NewsBetter.SettingsDialog import SettingsDialog
from NewsBetter.SummarizeArticle import SummarizeArticle


import feedparser
import requests
from markdownify import markdownify as md
from readability import Document
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Footer, Header, Label, Markdown, OptionList
from textual.widgets.option_list import Option


import os
import re
import textwrap

from NewsBetter.load_saved_feeds import load_saved_feeds
from NewsBetter.load_settings import load_settings
from NewsBetter.save_feeds import save_feeds

from pathlib import Path
# from textual.widgets import Button

home_dir = Path.home()
FEEDS_FILE = home_dir / ".nbfeeds.json"
SETTINGS_FILE = home_dir / ".nbsettings.json"


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
        ("t", "cycle_theme", "Cycle Theme"),
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

    def action_cycle_theme(self) -> None:
        themes = list(self.available_themes.keys())
        next_index = (themes.index(self.theme) + 1) % len(themes)
        self.theme = themes[next_index]
        status_bar = self.query_one("#status-bar", Label)
        status_bar.update(f"[b green]Theme: {self.theme}[/]")

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