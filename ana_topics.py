"""
Review a series of texts and extract and group topics (nouns), maintaining a noun-phrase link to the original text.

Explains POS Tags: http://universaldependencies.org/en/pos/all.html#al-en-pos/DET
"""
# FEATURE: Add anaphora resolution (Hobbs on spaCy?)
# TODO: Create a "this matters" topic highlighter (min threshold).
# TODO: Finish implementing graph_db_write

# IMPORTS
import spacy
import spacy.symbols as ss
import string
import json
import datetime
import viz_graph_db

# GLOBALS
OUTPUT_DIR = 'Output/'
TEXTS_DIR = 'Texts/'
# TODO: Re-include ss.PRON, hopefully with anaphora resolution?
NOUNS = {ss.NOUN, ss.PROPN}


class TopicBuilder:
    """
    Review a series of texts and extract topics (nouns), maintaining a noun-phrase link to the original texts.
    """
    nlp = spacy.load('en')

    def __init__(self, corpus_name, corpus, use_graph_db=True):
        """
        :param corpus_name: (str) The name of this corpus of texts (e.g., 20170101, Mat1)
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param use_graph_db: (bool) Is neo4j installed?
        """
        self.corpus_name = corpus_name  # (str) The name of the set (or corpus) of texts.
        self.corpus_raw = corpus            # (dict) {[reference]: [raw text sent in for analysis]}
        self.corpus_tokens = {}                # (dict) {[reference]: [spaCy tokenized texts]}
        self.corpus_clean_tokens = {}          # (dict) {[reference]: [cleaned up version of tokens]}
        self.tokens = []
        self.tokens_clean = []
        self.raw = ""                   # (str) All corpus texts, concatenated.

        self.use_graph_db = use_graph_db
        self.topics = {}  # Holds found Topics (basic tracking when graph db isn't available)
        now = datetime.datetime.now()
        self.json_results = [{'run_date': now.strftime("%Y-%m-%d %H:%M"), 'corpus_name': corpus_name}]  # For results as json

        if use_graph_db:
            self.gt = viz_graph_db.GraphManager(corpus_name)  # Fire up the graph database interface


    def tokenize(self):
        """
        Tokenize the texts that we're studying.  Build 3 class properties: raw, corpus_tokens, corpus_tokens_clean.
        :return: (dict) 
        """
        # TODO: This method creates for, maybe large, variables.  Maybe better to not to pre-create.

        # STOP WORDS
        with open(TEXTS_DIR + 'stopwords.txt', 'r') as file:
            stopwords = set(file.read().split(' '))

        for reference, text in self.corpus_raw.items():
            self.raw += text + ' '

            doc = self.nlp(text)
            self.corpus_tokens[reference] = [word for word in doc]
            self.tokens.append([word for word in doc])
            self.corpus_clean_tokens[reference] = [str(word.lemma_).lower() for word in doc
                                            if word.is_alpha and (str(word).lower() not in stopwords)]
            self.tokens_clean.append([str(word.lemma_).lower() for word in doc
                                            if word.is_alpha and (str(word).lower() not in stopwords)])

        return self.corpus_tokens


    def compare(self, orig_topics, min_count=2):
        """
        Calculate 
            shallow % overlap = ((count of topics that are in both orig and new) * 2) / 
                                (count of topics in orig + count of topics in new)
            deep % overlap = (sum of topic counts that are in both orig and new) / 
                                (sum of topic counts in orig + sum of topic counts in new)
            deep % new topics = (sum of topic counts that are only in new) / 
                                (sum of topic counts in orig + sum of topic counts in new)
            new topics

        :param orig_topics: (dict) 
        :param min_count: (int) The minimum number of times a topic can be mentioned, but still be considered in the 
            compare logic.
        :return: 
        """
        # Keep only "significant" entries (used more than "1" time)
        orig_topics_sig = {k: v for k, v in orig_topics.items() if v >= min_count}
        new_topics_sig = {k: v for k, v in self.topics.items() if v >= min_count}

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
        new_topics_expanded = sorted([[k, v, round(v / new_sum, 3), ('COMP' if k in new_comp_topics else '')]
                                      for k, v in new_topics_sig.items()], key=lambda x: x[1], reverse=True)
        intersect_topics_expanded = [[k, v, round(v / orig_sum, 3)]
                                     for k, v in orig_topics_sig.items() if k in intersect_topics]

        self.json_results.append({'new_topics_expanded': new_topics_expanded,
                                  'intersect_topics_expanded': intersect_topics_expanded,
                                  'new_comp_topics': [w for w in new_comp_topics],
                                  'new_sum': new_sum, 'orig_sum': orig_sum, 'intersect_pct': intersect_pct,
                                  'new_comp_pct': new_comp_pct})

    def find_nouns(self):
        """
        Loop through each entry in texts; analyze the texts for nouns
        :return: (dict) A dictionary of topics and counts: { topic: count }
        """

        for reference, text in self.corpus_tokens.items():
            skip_ahead = -1

            for token in text:
                if token.pos in NOUNS and token.i > skip_ahead:
                    if self.use_graph_db:
                        skip_ahead = self.analyze_phrase(token, "TEXT", reference, skip_ahead)
                    else:
                        topic = token.lemma_
                        if topic in self.topics:
                            self.topics[topic] += 1
                        else:
                            self.topics[topic] = 1

        return self.topics

    def analyze_phrase(self, token, source_type, source_key, skip_ahead):
        """
        Start with a token, find it's explanatory phrase. Then create Topic and Phrase nodes.  Then link those 
        together and to Post nodes.
        :param token: (spaCy token) A noun, pronoun, or proper noun; the topic
        :param source_type: (str) "TEXT" or "PHRASE"
        :param source_key: (str) A unique string representation of the source
        :param skip_ahead: (int) All words before this index (token.i) have been addressed; 
            avoids double-counting and loops 
        :return: (int) The new skip_ahead value
        """

        # Create Topic node and add to local dictionary; use the token lemma as the key.
        topic = token.lemma_
        self.gt.topic(topic)
        self.gt.corpus_to_topic(topic)

        # Get the subtree of the token.
        subtree = list(token.subtree)

        # If the Topic and Subtree Phrase are equal, write the topic and link it to the source.
        if len(subtree) == 1:
            if source_type == "PHRASE":
                self.gt.phrase_to_topic(source_key, topic)
            else:  # source is a TEXT
                self.gt.text_to_topic(source_key, topic)

        # The Subtree Phrase is bigger than the Topic. Create the Phrase, then save to the db and link
        else:
            phrase = ''.join([word.lemma_ for word in subtree])
            phrase = ''.join(char for char in phrase if char not in string.punctuation)
            verbatim = ' '.join([str(word) for word in subtree]).replace(" ,", ",").replace(" ;", ";")
            verbatim = verbatim.strip(string.punctuation)

            self.gt.phrase(phrase, verbatim)
            self.gt.phrase_to_topic(phrase, topic)

            if source_type == "PHRASE":
                self.gt.phrase_to_phrase(source_key, phrase)
            else:  # source is SOURCE
                self.gt.text_to_phrase(source_key, phrase)

            # Are there additional nouns in the Subtree? Loop through them and call this method recursively.
            nouns = [word for word in subtree if word.pos in NOUNS and word.i > skip_ahead]
            for n in range(0, len(nouns)):
                if n > 0 and nouns[n].i > skip_ahead:
                    skip_ahead = self.analyze_phrase(nouns[n], "PHRASE", phrase, skip_ahead)

        # skip_ahead: The index of the final word addressed in the Subtree. This avoids dupe work.
        return subtree[-1].i

    def json_export(self):
        """
        Save json_results variable to the Output directory.
        :return: 
        """
        with open(OUTPUT_DIR + 'topics_' + self.corpus_name + '.json', 'w') as f:
            json.dump(self.json_results, f)
