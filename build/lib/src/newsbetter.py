#!/usr/bin/env python3
import os
import textwrap
import sys
from pathlib import Path
import py_cui
import feedparser
from newspaper import Article

myfile = Path('urls')
myfile.touch(exist_ok=True)

class NewsBetter:

    def __init__(self, root: py_cui.PyCUI):
        self.root = root
        self.feed = ""
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
        self.article_list.add_key_command(               py_cui.keys.KEY_A_LOWER, self.add_new)
        self.article_list.add_key_command(               py_cui.keys.KEY_Q_LOWER, self.quit_now)
        self.article_list.add_key_command(               py_cui.keys.KEY_LEFT_ARROW, self.back_to_feeds)
        self.article_list.add_key_command(               py_cui.keys.KEY_RIGHT_ARROW, self.read_article)
        self.article_list.add_key_command(               py_cui.keys.KEY_ENTER, self.read_article)
        self.article_read.add_key_command(               py_cui.keys.KEY_CTRL_X, self.back_to_articles)
        self.article_read.add_key_command(               py_cui.keys.KEY_LEFT_ARROW, self.back_to_articles)

    def load_feeds(self):
        with open('urls', 'r+') as f:
            for line in f:
                (key, val) = line.split(",")
                self.d[key] = val

    def add_new(self):
        self.add_new_popup = self.root.show_text_box_popup("Site Name:", self.get_url)

    def get_url(self, name):
        self.load_feeds()
        if name in self.d.keys():
            self.name = name + " 2"
        else:
            self.name = name
        file_object = open('urls', 'a')
        file_object.write(self.name + ",")
        file_object.close()
        self.add_new_popup = self.root.show_text_box_popup("URL:", self.save_new)

    def save_new(self, entry):
        #entry = self.add_new_popup.get()
        file_object = open('urls', 'a')
        file_object.write(entry + "\n")
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
        # self.article_read.clear()
        # self.root.forget_widget(self.article_read)
        self.article_read.set_title("Article")
        self.root.move_focus(self.article_list)

    def back_to_feeds(self):
        self.article_list.clear()
        self.article_list.set_title("Articles")
        self.root.move_focus(self.feed_list)

    def read_article(self):
        # self.article_read = self.root.add_text_block("Article", 2, 0, row_span=7, column_span=8)
        columns, rows = os.get_terminal_size(0)
        article_title = self.article_list.get()
        try:
            for i in self.feed.entries:
                if i['title'] == article_title:
                 for x in i['links']:
                     article = Article(x.href)
                     article.download()
                     article.parse()
            try:
                if sys.argv[1] == "summary":
                    try:
                        article.nlp()
                        text_wrap = textwrap.wrap(article.summary, width=columns - 5, drop_whitespace=False, replace_whitespace=False)
                        self.article_read.set_title(article_title + " (Summary) CTRL-x to return to articles")
                    except:
                        text_wrap = textwrap.wrap(article.text, width=columns - 5, drop_whitespace=False, replace_whitespace=False)
                        self.article_read.set_title(article_title + " (Summary not available) CTRL-x to return to articles")
            except:
                text_wrap = textwrap.wrap(article.text, width=columns - 5, drop_whitespace=False, replace_whitespace=False)
                self.article_read.set_title(article_title)

            text = "\nPublish Date: " + str(article.publish_date) + "\n"
            #word_filter = ["Advertisement ", "advertisement has not loaded ", "We apologize, ", "video has failed ", "tap here to see"]
            # word_filter2 = "advertisement has not loaded "
            for text_line in text_wrap:
                #for entry in word_filter:
                    #if entry not in text_line:
                text += text_line.rstrip() + "\n"

        except Exception as e:
            text = "sorry, this page failed to load. Please try another article. " + str(e)

       
        self.article_read.clear()
        # self.article_read.set_title(article_title)
        self.article_read.set_text(str(text))
        self.root.move_focus(self.article_read)

# Create CUI object, pass to wrapper class, and start the CUI
root = py_cui.PyCUI(9, 8)
wrapper = NewsBetter(root)
root.start()
