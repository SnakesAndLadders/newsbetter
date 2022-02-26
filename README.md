# NewsBetter
Yet another RSS news reader

## Just... why?
There are tons of TUI and CLI RSS readers out there ([Newsboat](https://newsboat.org/)) is one that I have used for years. The one thing I don't like is that more and more sites are putting less and less details in their rss files.  
  
There is always the option to open the page in w3m or the like, but then you have to open a completely different program and then close it to go back to the reader.  
  
## Enter NewsBetter
NewsBetter uses the [newspaper3k library](https://newspaper.readthedocs.io/en/latest/) to download and parse the article. You also have the option to get a quick summary of the article via the library's Natural Language Processing (NLP) module.

## TODO
There are a lot of features that I would like to add to this software. Among them are:
- Support for themes
- Better handling of command line arguments
- Clearing the article widget when going back to the article list. At the moment calling .clear() on the widget if you are scrolled past the first page of text causes an error.
- Add a block list function to add words and phrases that can be used to filter out specific lines of text (like "Advertisement story continues below" for example)
- Find out why summary mode does not work when installing from pip

## Install
Simply run 
```
pip3 install NewsBetter 
```
and run NewsBetter when complete (Mind the capital letters, I know it is not the standard naming but oh well).

## Usage
When inside the software the controlls are simple. 
- Press 'a' to add a new feed. 
- Use the the up and down arrows to highlight the feed you want, then press the right arrow to go to the list of articles
- Use the up and down arrows to highlight the article you want to read, them press the right arrow to read the article.
- Use the left arrow to go back.
- Press 'q' to quit anywhere except when you are reading the article. To get out of the article widget press the left arrow key or 'esc'
- Press 's' to enter summary mode anywhere except when in the article widge. This will create a quick summary of the article. Press 's' again to go back to displaying the full article (stragely this works when running the entrypoint.py file directly but does not work in the build. I am looking into it.)
