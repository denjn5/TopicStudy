

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



