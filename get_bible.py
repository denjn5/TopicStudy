"""
Get Bible text, complete preliminary cleaning and parsing. Format into a common dict format that's ready for analysis.
Author: David Richards
Date: June 2017
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

        if not use_local_source:
            # Read raw file into pandas
            df = pd.read_csv(config.INPUT_DIR + version.lower() + '.csv', sep='|')

            # Get book that user requested
            if self.corpus_name == 'Bible':
                selection = df
            else:
                selection = df[(df['book'] == self.corpus_name)]
            # TODO: What if nothing is returned?

            # Loop through selection and turn it into a dictionary of entries
            for i, row in selection.iterrows():
                bk = row['book']
                ch = str(int(row['chapter']))
                # '<span[^>]+>|</span>|[''"`]' --> Looks span tags or span close or several types of quote marks
                text = re.sub(r'<span[^>]+>|</span>|[''"`]', '', row['text']).strip(' ').replace('  ', ' ')

                self.texts[bk + '_' + ch] = {"title": bk + ' ' + ch, "source": bk, "text": text,
                                             "url": 'www.esv.org/{}+{}'.format(bk, ch), "logoFile": "esv.png"}

            if save_source:
                file_name = '{}-ESV.json'.format(self.corpus_name)
                with open(config.SOURCE_DIR + file_name, 'w') as file:
                    json.dump(self.texts, file)

        return self.texts


if __name__ == "__main__":
    gt = GetBible("Genesis")
    gt.get_texts()
    gt.export_texts()
