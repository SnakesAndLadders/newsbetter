"""
Main TUI implementation for NewsBetter

Author: Shawn Ayotte
Created:
"""
# Todo: Add a "Remove Feed" option in the sidebar, allowing users to delete saved feeds from the list and the JSON file.
# Todo: Add option to save article in Markdown format to a local file, allowing users to archive articles for offline reading 
# Todo: Add option to export to Joplin using Jopin Web Clipper API, allowing users to save articles directly to their Joplin note-taking app. 
# Todo: Add option to export to Obsidian using Obsidian API, allowing users to save articles directly to their Obsidian note-taking app.
# Todo: Add option to get an AI summary of the article using whatever AI service they like, local or cloud-based, allowing users to quickly understand the main points of an article without reading the entire content.

import json
import os
import textwrap
import requests
import feedparser
from pathlib import Path
from markdownify import markdownify as md
from readability import Document
from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.widgets import Header, Footer, Input, OptionList, Label, Markdown
from textual.widgets.option_list import Option
from textual.screen import ModalScreen


home_dir = Path.home()
FEEDS_FILE = home_dir / ".nbfeeds.json"

def load_saved_feeds():
    if os.path.exists(FEEDS_FILE):
        try:
            with open(FEEDS_FILE, "r") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "Hacker News": "https://news.ycombinator.com/rss",
        "BBC News": "http://feeds.bbci.co.uk/news/rss.xml"
    }

def save_feeds(feeds):
    with open(FEEDS_FILE, "w") as f:
        json.dump(feeds, f, indent=4)


class AddFeedDialog(ModalScreen[tuple[str, str] | None]):
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
        with Vertical(id="dialog_box"):
            yield Label("Feed Name:")
            yield Input(placeholder="e.g., Slashdot", id="feed_name")
            yield Label("Feed URL:")
            yield Input(placeholder="https://example.com", id="feed_url")
            yield Label("\nPress [Enter] on URL to save, or [Esc] to cancel.", id="hint")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = self.query_one("#feed_name", Input).value.strip()
        url = self.query_one("#feed_url", Input).value.strip()
        if name and url:
            self.dismiss((name, url))
        else:
            self.dismiss(None)

    def action_quit(self) -> None:
        self.dismiss(None)

    BINDINGS = [("escape", "quit", "Cancel")]


class ReaderModeApp(App):
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
    RichLog {
        background: #1a1a1a;
        color: #e0e0e0;
        padding: 1 2;
    }
    #status-bar {
        content-align: center middle;
        width: 100%;
        margin: 1;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("a", "add_feed", "Add Feed"),
        ("b", "back_to_articles", "Focus Articles"),
        ("f", "focus_feeds", "Focus Sidebar"),
        ("left", "focus_previous", "Focus Previous"),
        ("right", "focus_next", "Focus Next")
    ]

    def __init__(self):
        super().__init__()
        self.saved_feeds = load_saved_feeds()
        self.current_feed_entries = []

    def compose(self) -> ComposeResult:
        yield Header()
        # yield Input(placeholder="Or paste temporary URL (Website or RSS) and hit Enter...", id="direct_input")
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
        self.title = "NewsBetter - TUI RSS Reader"
        self.refresh_saved_feeds_ui()
        self.query_one("#saved_feeds_list", OptionList).focus() 

    def refresh_saved_feeds_ui(self) -> None:
        feeds_list = self.query_one("#saved_feeds_list", OptionList)
        feeds_list.clear_options()
        for name in self.saved_feeds.keys():
            feeds_list.add_option(Option(name, id=name))
        feeds_list.focus()
        # feeds_list.action_first()

    def action_add_feed(self) -> None:
        def handle_dialog_result(result: tuple[str, str] | None) -> None:
            if result:
                name, url = result
                self.saved_feeds[name] = url
                save_feeds(self.saved_feeds)
                self.refresh_saved_feeds_ui()
                self.fetch_rss_feed(url)

        self.push_screen(AddFeedDialog(), handle_dialog_result)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        # CRITICAL FIX: Only parse URLs submitted via the primary top bar.
        # Ignore bubbling events sent from components inside the dialog modal.
        if event.input.id == "direct_input":
            url = event.value.strip()
            if url:
                self.fetch_rss_feed(url)
    @on(OptionList.OptionHighlighted, "#saved_feeds_list")
    @on(OptionList.OptionHighlighted, "#feed_menu")
    def on_option_list_option_selected(self, event: OptionList.OptionHighlighted) -> None:
        menu_id = event.option_list.id
        
        if menu_id == "saved_feeds_list":
            feed_name = event.option.id
            feed_url = self.saved_feeds[feed_name]
            self.fetch_rss_feed(feed_url)
            
        elif menu_id == "feed_menu":
            idx = int(event.option.id)
            entry = self.current_feed_entries[idx]
            article_url = entry.get("link")
            if article_url:
                self.load_article_reader(article_url)

    def fetch_rss_feed(self, url: str) -> None:
        viewer = self.query_one("#viewer", Markdown)
        feed_menu = self.query_one("#feed_menu", OptionList)
        
        feed_menu.clear_options()
        feed_name = next(
            (name for name, feed_url in self.saved_feeds.items() if feed_url == url),
            url,
        )
        status_bar = self.query_one("#status-bar", Label)
        #viewer.update(f"# Syncing feed source: {feed_name}...")
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
            viewer.update(f"\n# Network/Parsing Error: {str(e)}")

    def load_article_reader(self, url: str) -> None:
        viewer = self.query_one("#viewer", Markdown)
        viewer.update(f"# Opening reader mode for: {url}\n")

        try:
            response = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
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
        self.query_one("#saved_feeds_list", OptionList).focus()

    def action_back_to_articles(self) -> None:
        self.query_one("#feed_menu", OptionList).focus()


def main():
    ReaderModeApp().run()

if __name__ == "__main__":
    main()  # 1.1.2, 1.2.5