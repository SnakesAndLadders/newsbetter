"""Main TUI implementation for NewsBetter

Author: Shawn Ayotte
Created:
"""

import os
import textwrap
import json
import sys
from pathlib import Path
import py_cui
import feedparser
from newspaper import Article, Config

__version__ = 'v1.0.4'

urlfile = Path(str(Path.home()) + '/.nburls')
urlfile.touch(exist_ok=True)

settingsfile = Path(str(Path.home()) + '/.nbsettings')
settingsfile.touch(exist_ok=True)

config = Config()
config.browser_user_agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124  Safari/537.36'
config.fetch_images = False

columns, rows = os.get_terminal_size(0)

class NewsbetterApp:

    def __init__(self, root: py_cui.PyCUI):
        self.root = root
        self.feed = ""
        self.summary = 0
        self.d = {}
        self.feed_list = self.root.add_scroll_menu('Source', 0, 0, row_span=2, column_span=3)

        # Add sources from URLS file
        self.load_feeds()
        sources=[]
        for source in self.d:
            sources.append(source)
        self.feed_list.add_item_list(sources)
        self.root.move_focus(self.feed_list)

        self.article_list = self.root.add_scroll_menu('Articles', 0, 3, row_span=2, column_span=5)
        self.article_read = self.root.add_text_block("Article", 2, 0, row_span=7, column_span=8)

        self.root.set_title("NewsBetter News Reader")
        self.root.set_status_bar_text("Options: Left/Right arrow to navigate between panes, a to add new, q to quit.")

        self.feed_list.add_key_command(                  py_cui.keys.KEY_A_LOWER, self.add_new)
        self.feed_list.add_key_command(                  py_cui.keys.KEY_Q_LOWER, self.quit_now)
        self.feed_list.add_key_command(                  py_cui.keys.KEY_ENTER, self.list_articles)
        self.feed_list.add_key_command(                  py_cui.keys.KEY_RIGHT_ARROW, self.list_articles)
        self.feed_list.add_key_command(                  py_cui.keys.KEY_S_LOWER, self.toggle_summary)

        self.article_list.add_key_command(               py_cui.keys.KEY_A_LOWER, self.add_new)
        self.article_list.add_key_command(               py_cui.keys.KEY_Q_LOWER, self.quit_now)
        self.article_list.add_key_command(               py_cui.keys.KEY_LEFT_ARROW, self.back_to_feeds)
        self.article_list.add_key_command(               py_cui.keys.KEY_RIGHT_ARROW, self.read_article)
        self.article_list.add_key_command(               py_cui.keys.KEY_ENTER, self.read_article)
        self.article_list.add_key_command(               py_cui.keys.KEY_S_LOWER, self.toggle_summary)

        self.article_read.add_key_command(               py_cui.keys.KEY_CTRL_X, self.back_to_articles)
        self.article_read.add_key_command(               py_cui.keys.KEY_LEFT_ARROW, self.back_to_articles)

    def load_feeds(self):
        with open(urlfile, 'r+') as f:
            for line in f:
                (key, val) = line.split(",")
                self.d[key] = val

    def toggle_summary(self):
        if self.summary == 0:
            self.summary = 1
            self.feed_list.set_title("Source (Summary Mode On)")
        elif self.summary == 1:
            self.summary = 0
            self.feed_list.set_title("Source")


    def add_new(self):
        self.add_new_popup = self.root.show_text_box_popup("Site Name:", self.get_url)

    def get_url(self, name):
        self.load_feeds()
        if name in self.d.keys():
            self.name = name + " 2"
        else:
            self.name = name
        file_object = open(urlfile, 'a')
        file_object.write(self.name + ",")
        file_object.close()
        self.add_new_popup = self.root.show_text_box_popup("URL:", self.save_new)

    def save_new(self, entry):
        file_object = open(urlfile, 'a')
        file_object.write(entry.strip() + "\n")
        file_object.close()
        self.name = ""
        self.feed_list.clear()
        self.load_feeds()
        sources=[]
        for source in self.d:
            sources.append(source)
        self.feed_list.add_item_list(sources)
        self.root.move_focus(self.feed_list)


    def quit_now(self):
        exit()

    def list_articles(self):
        source = self.feed_list.get()
        url = self.d[source]
        self.feed = feedparser.parse(url)
        titles = []
        for j in self.feed.entries:
            titles.append(j['title'])
        self.article_list.clear()
        self.article_list.set_title(source)
        self.article_list.add_item_list(titles)
        self.root.move_focus(self.article_list)

    def back_to_articles(self):
        self.article_read.get_start_position()
        self.article_read.set_title("Article")
        self.root.move_focus(self.article_list)

    def back_to_feeds(self):
        self.article_list.clear()
        self.article_list.set_title("Articles")
        self.root.move_focus(self.feed_list)

    def read_article(self):
        
        article_title = self.article_list.get()
        try:
            for i in self.feed.entries:
                if i['title'] == article_title:
                    for x in i['links']:
                        article = Article(x.href, config=config)
                        article.download()
                        article.parse()

            text = "\nPublish Date: " + str(article.publish_date) + "\n"
            text = text + parse_article(article.text)

        except Exception as e:
            text = "sorry, this page failed to load. Please try another article. " + str(e)

        self.article_read.clear()
        self.article_read.set_text(str(text))
        self.root.move_focus(self.article_read)

def parse_article(text):
    f = open(settingsfile)
    data = json.load(f)
    f.close()
    settings = tuple(data.items())
    removeme = settings[0][1]
    removephrase = settings[1][1]

    inputtext = text.splitlines()
    output = ""
    for line in inputtext:
        if not line.startswith(tuple(removeme)) and line != "":
            for old in removephrase:
                line = line.replace(old, "")

            output = output + "\n"
            wrapped = textwrap.wrap(line, width=columns - 5, drop_whitespace=True, replace_whitespace=False)
            for newline in wrapped:
                output += newline + "\n"
    return(output)

def main():
    root = py_cui.PyCUI(9, 8)
    wrapper =  NewsbetterApp(root)
    root.start()
main()