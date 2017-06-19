"""
Get Bible text, complete preliminary cleaning and parsing. Format into a common dict format that's ready for analysis.
Author: David Richards
Date: June 2017
"""

import json
import re

import pandas as pd

import config


class Bible(object):
    """
    Get Bible texts for topic modeling.
    """

    def __init__(self, book):
        """
        Initialize the GetBible class. Set up common variables that are needed later in the class.
        :param book: The book for analysis. Either a Bible Book (e.g., Genesis) or "Bible"
        """
        self.texts = {}  # The dict of dicts that contains the raw text and metadata.
        self.corpus_name = book  # the requested Bible book or full Bible

    def get_texts(self, use_local_source=False, save_source=False, version='esv'):
        """
        Get a Bible chapter, book (or the whole Bible!)
        :param use_local_source: (bool) Should we use the locally saved source?
        :param save_source: (bool) Should we save the minimally processed source file.
        :param version: (str) FUTURE USE. What version of the Bible do you want to work with?
        :return: (dict) list of dictionaries that contains the text and metadata (and some empty dict entries that
            we'll fill out later.
        """
        # TODO: Implement version
        assert not (use_local_source and save_source), "Either use_local_source or save_source should be false. " \
                                                       "Doesn't sense to use the local file and save a local file."
        assert version.lower() in {"kjv", "esv"}, "I only know ESV and KJV."

        if use_local_source:
            file_name = config.SOURCE_DIR + '{}-ESV.json'.format(self.corpus_name)
            try:
                with open(file_name) as file:
                    self.texts = json.loads(file)
            except IOError:
                print("I couldn't find {}. I'll try pulling it from it's source.".format(file_name))
                use_local_source = False  # If we couldn't get source locally, get it from origin...
                save_source = True  # ...and save it for next time

        else:
            # Read raw file into pandas and get the correct selection
            df = pd.read_csv(config.INPUT_DIR + version.lower() + '.csv', sep='|')
            df['key'] = df['book'].str.lower() + '_' + df['chapter'].map(str)
            df['title'] = df['book'] + ' ' + df['chapter'].map(str)
            df['url'] = 'www.esv.org/' + df['book'] + '+' + df['chapter'].map(str)
            df['logoFile'] = 'esv.png'
            df['text'].replace(to_replace='<span[^>]+>|</span>|[''"`]', value=r'', regex=True, inplace=True)
            df['text'].str.strip().replace(to_replace='  ', value=r' ', regex=False, inplace=True)
            df.rename(columns={'book': 'source'}, inplace=True)
            del df['chapter']

            selection = df if self.corpus_name.lower() == 'bible' else df[(df['source'] == self.corpus_name)]

            # TODO: What if nothing is returned?

            # Loop through selection and turn it into a dictionary of entries (df --> dict)
            for i, row in selection.iterrows():
                self.texts[row['key']] = {"title": row['title'], "source": row['source'], "text": row['text'],
                                             "url": row['url'], "logoFile": row['logoFile']}

            # http://www.rationalgirl.com/blog/html/2013/04/15/pandas__create_dataframe.html


            if save_source:
                file_name = '{}-ESV.json'.format(self.corpus_name)
                with open(config.SOURCE_DIR + file_name, 'w') as file:
                    json.dump(self.texts, file)

                file_name = '{}-ESV.pickle'.format(self.corpus_name)
                df.to_pickle(config.SOURCE_DIR + file_name)


        return self.texts


if __name__ == "__main__":
    gt = Bible("Genesis")
    gt.get_texts()
