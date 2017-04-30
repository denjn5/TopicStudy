

# TextAnalyzer 
The goal of TextAnalyzer is to take _any_ corpus, provided it is formatted properly, and perform several types of analysis on it, then export it for visualization in d3.


## Analysis / File Summary 
|Export File|Description|Python Methods|JavaScript Methods|
|---|---|---|---|
|**Topic**|Find topics, and related phrases / texts.||  |
|**Text**|A tabular json file that contains a single entry for each Text.  |  |  |
||  |  |  |
||  |  |  |


## File Technical Definitions
### Topics-Name-Date.json
###### Summary
A _hierarchical_ json file that begins with a root node that describes the file. Children are _Topics_, grandchildren are made up of _Phrases_ which provide context for the Topics. Both Topics and Phrases contain ID references to _Text_ documents.  See below for a more detailed description.

###### File Name
The file name Topics-Name-Date.json (e.g., "Topics-Matthew-20170514.json") for this file includes 3 parts separated by dashes in the prefix that must follow this convention to be found by the UI.
1) The word "Topics", as written here.
2) The short name of the underlying data. No spaces.
3) The data date for the file (see _Meta File Definition_) expressed as YYYYMMDD (always 6 digits).

###### Meta File Definition
* **Root**. The root node contains metadata for the file and its data.
    * **name** (_str_). What's the name of the underlying corpus for this topic study? This text may be used as button text in the UI.
    * **description** (_str_). 
    * **dataDateRange** (_datetime_). What date does the data represent. May be null.
    * **runDate** (_datetime_). When was this file run?
    * **children** (_array_). Topics (described below).
* **Topics**. The top 50 topics (based on usage-count) found in the corpus 5 or more times each. These are almost always nouns, lemmatized, and stored as lower-case. Proper nouns (Named Entities) are capitalized. NOTE: We use an analytic package to recognize proper nouns, so you'll see times when a proper noun as lower-case, and vice-versa. One outcome of this is that some topics are inappropriately divided.
    * **name** (_str_). The single-word (usually) topic that was found in the underlying corpus. Name should be unique at this level across both Topics and Phrases.  It'll be used as the "index" 
    * **rank** (_int_). A numeric rank based on _count_ across the _topics_. 1 = highest rank. We use "standard competition ranking" where topics with equal count have equal rank. However, if we have 3 topics with equal rank (e.g., they are all rank 5), we'll skip 2 ranks (so the next rank will be 8, skipping 6 and 7). This simplifies showing the "top X topics" in our visualizations.
    * **count** (_int_). The number of times this lemmatized _Topic_ appears in the underlying corpus.
    * **size** (_int_). The count, less the summed sizes of its children. It's used to size nodes / slices in hierarchical visualizations.
    * **id** (_array_). A series of id's that represent the text where this _Topic_ was found.
    * **children** (_array_). Phrases (described below).
* **Phrases**. Multi-word phrases the provide context for the Topics above. Only phrases that occur 5 or more times are included. These are presented (via _verbatim_) as proper casing, but the node is built (and size calculated) based on a copy of the phrase that is lemmatized and lower-case, with spaces and punctuation removed. So the verbatim is representative only. Many instances of Topics will not be described by underlying phrases.
    * **verbatim** (_str_). A representative phrase.
    * **phrase** (_NULL_). A lemmatized and lower-case, no-spaces and no-punctuation copy of the phrase. NOTE: This is deleted before being dumped to json.
    * **size** (_int_). The number of times this lemmatized topic appears in the underlying corpus.
    * **id** (_array_). A series of id's that represent the text where this _Phrase_ was found.


### Texts-Name-Date.json
###### Summary
A tabular json file that contains a single entry for each Text.

###### File Name
The file name Texts-Name-Date.json (e.g., "Texts-Matthew-20170514.json") for this file includes 3 parts separated by dashes in the prefix that must follow this convention to be found by the UI.
1) The word "Texts", as written here.
2) The short name of the underlying data. No spaces.
3) The data date for the file (see _Meta File Definition_) expressed as YYYYMMDD (always 6 digits).

###### Meta File Definition
* **Texts**. Each "line" fully describes the underlying text. The only guaranteed field is _id_. After that, _abstract_ and _url_ will be common. Other fields are only filled out when available.  
    * **id** (_str_). A unique (for this file) reference-point for this line.
    * **author** (_str_). The author of the post.
    * **title** (_str_). The title of the post.
    * **sentiment** (_float_). A number between 0 and 1. 0 represents negative sentiment. 1 represents a positive sentiment.
    * **source** (_str_). The source for this text.  
    * **url** (_str_). The url for the source. NOTE: This is deleted before being dumped to json.
    * **fullText** (_str_). The rest of the text, less then abstract. NOTE: This is deleted before being dumped to json.
    * **html** (_str_). Pre-formed html that incorporates 

* **Root**. The root node contains metadata for the file and its data.
    * **name** (_str_). What's the name of the underlying corpus for this topic study? This text may be used as button text in the UI.
    * **description** (_str_). 
    * **dataDateRange** (_datetime_). What date does the data represent. May be null.
    * **runDate** (_datetime_). When was this file run?
    * **children** (_array_). Topics (described below).

Example: {"id": "id", "author": "author", "title": "title", "sentiment": 0.5, "source": "source", "url": "http...", "htmlCard": "<div></div>"}





# Text Analyzer
A series of helper functions to find topics in context, new important topics and sentences, and compare topics across texts, and visualize.

It's broken into 3 sets of classes:
* get_ classes retrieve a specific subject and format it for analysis (social, bible, etc.)
    -> dictionary of sources: { reference: text }
* ana_ classes take the texts and analyze them (topics, vector models)
    -> 
* viz_ classes show results
    -> graph database
    -> json 

Code example test
```javascript
function fancyAlert(arg) {
  if(arg) {
    $.facebox({div:'#foo'})
  }
}
```

```python
import get_bible
import ana_topics
import ana_factory
```

# Web Output
A web page that illustrates results



