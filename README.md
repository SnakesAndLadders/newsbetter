# NewsBetter
Yet another RSS news reader

## Just... why?
There are tons of TUI and CLI RSS readers out there [Newsboat](https://newsboat.org/) is one that I have used for years. The one thing I don't like is that more and more sites are putting less and less details in their rss files.  
  
There is always the option to open the page in w3m or the like, but then you have to open a completely different program and then close it to go back to the reader.  
  
## Enter NewsBetter
NewsBetter uses the [Mozilla Readability](https://pypi.org/project/python-readability/) library to parse the article from its main URL, instead of only loading the summary from the RSS feed. This allows you to see the whole article and not the filler, just like using Reader View in Firefox! Built on the [Textual](https://textual.textualize.io/) framework so it supports theming, mouse navigation, and low resource usage.

My goal is to make the navigation as quick and painless as possible. There is no offline caching or sync procedures. When you highlight a feed it refreshes it on the fly, the same when navigating articles. the Readability library is extremely fast so there is very little wait time.
  
### AI Disclaimer
I am building this by hand, and I am using some LLM assistance. This is not "Vibe Coded". I am only using AI (in this case Gemini) for code hints and troubleshooting. I review every line of code and run all tests myself. That being said I am a hobbyist. If you see anything I can improve please submit an issue.

## Features
- Fast navigation.
- Read the full article text without most of the extra junk.
- Extremely fast loading articles.
- Full mouse support, even over SSH!
- Summary page to quickly distill article information using [Sumy](https://github.com/miso-belica/sumy) with LexRank. It is a fast, efficient way to summarize locally without relying on an LLM, though it's not perfect.

## TODO
### Fixes
- Hide the export function behind a settings file, so you only need to configure one exporter and the option to export will not show in the shortcuts menu unless it is configured and selected. Barring that, bring up the settings menu if the export key is used and no exporter is enabled.

### Features
- Add option to save article in Markdown format to a local file, allowing users to archive articles for offline reading.
- Add support for other note taking APIs like [Obsidian](https://obsidian.md/) or [Logseq](https://logseq.com/).
- For those that prefer to use an LLM I would like to add an option to get an AI summary of the article using whatever LLM they like, local or cloud-based. 

## Install
Simply run 
```
pip3 install NewsBetter 
```
and run "newsbetter" when complete 

## Usage
### Controls
- Press the down arrow and then enter to select your feed. The feed will load automatically and move you into the article list. Hit enter to load the article.
- Use the right and left arrows to navigate
- Press 'a' to add a feed, and 'd' to delete the selected feed
- Press 's' for a summary of the current article. It will open in a new window.
### Joplin Export
When an article is loaded you can press 'j' to export the article to Joplin Web Cliiper (assuming it is running on the local machine)
- Enable the [Web Clipper Service](https://joplinapp.org/help/apps/clipper/)
- After it is enabled go to Advanced options (in the Web Clipper options) and generate an authorization token
- Load an article and press 'j'
- Paste that token into the 'Joplin Token' field
- Go back to Joplin and create a folder to clip articles to (or use and existing folder if you like) it can be a sub-folder as well
- Right click the folder and select 'Copy Notebook ID'
- Paste that into the 'Notebook ID' field 
- Hit the 'Save to Joplin' button and you are done!
