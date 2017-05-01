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
# FEATURE: Should I prep images for the htmlCard?

# IMPORTS
import pandas as pd
from datetime import datetime
import json
import viz_graph_db


# GLOBALS
SRC_DIR = 'Texts/'


class getBibleTexts(object):

    def __init__(self, book, chapter=""):
        self.texts = []  # a list for all of our texts
        self.book = book
        self.chapter = chapter
        self.reference = book + (('_' + str(chapter)) if chapter else '')
        self.title = book + ((' ' + str(chapter)) if chapter else '')


    def get_texts(self):
        """
        Get a Bible chapter, book (or the whole Bible!)
        :return: list of dictionaries
        """
        # READ KJV (kjv.csv) or ov.csv file
        df = pd.read_csv(SRC_DIR + 'ov.csv', sep='|')

        # GET SELECTION
        if self.book == 'bible':
            selection = df
        elif self.chapter:
            selection = df[(df['book'] == self.book) & (df['chapter'] == self.chapter)]
        else:
            selection = df[(df['book'] == self.book)]

        # Move to standard list structure
        for i, row in selection.iterrows():
            url_book_chapter = str(row['book'] + '+' + str(int(row['chapter'])))
            title = str(row['book'] + ' ' + str(int(row['chapter'])) + ':' + str(int(row['verse'])))
            text_id = str(row['book'] + '_' + str(int(row['chapter'])) + ':' + str(int(row['verse'])))
            text = row['text'].replace("'", "").replace('"', '')
            # verses[text_id] = row['text'].replace("'", "").replace('"', '')

            # {} = Matthew+1
            # {} = Matthew 1:4
            # {} = [text]
            html_card = "<div class='bs-callout'><a href='https://www.esv.org/{}/' target='_blank'>" \
                       "<img src='Libraries/esv.png?size=40' class='img' /></a><b>{}</b>. {}</div>" \
                .format(url_book_chapter, text_id, text)

            self.texts.append({"id": text_id, "author": "", "title": title, "sentiment": 0.5, "source": "",
                               "text": text, "htmlCard": html_card})

        return self.texts


    def db_add_posts(self, db_start_fresh=False):
        """
        Save each verse to the graph database.
        :param db_start_fresh: Do we delete all on graph db before starting?
        :return: 
        """
        # TODO: Add "title" to Text node.
        gt = viz_graph_db.GraphManager()

        if db_start_fresh:
            gt.delete_all()

        for text in self.texts:
            gt.text(text['id'], text['text'])
        # gt.close()


    def export_texts(self, save_location):
        file_name = 'Texts-{}-{}.json'.format(self.reference, datetime.today().strftime('%Y%m%d'))

        texts = []
        for text in self.texts:
            texts.append({"id": text['id'], "title": text['title'], "sentiment": text['sentiment'],
                         "text": text['text'], "htmlCard": text['htmlCard']})

        with open(save_location + file_name, 'w') as f:
            json.dump(texts, f)


# if __name__ == "__main__":
#     main("psa 23")
