"""
Get Bible text, complete preliminary cleaning and parsing. Format into a common dict format that's ready for analysis.
Author: David Richards
Date: June 2017
"""

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
        # self.df_texts = None  # Will hold a pandas dataframe of our selection

    def __len__(self):
        """
        How many entries are in self.texts?
        :return:
        """
        return len(self.texts)

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
            file_name = config.SOURCE_DIR + '{}-ESV.pkl'.format(self.corpus_name)
            df = None

            try:
                df = pd.read_pickle(file_name)

                # file_name = config.SOURCE_DIR + '{}-ESV.json'.format(self.corpus_name)
                # with open(file_name) as file:
                #     self.texts = json.loads(file)
            except IOError:
                print("I couldn't find {}. I'll try pulling it from it's source.".format(file_name))
                use_local_source = False  # If we couldn't get source locally, get it from origin...
                save_source = True  # ...and save it for next time

        else:
            # Create base dataframe
            columns = ['textId', 'title', 'titleDoc', 'text', 'textDoc', 'textClean', 'sentiment', 'url',
                       'logoFile', 'time', 'date', 'count']
            df = pd.DataFrame(columns=columns)

            # Read raw file into pandas and get the correct selection
            df_get = pd.read_csv(config.INPUT_DIR + version.lower() + '.csv', sep='|')
            df['textId'] = df_get['book'].str.lower() + '_' + df_get['chapter'].map(str)
            df['title'] = df_get['book'] + ' ' + df_get['chapter'].map(str)
            df['url'] = 'www.esv.org/' + df_get['book'] + '+' + df_get['chapter'].map(str)
            df['logoFile'] = 'esv.png'
            df_get['text'].replace(to_replace='<span[^>]+>|</span>|[''"`]', value=r'', regex=True, inplace=True)
            df_get['text'].str.strip().replace(to_replace='  ', value=r' ', regex=False, inplace=True)
            df['text'] = df_get['text']
            df['source'] = df_get['book']

        # We should have texts, now lets select something
        self.texts = df if self.corpus_name.lower() == 'bible' else df[(df['source'] == self.corpus_name)]

        # Loop through selection and turn it into a dictionary of entries (df --> dict)
        # for i, row in self.df_texts.iterrows():
        #     self.texts[row['textId']] = {"title": row['title'], "source": row['source'], "text": row['text'],
        #                                  "url": row['url'], "logoFile": row['logoFile']}

        if save_source:
            file_name = config.SOURCE_DIR + '{}-ESV.pkl'.format(self.corpus_name)
            df.to_pickle(file_name)

        return self.texts


if __name__ == "__main__":
    bib = Bible("Genesis")
    bib.get_texts()
