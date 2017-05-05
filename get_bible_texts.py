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
import json
import graph_database

# GLOBALS
SRC_DIR = 'Data/'
SAVE_DIR = 'Output/'

HTML_CARD = "<div class='card bs-callout {card_sent}'><div class='cardTime'>{time}</div>" \
            "<img src='{logo_path}' height=40 class='cardImage' />" \
            "<div class='cardTitle'><a href='{url}' target='_blank'><b>{card_title}</b></a></div>" \
            "<div class='cardText'>{card_text}</div>"


class getBibleTexts(object):
    def __init__(self, book, chapter=""):
        """
        
        :param book: The book for analysis. Either a Bible Book (e.g., Genesis) or "Bible"
        :param chapter: An optional chapter reference
        """
        self.texts = []  # a list of dictionaries; each item contains one verse with its attributes
        # TODO: Should a text really be a chapter? That'd simplify large block compares. And let me test highlites.
        self.book = book  # the requested Bible book or full Bible
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
            url_book_chapter = row['book'] + '+' + str(int(row['chapter']))
            title = str(row['book'] + ' ' + str(int(row['chapter'])) + ':' + str(int(row['verse'])))
            text_id = str(row['book'] + '_' + str(int(row['chapter'])) + ':' + str(int(row['verse'])))
            text = row['text'].replace("'", "").replace('"', '')

            self.texts.append({"id": text_id, "author": "", "title": title, "sentiment": 0.5, "source": "",
                               "text": text, "textMark": text, "topics": set(), "urlBookChapter": url_book_chapter})

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

    def export_texts(self, save_location):
        file_name = 'Texts-{}.json'.format(self.reference)

        texts = []
        for text in self.texts:
            sent_class = 'bs-callout-neg' if text['sentiment'] < -0.33 else ('bs-callout-pos' if text['sentiment'] > 0.33 else '')
            html_card = HTML_CARD.format(card_sent=sent_class, time='', logo_path='Logos\esv.png', card_title=text['title'],
                                         url='https://www.esv.org/' + text['urlBookChapter'],
                                         card_text=text['textMark'])

            texts.append({"id": text['id'], "title": text['title'], "sentiment": text['sentiment'],
                          "text": text['text'], "topics": list(text['topics']), "htmlCard": html_card})

        with open(save_location + file_name, 'w') as f:
            json.dump(texts, f)

# if __name__ == "__main__":
#     main("psa 23")
