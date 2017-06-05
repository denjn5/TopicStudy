"""
Purpose: Get Bible text, complete preliminary cleaning and parsing.
Build requirements: 
* main() takes arguments necessary to pull the corpus, gets corpus, and returns 
    * a list of dicts in the following form: {"id": "id", "author": "author", "title": "title", "sentiment": 0.5, 
        "source": "source", "url": "http...", "htmlCard": "<div></div>"}
* export_texts(texts, save_directory) takes the list of dicts created above and the directory location and dumps / saves
    it as a json file.
* db_add_posts() is an optional function that takes the returned object from main() and saves it to a dictionary.
"""

import json
import re

import pandas as pd

import config


class GetBible(object):
    """
    Get Bible texts for topic modeling.
    """

    def __init__(self, book):
        """
        Get texts from text file and prepare for analysis.
        :param book: The book for analysis. Either a Bible Book (e.g., Genesis) or "Bible"
        """
        self.texts = {}
        self.corpus_name = book  # the requested Bible book or full Bible

        self.html_card = "<div class='card bs-callout {card_sent}' id='card_{id}'>" \
                         "<div class='cardTime'>{time}</div>" \
                         "<a href='{url}' target='_blank'><img src='{logo_path}' class='cardImage' /></a>" \
                         "<div class='cardTitle h4'>" \
                         "<a href='javascript:void(0);' onclick='cardToggle({id})'>{card_title}</a></div>" \
                         "<a href='javascript:void(0);' onclick='cardToggle({id})'>" \
                         "<i class='fa fa-minus-square-o fa-lg cardToggle'></i></a>" \
                         "<div class='cardText' id='text_{id}'>{card_text}</div>" \
                         "</div>"

    def get_texts(self, use_local_source=False, save_source=False, version=''):
        """
        Get a Bible chapter, book (or the whole Bible!)
        :return: list of dictionaries
        """
        assert not(use_local_source and save_source), "Either use_local_source or save_source should be false. Doesn't " \
                                                 "sense to use the local file and then save right back over it."

        if use_local_source:
            file_name = config.SOURCE_DIR + 'ESV-{}.json'.format(self.corpus_name)
            try:
                with open(file_name) as file:
                    self.texts = json.loads(file)
            except IOError:
                print("I couldn't find {}. I'll try pulling it from it's source.".format(file_name))
                use_local_source = False

        if not use_local_source:
            # READ KJV (kjv.csv) or ov.csv file
            df = pd.read_csv(config.INPUT_DIR + 'ovbc.csv', sep='|')

            # GET SELECTION
            if self.corpus_name == 'Bible':
                selection = df
            else:
                selection = df[(df['book'] == self.corpus_name)]

            # Move to standard list structure
            for i, row in selection.iterrows():
                bk = row['book']
                ch = str(int(row['chapter']))
                # '<span[^>]+>|</span>|[''"`]' --> Looks span tags or span close or several types of quote marks
                text = re.sub(r'<span[^>]+>|</span>|[''"`]', '', row['text']).strip(' ').replace('  ', ' ')

                self.texts[bk + '_' + ch] = {"author": "", "title": bk + ' ' + ch, "sentiment": 0, "source": bk,
                                             "text": text, "topics": {}, "tokens": "", "tokensClean": "",
                                             "titleTokens": "", "urlQueryString": bk + '+' + ch}

            if save_source:
                file_name = 'ESV-{}.json'.format(self.corpus_name)
                with open(config.SOURCE_DIR + file_name, 'w') as file:
                    json.dump(self.texts, file)

        return self.texts

    def export_texts(self):
        """
        Gets raw texts list ready for save by creating the htmlCard and jettisoning fields that we no longer need.
        NOTE: Assumes that we've already populated **sentiment** and **topics** (outside of this class).
        :return: None
        """

        save_texts = []
        for text_id, text in self.texts.items():
            sent_class = 'bs-callout-neg' if text['sentiment'] < -0.33 else ('bs-callout-pos'
                                                                             if text['sentiment'] > 0.33 else '')
            html_card = self.html_card.format(id=text_id, card_sent=sent_class, time='', logo_path='Logos\esv.png',
                                              card_title=text['title'],
                                              url='https://www.esv.org/' + text['urlQueryString'],
                                              card_text=text['text'])

            topics = {k: list(v) for k, v in text['topics'].items()}  # turn dict sets into dict lists

            save_texts.append({"id": text_id, "title": text['title'], "sentiment": text['sentiment'],
                               "text": text['text'], "topics": topics, "htmlCard": html_card})

        file_name = 'Texts-{}.txt'.format(self.corpus_name)
        with open(config.OUTPUT_DIR + file_name, 'w') as file:
            json.dump(save_texts, file)

# if __name__ == "__main__":
#     main("psa 23")
