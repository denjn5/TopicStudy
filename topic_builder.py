"""
Review a series of texts and extract and group topics (nouns), maintaining a noun-phrase link to the original text.

Explains POS Tags: http://universaldependencies.org/en/pos/all.html#al-en-pos/DET
"""
# FEATURE: Add anaphora resolution (Hobbs on spaCy?)
# TODO: Create a "this matters" topic highlighter (min threshold).

# IMPORTS
import spacy
import spacy.symbols as ss
import re
import string
import json
from datetime import datetime
import config


class TopicBuilder(object):
    """
    Review a series of texts and extract topics (nouns), maintaining a noun-phrase link to the original texts.
    """
    nlp = spacy.load('en')

    def __init__(self, corpus_name, corpus, max_topics=40, data_date=''):
        """
        :param corpus_name: (str) A short (between 4 and 20 characters) human-readable name for this corpus of texts.
            It will show up in the UI and help us pass the file back-and-forth.
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param max_topics: (int) What's the maximum number of topics to output to sunburst?
        :param data_date: (str: YYYY-MM-DD) The date of the data we're pulling. Passed through to the JSON.
            Required for the UI.
        """

        # Test Patters and sets for use later in our topic model
        # Match letters, numbers, spaces, underscores, and dashes. Ignore case. Must be 2 or more characters in length.
        self.phrase_pattern = re.compile('^[a-z0-9 _-]{2,}$', re.IGNORECASE)
        self.date_pattern = re.compile('20[0-9]{2}-[0-1][0-9]-[0-3][0-9]$')
        self.nouns = {ss.NOUN, ss.PROPN}
        self.entities = {ss.PERSON, ss.NORP, ss.FACILITY, ss.ORG, ss.GPE, ss.LOC, ss.PRODUCT, ss.EVENT, ss.WORK_OF_ART,
                         ss.LANGUAGE}

        # Check the user arguments
        assert 3 < len(corpus_name) < 21 and re.match(self.phrase_pattern, corpus_name), \
            'A corpus_name (between 4 and 20 characters; made of letters, numbers, underscores, or dashes) is required.'
        assert data_date == '' or re.match(self.date_pattern, data_date), \
            'If you include a data_date, it must match the form 20YY-MM-DD.'
        assert type(corpus) is dict, 'The corpus must be a dictionary.'
        assert type(max_topics) is int, 'The max_topics must be an integer.'

        # Topic metadata & settings
        self.corpus_name = corpus_name.replace(' ', '')  # (str) The name of the set (or corpus) of texts.
        self.max_topics = max_topics
        self.data_date = data_date
        self.model_output = {'name': corpus_name,
                             'data_date': data_date,
                             'run_date': datetime.now().strftime("%Y-%m-%d %H:%M")}  # For results as json


        # Primary Data
        self.texts = corpus  # The passed in dict of all texts that we'll analyze
        self.summary = {}  # A dictionary that we'll create here that has summary stats
        self.topics = {}  # A dict that we'll populate with found Topics

        self._tokenize()

    def _tokenize(self):
        """
        Create spaCy token lists from the original text strings from self.texts['text']. 
        :return: 
        """

        # Get known entities
        try:
            with open(config.SRC_DIR + 'known_entities.txt', 'r') as file:
                self.known_entities = set(file.read().split(' '))
        except IOError:
            print('Add a text file named "known_entities.txt" that lists named entities (space-delimited) that we '
                  'want to be sure are treated as proper nouns.')
            self.known_entities = set()

        # Stop Words
        try:
            with open(config.SRC_DIR + 'stop_words.txt', 'r') as file:
                self.stop_words = set(file.read().split(' '))
        except IOError:
            print('Add a text file named "stop_words.txt" that lists common words (space-delimited) that we should '
                  'ignore in most text processing.')
            self.stop_words = set()

        # Loop through texts looking for important known entities and entity n-grams
        for text_id, text in self.texts.items():
            doc = self.nlp(text['text'])

            # Loop through tokens and find known entities aren't already marked
            for token in doc:
                # Is this word in our known_entities, but is not recognized by the spaCy parser?
                if str(token).lower() in self.known_entities and token.ent_type not in self.entities:
                    # We need to set the new entity to doc.ents directly (I believe the getter for doc.ents does
                    #     some important massaging.  However, counter to the online docs, setting doc.ents wipes out
                    #     all of the previously recognized ents, so we stash the value, then we combine and reset.
                    stash = doc.ents
                    doc.ents = [(str(token).title(), doc.vocab.strings['PERSON'], token.i, token.i + 1)]
                    doc.ents = doc.ents + stash

            # Find proper noun n-grams: (a) find a known entity, (b) is the next word also a known entity?,
            #   (c) merge, (d) repeat
            doc_len = len(doc)  # Helps us know when to exit the 'for loop' (since we change the # of items via merge)
            for token in doc:
                if token.i + 1 < doc_len and token.ent_type in self.entities:
                    while token.i + 1 < doc_len and doc[token.i + 1].ent_type == token.ent_type:
                        n_gram = doc[token.i:token.i + 2]
                        n_gram.merge()
                        doc_len -= 1  # the merge changes the list length, so we just shrunk the list!
                        # print(x)
                if token.i + 1 >= doc_len:
                    break

            text['tokens'] = [word for word in doc]
            text['tokensClean'] = [str(word.lemma_).lower() for word in doc
                                   if word.is_alpha and (str(word).lower() not in self.stop_words)]

            title = self.nlp(text['title'])
            text['titleTokens'] = [word for word in title]

    def summarize_texts(self):
        """
        Add an entry to the summary dict that contains all texts.
        :return: Return the summary dict.
        """
        summary = {'text': ''.join([text['text'] for text_id, text in self.texts.items()])}

        return summary

    def topic_finder(self, include_titles=False):
        """
        Loop through each entry in texts; analyze the texts for nouns. Create a Topic dict, even if we're not doing
        a graph db.  
        :return: (dict) A dictionary of topics and counts: { topic: count }
        """

        for text_id, text in self.texts.items():
            # self.current_id = text_id  # text_id always remembers where we're at as we loop through our texts

            for token in text['tokens']:
                # "^[A-Za-z0-9_ -]{2,}$" --> whole word is (a) made up of letters, numbers, spaces, underscores, and
                #   hyphens, and (b) is 2 letters or longer.

                # We should only go beyond this point if this token is a noun or known entity, contains only vanilla
                # characters (letters, numbers), and is *not* in our stop_words list.
                if (token.pos not in self.nouns and token.ent_type not in self.entities) or \
                        not self.phrase_pattern.match(str(token)) or str(token) in self.stop_words:
                    continue

                # Find Topics and Phrases
                topic_verbatim = str(token).lower()  # this is the "verbatim" of the word
                topic_lemma = token.lemma_
                if token.pos == ss.PROPN or token.ent_type in self.entities:
                    topic_lemma = topic_lemma.upper()

                # Increment or add topic
                if topic_lemma in self.topics:
                    self.topics[topic_lemma]['count'] += 1
                    self.topics[topic_lemma]['verbatims'].add(topic_verbatim)
                    self.topics[topic_lemma]['textIDs'].add(text_id)
                else:
                    self.topics[topic_lemma] = {}
                    self.topics[topic_lemma]['name'] = topic_lemma
                    self.topics[topic_lemma]['count'] = 1
                    self.topics[topic_lemma]['verbatims'] = {topic_verbatim}  # initialize a set
                    self.topics[topic_lemma]['textIDs'] = {text_id}
                    self.topics[topic_lemma]['children'] = {}

                subtree = list(token.subtree)
                if len(subtree) > 1:

                    phrase_lemma = ''.join(
                        [(str(word) if word.lemma_ == '-PRON-' else word.lemma_) for word in subtree])
                    phrase_lemma = ''.join(char for char in phrase_lemma if char not in string.punctuation)
                    phrase_lemma = phrase_lemma.lower().strip(' ')
                    phrase_verbatim = ' '.join(
                        [str(word) for word in subtree])  # .replace(" ,", ",").replace(" ;", ";")
                    phrase_verbatim = phrase_verbatim.strip(string.punctuation).lower().strip(' ')

                    # Increment or add topic
                    if phrase_lemma in self.topics[topic_lemma]['children']:
                        self.topics[topic_lemma]['children'][phrase_lemma]['count'] += 1
                        self.topics[topic_lemma]['children'][phrase_lemma]['verbatims'].add(phrase_verbatim)
                        self.topics[topic_lemma]['children'][phrase_lemma]['textIDs'].add(text_id)
                    else:
                        self.topics[topic_lemma]['children'][phrase_lemma] = {}
                        self.topics[topic_lemma]['children'][phrase_lemma]['name'] = phrase_lemma
                        self.topics[topic_lemma]['children'][phrase_lemma]['count'] = 1
                        self.topics[topic_lemma]['children'][phrase_lemma]['verbatims'] = {phrase_verbatim}
                        self.topics[topic_lemma]['children'][phrase_lemma]['textIDs'] = {text_id}


    def export_topics(self):
        """
        Save topics to Topics-XYZ.txt in the Output directory.  Along the way we'll sort, rank, recalculate at least
        on field for the UI, and prune the dataset (dropping low-usage topics).
        :return: 
        """

        # format as a json-style list with name, size, rank (prepping for sunburst viz).
        topics = [{'name': topic['name'], 'count': topic['count'],
                   'verbatims': list(topic['verbatims']), 'textIDs': list(topic['textIDs']),
                   'textCount': len(list(topic['textIDs'])),
                   'children': topic['children']} for topic_id, topic in self.topics.items() if topic['count'] > 5]
        topics = sorted(topics, key=lambda topic: topic['textCount'], reverse=True)

        rank = 1
        prev_count = 0
        for i, topic in enumerate(topics):
            current_count = topic['textCount']

            if current_count < prev_count:  # this topic occurs left often than the last one
                rank = i + 1
                if rank > self.max_topics:
                    break

            topic['rank'] = rank
            # Prune low-use phrases and the 'phrase' attribute
            # topic['children'] = []
            topic['children'] = [{'name': child['name'], 'count': child['count'],
                                  'verbatims': list(child['verbatims']), 'textIDs': list(child['textIDs']),
                                  'textCount': len(list(child['textIDs']))}
                                 for child_id, child in topic['children'].items() if child['count'] > 3]

            topic['children'] = sorted(topic['children'], key=lambda lemma: lemma['textCount'], reverse=True)

            child_count = 0
            for child in topic['children']:
                child['rank'] = rank
                child['size'] = child['textCount']
                child_count += child['size']

            topic['size'] = topic['textCount'] - child_count if topic['textCount'] >= child_count else 0
            prev_count = current_count

        # Prune topics over max_topics (default ~40): we stopped calc'ing rank over the max_topics
        self.model_output["children"] = [topic for topic in topics if 'rank' in topic]

        if self.data_date:
            date = datetime.strptime(self.data_date, "%Y-%m-%d").strftime('%d')  # from YYYY-MM-DD to DD
            file_name = 'Topics-{}-{}.txt'.format(self.corpus_name, date)
        else:
            file_name = 'Topics-{}.txt'.format(self.corpus_name)

        # with open(save_location + 'topics_' + self.corpus_name + '.json', 'w') as f:
        with open(config.SAVE_DIR + file_name, 'w') as file:
            json.dump(self.model_output, file)
