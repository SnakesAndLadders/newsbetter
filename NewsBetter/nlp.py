import strip_markdown
from textual.screen import ModalScreen
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Footer, Label, TextArea
from textual import on
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer


class AddFeedDialog(ModalScreen[tuple[str, str] | None]):
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
        with Horizontal(classes="button-group"):
            yield Button("OK", variant="success", id="ok-btn")
        yield Footer()

    def on_mount(self) -> None:
        def update_summary() -> None:
            md_to_txt = strip_markdown.strip_markdown(self.note_body)
            parser = PlaintextParser.from_string(md_to_txt, Tokenizer("english"))
            summarizer = LexRankSummarizer()
            summary = summarizer(parser.document, sentences_count=4)            
            dialog_body = self.query_one("#dialog_body", TextArea)
            dialog_body.text = "\n".join(str(sentence) for sentence in summary)
        update_summary()

    @on(Button.Pressed, "#ok-btn")
    def action_quit(self) -> None:
        """Handle the quit action."""
        self.dismiss(None)