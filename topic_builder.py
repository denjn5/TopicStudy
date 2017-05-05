"""
Review a series of texts and extract and group topics (nouns), maintaining a noun-phrase link to the original text.

Explains POS Tags: http://universaldependencies.org/en/pos/all.html#al-en-pos/DET
"""
# FEATURE: Add anaphora resolution (Hobbs on spaCy?)
# TODO: Create a "this matters" topic highlighter (min threshold).

# IMPORTS
import spacy
import spacy.symbols as ss
import string
import json
from datetime import datetime
import graph_database


# GLOBALS
OUTPUT_DIR = 'Output/'
TEXTS_DIR = 'Data/'
# TODO: Re-include ss.PRON, hopefully with anaphora resolution?
NOUNS = {ss.NOUN, ss.PROPN}


class TopicBuilder(object):
    """
    Review a series of texts and extract topics (nouns), maintaining a noun-phrase link to the original texts.
    """
    nlp = spacy.load('en')

    def __init__(self, corpus_name, corpus, use_graph_db=True, max_topics=50):
        """
        :param corpus_name: (str) The name of this corpus of texts (e.g., 20170101, Mat1)
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param use_graph_db: (bool) Is neo4j installed?
        """
        # Meta
        self.corpus_name = corpus_name.replace(' ', '')  # (str) The name of the set (or corpus) of texts.
        self.text_id = ""  # This is a bit of a hack. When I dive recursively into the phrases, when I get deep
            # lose the connection to the orig verse. This helps me retain it.

        # Settings
        self.use_graph_db = use_graph_db
        self.max_topics = max_topics

        # Primary Data
        self.texts = corpus
        self.topics = []  # Holds found Topics (basic tracking when graph db isn't available)
        self.model_output = {'name': corpus_name,
                                   'run_date': datetime.now().strftime("%Y-%m-%d %H:%M")}  # For results as json

        # TODO: Unneeded?
        self.phrases = {}

        # Stop Words
        with open(TEXTS_DIR + 'stopwords.txt', 'r') as file:
            stopwords = set(file.read().split(' '))

        for text in self.texts:
            doc = self.nlp(text['text'])
            text['tokens'] = [word for word in doc]
            text['tokens_clean'] = [str(word.lemma_).lower() for word in doc
                                    if word.is_alpha and (str(word).lower() not in stopwords)]

        if use_graph_db:
            self.gt = graph_database.GraphManager(corpus_name)  # Fire up the graph database interface



    def compare(self, orig_topics, min_count=2):
        """
        Calculate 
            % overlap = (sum of topic counts that are in both orig and new) / 
                                (sum of topic counts in orig + sum of topic counts in new)
            % new topics = (sum of topic counts that are only in new) / 
                                (sum of topic counts in orig + sum of topic counts in new)
            new topics

        :param orig_topics: (dict) 
        :param min_count: (int) The minimum number of times a topic can be mentioned, but still be considered in the 
            compare logic.
        :return: 
        """
        # Keep only "significant" entries (used more than "1" time)
        # TODO: Blend with self.topics and delete current self.topics
        orig_topics_sig = {k: v for k, v in orig_topics.items() if v >= min_count}
        new_topics_sig = {k: v for k, v in self.topics if v >= min_count}

        # What Topics are in both sets?
        intersect_topics = set([t for t in new_topics_sig if t in orig_topics_sig])
        intersect_sum = sum([v for k, v in orig_topics_sig.items() if k in intersect_topics]) + \
                        sum([v for k, v in new_topics_sig.items() if k in intersect_topics])

        # New Topic relative complement: What Topics are in New set, but not in Original set.
        new_comp_topics = set([t for t in new_topics_sig if t not in orig_topics_sig])
        new_comp_sum = sum([v for k, v in new_topics_sig.items() if k in new_comp_topics])

        # General sums & proportions
        orig_sum = sum(orig_topics_sig.values())
        new_sum = sum(new_topics_sig.values())
        intersect_pct = round(intersect_sum / (orig_sum + new_sum), 3)
        new_comp_pct = round(new_comp_sum / new_sum, 3)

        # New Topic list: Topic, Count, % of Total, Comp?
        new_topics_details = sorted([[k, v, round(v / new_sum, 3), ('COMP' if k in new_comp_topics else '')]
                                     for k, v in new_topics_sig.items()], key=lambda x: x[1], reverse=True)
        intersect_topics_details = [[k, v, round(v / orig_sum, 3)]
                                    for k, v in orig_topics_sig.items() if k in intersect_topics]

        self.model_output["compare"] = {'new_topics_details': new_topics_details,
                                        'intersect_topics_details': intersect_topics_details,
                                        'new_comp_topics': [w for w in new_comp_topics], 'new_sum': new_sum,
                                        'orig_sum': orig_sum, 'intersect_pct': intersect_pct,
                                        'new_comp_pct': new_comp_pct}

    def nouns(self):
        """
        Loop through each entry in texts; analyze the texts for nouns. Create a Topic dict, even if we're not doing
        a graph db.  
        :return: (dict) A dictionary of topics and counts: { topic: count }
        """

        for text in self.texts:
            self.text_id = text['id']  # text_id always remembers where we're at as we loop through our texts

            # for reference, text in self._text_tokens_dict.items():
            skip_ahead = -1

            for token in text['tokens']:
                if token.pos in NOUNS and token.i > skip_ahead:

                    # # Capitalize NERs (named entities)
                    # topic_word = token.lemma_ if token.ent_type_ == '' else token.lemma_.upper()
                    #
                    # text['topics'].add(topic_word)  # Found a Topic. Note that in the current Text.
                    #
                    # # Loop through topics to increment
                    # found = False
                    # for topic in self.topics:
                    #     if topic['name'] == topic_word:
                    #         topic['size'] += 1
                    #         topic['count'] += 1
                    #         break
                    #
                    # if not found:
                    #     self.topics.append({'name': topic_word, 'size': 1, 'count': 1, 'children': []})
                    #
                    # # Also, add it to the graph db...


                    skip_ahead = self.analyze_phrase(token, "TEXT", skip_ahead)


    def analyze_phrase(self, token, source_type, skip_ahead, source_id=''):
        """
        Start with a token, find it's contextual phrase. Then create Topic and Phrase nodes.  Then link those 
        together with their source Text node.
        :param token: (spaCy token) A noun, pronoun, or proper noun; the topic
        :param source_type: (str) "TEXT" or "PHRASE"
        :param skip_ahead: (int) All words before this index (token.i) have been addressed; 
            avoids double-counting and loops 
        :param source_id: (str) Usually this will be the self.text_id In that case, no need to send it. However, 
            when we're being recursive, this could be the phrase that another phrase is derived from.
        :return: (int) The new skip_ahead value
        """

        # Get the subtree of the token & lemmatize current token (upper if proper noun)
        subtree = list(token.subtree)
        topic_word = token.lemma_ if token.ent_type_ == '' else token.lemma_.upper()

        # Found a Topic, note that in the Data data store
        for text in self.texts:
            if text['id'] == self.text_id:
                text['topics'].add(topic_word)
                text['textMark'] = text['textMark'].replace(str(token), "<mark class='topic_word'>" + str(token) + "</mark>")

        # If the Topic and Subtree Phrase are equal, write the Topic and link it directly to the original Text.
        if len(subtree) == 1:
            if self.use_graph_db:
                # TODO: Do we use both branches of this if statement?
                if source_type == "PHRASE":
                    self.gt.phrase_to_topic(source_id, topic_word)
                else:  # source is a TEXT
                    self.gt.text_to_topic(self.text_id, topic_word)

        # The Subtree Phrase is bigger than the Topic. Create the Phrase, then save to the db and link
        else:
            # phrase_id: a simplified representation of this phrase, used to combine similar phrases
            phrase_id = ''.join([(str(word) if word.lemma_ == '-PRON-' else word.lemma_) for word in subtree])
            phrase_id = ''.join(char for char in phrase_id if char not in string.punctuation)
            verbatim = ' '.join([str(word) for word in subtree]).replace(" ,", ",").replace(" ;", ";")
            verbatim = verbatim.strip(string.punctuation)

            # Track phrase_ids in hierarchical arrays and dictionaries (which translates nicely to json).
            found_topic = False
            for topic in self.topics:
                if topic['name'] == topic_word:
                    topic['size'] += 1
                    topic['count'] += 1

                    # Topic found! Now look for the context phrase_id (either increment the phrase_id or add it).
                    found_phrase = False
                    for phrase in topic['children']:
                        # Compare based on phrase_id, which is a genericized version of the underlying text (fewer groups)
                        if phrase['phrase_id'] == phrase_id:
                            phrase['name'] = verbatim
                            phrase['size'] += 1
                            found = True
                            break

                    if not found_phrase:
                        topic['children'].append({'name': verbatim, 'phrase_id': phrase_id, 'size': 1})

                    break  # We've found or added the phrase, stop looing

            # Didn't find the topic? No problem, add it in.
            if not found_topic:
                self.topics.append({'name': topic_word, 'size': 1, 'count': 1, 'children': []})

            if self.use_graph_db:
                self.gt.topic(topic_word)
                self.gt.corpus_to_topic(topic_word)
                self.gt.phrase(phrase_id, verbatim)
                self.gt.phrase_to_topic(phrase_id, topic_word)

                if source_type == "PHRASE":
                    self.gt.phrase_to_phrase(source_id, phrase_id)
                else:  # source is SOURCE
                    self.gt.text_to_phrase(self.text_id, phrase_id)

            # Are there additional nouns in the Subtree? Loop through them and call this method recursively.
            nouns = [word for word in subtree if word.pos in NOUNS and word.i > skip_ahead]
            for n in range(0, len(nouns)):
                if n > 0 and nouns[n].i > skip_ahead:
                    skip_ahead = self.analyze_phrase(nouns[n], "PHRASE", skip_ahead, source_id=phrase_id)

        # skip_ahead: The index of the final word addressed in the Subtree. This avoids dupe work.
        return subtree[-1].i

    def export_topics(self, save_location, date_file_name=True):
        """
        Save json_results variable to the Output directory.
        :return: 
        """

        # format as a json-style list with name, size, rank (prepping for sunburst viz).
        topics = [topic for topic in self.topics if topic['count'] > 5]
        topics = sorted(topics, key=lambda x: x['count'], reverse=True)

        rank = 1
        prev_use_count = 0
        for i, topic in enumerate(topics):
            current_use_count = topic['count']

            if current_use_count < prev_use_count:  # this topic occurs left often than the last one
                rank = i + 1
                if rank > self.max_topics:
                    break

            topic['rank'] = rank
            # Prune low-use phrases and the 'phrase' attribute
            topic['children'] = [{'name': child['name'], 'size': child['size']} for child
                                 in topic['children'] if child['size'] > 5]
            child_use_count = 0
            for child in topic['children']:
                child['rank'] = rank
                child_use_count += child['size']
            topic['size'] = topic['size'] - child_use_count
            prev_use_count = current_use_count

        self.model_output["children"] = topics

        if date_file_name:
            file_name = 'Topics-{}-{}.json'.format(self.corpus_name, datetime.today().strftime('%Y%m%d'))
        else:
            file_name = 'Topics-{}.json'.format(self.corpus_name)

        # with open(save_location + 'topics_' + self.corpus_name + '.json', 'w') as f:
        with open(save_location + file_name, 'w') as f:
            json.dump(self.model_output, f)
