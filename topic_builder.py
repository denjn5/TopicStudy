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

# GLOBALS
NOUNS = {ss.NOUN, ss.PROPN}


class TopicBuilder(object):
    """
    Review a series of texts and extract topics (nouns), maintaining a noun-phrase link to the original texts.
    """
    nlp = spacy.load('en')

    def __init__(self, corpus_name, corpus, max_topics=40):
        """
        :param corpus_name: (str) The name of this corpus of texts (e.g., 20170101, Mat1)
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param use_graph_db: (bool) Is neo4j installed?
        """
        # Meta
        self.corpus_name = corpus_name  # (str) The name of the set (or corpus) of texts.
        # self.current_id = ""  # This is a bit of a hack. When I dive recursively into the phrases, when I get deep
        # lose the connection to the orig verse. This helps me retain it.

        # Settings
        self.max_topics = max_topics

        # Primary Data
        self.texts = corpus
        self.topics = {}  # Holds found Topics (basic tracking when graph db isn't available)
        self.model_output = {'name': corpus_name,
                             'run_date': datetime.now().strftime("%Y-%m-%d %H:%M")}  # For results as json

        # Special Words
        with open(config.SRC_DIR + 'special.txt', 'r') as file:
            self.special_words = set(file.read().split(' '))

        # Stop Words
        with open(config.SRC_DIR + 'stop_words.txt', 'r') as file:
            stop_words = set(file.read().split(' '))

        for text_id, text in self.texts.items():
            doc = self.nlp(text['text'])
            text['tokens'] = [word for word in doc]
            text['tokensClean'] = [str(word.lemma_).lower() for word in doc
                                   if word.is_alpha and (str(word).lower() not in stop_words)]


    def summarize_texts(self):
        summary = {}
        # summarized_texts['tokens'] = [token for token in text['tokens'] for text in self.texts]
        summary['text'] = ''.join([text['text'] for text_id, text in self.texts.items()])

        return summary


    def nouns(self):
        """
        Loop through each entry in texts; analyze the texts for nouns. Create a Topic dict, even if we're not doing
        a graph db.  
        :return: (dict) A dictionary of topics and counts: { topic: count }
        """

        for text_id, text in self.texts.items():
            # self.current_id = text_id  # text_id always remembers where we're at as we loop through our texts

            for token in text['tokens']:
                if token.pos in NOUNS and re.match("^[A-Za-z0-9_-]*$", str(token)):

                    # Find Topics and Phrases
                    topic_verbatim = str(token)  # this is the "verbatim" of the word
                    topic_lemma = token.lemma_ if token.ent_type_ == '' and str(token).lower() not in self.special_words \
                        else token.lemma_.upper()
                    self.add_topic_to_text(topic_lemma, topic_verbatim, text_id)

                    # Increment or add topic
                    if topic_lemma in self.topics:
                        self.topics[topic_lemma]['count'] += 1
                        self.topics[topic_lemma]['verbatims'].add(topic_verbatim)
                    else:
                        self.topics[topic_lemma] = {}
                        self.topics[topic_lemma]['name'] = topic_lemma
                        self.topics[topic_lemma]['count'] = 1
                        self.topics[topic_lemma]['verbatims'] = {topic_verbatim}  # initialize a set
                        self.topics[topic_lemma]['children'] = {}


                    subtree = list(token.subtree)
                    if len(subtree) > 1:

                        phrase_lemma = ''.join([(str(word) if word.lemma_ == '-PRON-' else word.lemma_) for word in subtree])
                        phrase_lemma = ''.join(char for char in phrase_lemma if char not in string.punctuation)
                        phrase_verbatim = ' '.join([str(word) for word in subtree])  # .replace(" ,", ",").replace(" ;", ";")
                        phrase_verbatim = phrase_verbatim.strip(string.punctuation)
                        self.add_topic_to_text(phrase_lemma, phrase_verbatim, text_id)

                        # Increment or add topic
                        if phrase_lemma in self.topics[topic_lemma]['children']:
                            self.topics[topic_lemma]['children'][phrase_lemma]['count'] += 1
                            self.topics[topic_lemma]['children'][phrase_lemma]['verbatims'].add(phrase_verbatim)
                        else:
                            self.topics[topic_lemma]['children'][phrase_lemma] = {}
                            self.topics[topic_lemma]['children'][phrase_lemma]['name'] = phrase_lemma
                            self.topics[topic_lemma]['children'][phrase_lemma]['count'] = 1
                            self.topics[topic_lemma]['children'][phrase_lemma]['verbatims'] = {phrase_verbatim}


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
        topics = [{'name': topic['name'], 'count': topic['count'], 'verbatims': list(topic['verbatims']),
                   'children': topic['children']} for topic_id, topic in self.topics.items() if topic['count'] > 5]
        topics = sorted(topics, key=lambda topic: topic['count'], reverse=True)

        rank = 1
        prev_count = 0
        for i, topic in enumerate(topics):
            current_count = topic['count']

            if current_count < prev_count:  # this topic occurs left often than the last one
                rank = i + 1
                if rank > self.max_topics:
                    break

            topic['rank'] = rank
            # Prune low-use phrases and the 'phrase' attribute
            # topic['children'] = []
            topic['children'] = [{'name': child['name'], 'count': child['count'], 'verbatims': list(child['verbatims'])}
                                 for child_id, child in topic['children'].items() if child['count'] > 5]

            topic['children'] = sorted(topic['children'], key=lambda lemma: lemma['count'], reverse=True)

            child_count = 0
            for child in topic['children']:
                child['rank'] = rank
                child['size'] = child['count']
                child_count += child['size']

            topic['size'] = topic['count'] - child_count
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
