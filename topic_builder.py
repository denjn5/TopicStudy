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
        :param corpus_name: (str) The name of this corpus of texts (e.g., 20170101, Mat1)
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param max_topics: (int) What's the maximum number of topics to output to sunburst?
        :param data_date: (str: YYYY-MM-DD) The date of the data we're pulling. Simply passed through to the JSON.
            Required for the UI.
        """

        # Meta
        assert corpus_name, "corpus_name required for UI"
        # TODO: data_date assert: (a) Add beginning of string checker to pattern. (b) allow ''
        self.check_date_pattern = re.compile("20[0-9]{2}-[0-9]{2}-[0-9]{2}$")
        # assert re.match(self.check_date_pattern, data_date), "data_date must be in the form 20YY-MM-DD"

        self.corpus_name = corpus_name  # (str) The name of the set (or corpus) of texts.
        self.model_output = {'name': corpus_name,
                             'data_date': data_date,
                             'run_date': datetime.now().strftime("%Y-%m-%d %H:%M")}  # For results as json

        self.nouns = {ss.NOUN, ss.PROPN}
        self.entities = {ss.PERSON, ss.NORP, ss.FACILITY, ss.ORG, ss.GPE, ss.LOC, ss.PRODUCT, ss.EVENT, ss.WORK_OF_ART,
                         ss.LANGUAGE}

        # Settings
        self.max_topics = max_topics

        # Primary Data
        self.texts = corpus  # The passed in dict of all texts that we'll analyze
        self.summary = {}  # A dictionary that we'll create here that has summary stats
        self.topics = {}  # A dict that we'll populate with found Topics

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
            text['tokensClean'] = [str(word.lemma_).lower() for word in doc
                                   if word.is_alpha and (str(word).lower() not in self.stop_words)]

            title = self.nlp(text['title'])
            text['titleTokens'] = [word for word in title]

            # Loop through doc.  If I find a proper noun, then check if the next token is a proper noun of the same
            # entity type. If yes, merge and repeat.
            doc_len = len(doc)
            for token in doc:
                if str(token).lower() in self.known_entities and token.pos != ss.PROPN:
                    doc.ents = [(str(token).title(), doc.vocab.strings['PERSON'], token.i, token.i + 1)]

                if token.i + 1 < doc_len and token.ent_type in self.entities:
                    while token.i + 1 < doc_len and doc[token.i + 1].ent_type == token.ent_type:
                        n_gram = doc[token.i:token.i + 2]
                        n_gram.merge()
                        doc_len -= 1  # we just shrunk the list!
                        # print(x)
                if token.i + 1 >= doc_len:
                    break

            text['tokens'] = [word for word in doc]

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
                if (token.pos in self.nouns or token.ent_type in self.entities) and \
                        re.match("^[A-Za-z0-9_-]{2,}$", str(token)) and str(token) not in self.stop_words:

                    # Find Topics and Phrases
                    topic_verbatim = str(token).lower()  # this is the "verbatim" of the word
                    # TODO: Can I skip the self.known_entities check (since I fix that in a 1st pass now)?
                    topic_lemma = token.lemma_ if token.ent_type_ == '' else token.lemma_.upper()
                    self.add_topic_to_text(topic_lemma, topic_verbatim, text_id)

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
                        self.add_topic_to_text(phrase_lemma, phrase_verbatim, text_id)

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

    def add_topic_to_text(self, lemma, verbatim, text_id):
        # Found a Topic (we're confident it's a noun); record it in the Texts data store
        # We need to loop through the list of texts until we find the one where currently studying.
        # Then only proceed if we haven't already "found" the instances of this word in this text.

        # Add entry to the "found" dict for this topic_word (if it's not there already); it's a set!
        # We record lemmatized topics from our variable topic_word (e.g. run), but as we iterate through we'll
        # end up searching for it's various forms (e.g., runs, ran) in the topic_str.

        text = self.texts[text_id]

        if lemma in text['topics']:
            text['topics'][lemma].add(verbatim)
        else:
            text['topics'][lemma] = {verbatim}  # initialize set with 1st element

    def export_topics(self, data_date=""):
        """
        Save json_results variable to the Output directory.
        :param data_date: YYYY-MM-DD, the date of the data
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
                                 for child_id, child in topic['children'].items() if child['count'] > 5]

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

        if data_date:
            date = datetime.strptime(data_date, "%Y-%m-%d").strftime('%m-%d')  # from YYYY-MM-DD to MM-DD
            file_name = 'Topics-{}-{}.txt'.format(self.corpus_name, date)
        else:
            file_name = 'Topics-{}.txt'.format(self.corpus_name)

        # with open(save_location + 'topics_' + self.corpus_name + '.json', 'w') as f:
        with open(config.SAVE_DIR + file_name, 'w') as f:
            json.dump(self.model_output, f)
