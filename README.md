# NewsBetter
Yet another RSS news reader

## Just... why?
There are tons of TUI and CLI RSS readers out there ([Newsboat](https://newsboat.org/)) is one that I have used for years. The one thing I don't like is that more and more sites are putting less and less details in their rss files.  
  
There is always the option to open the page in w3m or the like, but then you have to open a completely different program and then close it to go back to the reader.  
  
## Enter NewsBetter
NewsBetter uses the [Mozilla Readability](https://pypi.org/project/python-readability/) library to parse the article from its main URL, instead of only loading the summary from the RSS feed. This allows you to see the whole article and not the filler, just like using Reader View in Firefox!  

## TODO
There are a lot of features that I would like to add to this software. Among them are:
- Currently you can't remove a feed, I am going to fix that. For now edit your [Home Folder] -> .nbfeeds.json file to remove entries
- Update this README with current information. Installation is the same but everything has been reworked. See release notes.
- Add option to save article in Markdown format to a local file, allowing users to archive articles for offline reading.
- Add option to export to Joplin using Jopin Web Clipper API, allowing users to save articles directly to their Joplin note-taking app.
- Add support for other note taking APIs.
- Add option to get an AI summary of the article using whatever AI service they like, local or cloud-based.

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
