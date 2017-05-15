"""
Purpose: Get bible text, complete preliminary cleaning and parsing. 
Build requirements: 
* main() takes arguments necessary to pull the corpus, gets corpus, and returns 
    * a list of dicts in the following form: {"id": "id", "author": "author", "title": "title", "sentiment": 0.5, 
        "source": "source", "url": "http...", "htmlCard": "<div></div>"}
* export_texts(texts, save_directory) takes the list of dicts created above and the directory location and dumps / saves
    it as a json file.
* db_add_posts() is an optional function that takes the returned object from main() and saves it to a dictionary.

Text parsing work:
1) Remove all quotes (', ")
2) htmlCard --> 
    <a href='https://reddit.com/' target='_blank'>
        <img src='//logo.clearbit.com/reddit.com?size=40' class='img' /></a>
    <b>Title</b>. The first 30 words of the article<a href='#' class='textToggle' id='1'>...</a>
    <span style='display: none' id='1t'>The 'rest' of the article here.</span>

"""

# FEATURE: Can I run a compare of all chapters in the Bible to see which ones have the greatest overlap?

# IMPORTS
import re
import pandas as pd
import json
import graph_database
import config

# GLOBALS
HTML_CARD = "<div class='card bs-callout {card_sent}' id='card_{id}'>" \
            "   <div class='cardTime'>{time}</div>" \
            "   <a href='{url}' target='_blank'><img src='{logo_path}' class='cardImage' /></a>" \
            "   <div class='cardTitle h4'><a href='javascript:void(0);' onclick='cardToggle({id})'>{card_title}</a></div>" \
            "   <a href='javascript:void(0);' onclick='cardToggle({id})'>" \
            "       <i class='fa fa-minus-square-o fa-lg cardToggle'></i></a>" \
            "   <div class='cardText' id='text_{id}'>{card_text}</div>" \
            "</div>"


class getBibleTexts(object):
    def __init__(self, book):
        """
        Get texts from text file and prepare for analysis.
        :param book: The book for analysis. Either a Bible Book (e.g., Genesis) or "Bible"
        """
        self.texts = {}
        self.corpus_name = book  # the requested Bible book or full Bible

    def get_texts(self):
        """
        Get a Bible chapter, book (or the whole Bible!)
        :return: list of dictionaries
        """
        # READ KJV (kjv.csv) or ov.csv file
        df = pd.read_csv(config.SRC_DIR + 'ovbc.csv', sep='|')

        # GET SELECTION
        if self.corpus_name == 'bible':
            selection = df
        else:
            selection = df[(df['book'] == self.corpus_name)]

        # Move to standard list structure
        for i, row in selection.iterrows():
            bk = row['book']
            ch = str(int(row['chapter']))
            # TODO: Put more of our replace in the regex? .replace may be faster, but we doing multiple passes...
            text = re.sub(r'<span[^>]+>|</span>', '', row['text'])
            text = text.replace("'", "").replace('"', '').replace('  ', ' ')

            self.texts[str(i)] = {"author": "", "title": bk + ' ' + ch, "sentiment": 0, "source": "",
                                    "text": text, "topics": {}, "tokens": "", "tokensClean": "",
                                    "titleTokens": "", "urlQueryString": bk + '+' + ch}


        return self.texts

    def db_add_posts(self, db_start_fresh=False):
        """
        Save each verse to the graph database.
        :param db_start_fresh: Do we delete all on graph db before starting?
        :return: 
        """
        # TODO: Add "title" to Text node.
        gt = graph_database.GraphManager()

        if db_start_fresh:
            gt.delete_all()

        for text in self.texts:
            gt.text(text['id'], text['text'])
            # gt.close()

    def export_texts(self):
        """
        Gets raw texts list ready for save by creating the htmlCard and jettisoning fields that we no longer need.
        NOTE: Assumes that we've already populated **sentiment** and **topics** (outside of this class).
        :return: None
        """
        file_name = 'Texts-{}.txt'.format(self.corpus_name)

        save_texts = []
        for text_id, text in self.texts.items():
            sent_class = 'bs-callout-neg' if text['sentiment'] < -0.33 else ('bs-callout-pos'
                                                                             if text['sentiment'] > 0.33 else '')
            html_card = HTML_CARD.format(id=text_id, card_sent=sent_class, time='', logo_path='Logos\esv.png',
                                         card_title=text['title'], url='https://www.esv.org/' + text['urlQueryString'],
                                         card_text=text['text'])

            topics = {k: list(v) for k, v in text['topics'].items()}  # turn dict sets into dict lists

            save_texts.append({"id": text_id, "title": text['title'], "sentiment": text['sentiment'],
                               "text": text['text'], "topics": topics, "htmlCard": html_card})



        with open(config.SAVE_DIR + file_name, 'w') as f:
            json.dump(save_texts, f)

# if __name__ == "__main__":
#     main("psa 23")
