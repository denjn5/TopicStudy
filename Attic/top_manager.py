"""
Manages the complexity of tracking subtopics



Class
# Dictionary for fast lookup
# Word (stored in orig dictionary?)
    # Word Object
        : int: Count
        :
    topic | count | subphrases:
        lemma | spaCy | count

Goal: track topics and related phrases
{topic, count, {[phr A lemma, phr A count, phr A1 start, phr A1 len, phr A2 start, phr A2 len, phr An start, phr An len]
            [phr B lemma, phr B count, phr B1 start, phr B1 len, phr B2 start, phr B2 len, phr Bn start, phr Bn len]}}

Double hierarchy will be trouble -- plus lots of re-storage.  Think graph db?

topic node [id, count]: most generic, grouped topic
usage node [start, length]: an example of when this is used in actual text
topic-usage relationship [count]


"""

import pandas as pd

class TopicManager:

    def __init__(self):

        columns = ['topic', 'count', 'headers']
        topics = pd.DataFrame(columns=columns, index=columns['topic'])

    def word_test(self):
        # check word vs. dictionary
        # if not there, add
        # if it's there, get context phrase

    def new_word(self):
        # add new word to dictionary
        #

