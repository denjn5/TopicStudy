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
import datetime
import viz_graph_db


# GLOBALS
OUTPUT_DIR = 'Output/'
TEXTS_DIR = 'Texts/'
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
        self.corpus_name = corpus_name.replace(' ', '')  # (str) The name of the set (or corpus) of texts.

        self.corpus_raw = corpus  # (dict) {[reference]: [raw text sent in for analysis]}
        self.max_topics = max_topics
        self._text_tokens_dict = {}  # (dict) {[reference]: [spaCy tokenized texts]}
        self._text_token_dict_clean = {}  # (dict) {[reference]: [cleaned up version of tokens]}
        self._text_token_concat_clean = []
        self._text_concat_raw = ""  # (str) All corpus texts, concatenated.

        self.use_graph_db = use_graph_db

        self.topics = {}  # Holds found Topics (basic tracking when graph db isn't available)
        self.viz_topics = []  # Dupe of self.topics, but fully formed for sunburst viz.
        self.viz_texts = []  # An ID driven list of the sources used in the viz (to avoid huge file size).
        self.phrases = {}

        self.model_output = {'name': corpus_name,
                                   'run_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                                   }  # For results as json

        if use_graph_db:
            self.gt = viz_graph_db.GraphManager(corpus_name)  # Fire up the graph database interface

    def text_concat_raw(self):
        """
        Concatenate all texts into a single string. (Ensure it hasn't already been built first.) Uses: 
        * gensim.summarization.keywords
        * gensim.summarization.summarize
        :return: (str) A single string with all texts: "First sentence. Second sentence."
        """

        if not self._text_concat_raw:
            for reference, text in self.corpus_raw.items():
                self._text_concat_raw += text + ' '

        return self._text_concat_raw

    def text_token_concat_clean(self):
        """
        Concatenate all texts into a single nested list. Remove stop words and any non-alpha words. Ensure it 
        hasn't already been built first. Uses: 
        * gensim.models.Word2Vec
        :return: (list) A single list of lists of tokens: [['first', 'sentence'], ['second', 'sentence']]
        """

        # Stop Words
        with open(TEXTS_DIR + 'stopwords.txt', 'r') as file:
            stopwords = set(file.read().split(' '))

        if not self._text_token_concat_clean:
            for reference, text in self.corpus_raw.items():
                doc = self.nlp(text)
                self._text_token_concat_clean.append([str(word.lemma_).lower() for word in doc
                                                      if word.is_alpha and (str(word).lower() not in stopwords)])

        return self._text_token_concat_clean

    def text_token_dict_clean(self):
        """
        Recreate dictionary. Transform strings into lemma list (strings, based on spaCy tokens). 
        Remove stop words and any non-alpha words. Uses:
        * gensim.models.Doc2Vec
        :return: (dict) References and string lists: {reference: ["first", "sentence", "second", "sentence"]}
        """

        # Stop Words
        with open(TEXTS_DIR + 'stopwords.txt', 'r') as file:
            stopwords = set(file.read().split(' '))

        if not self._text_token_dict_clean:
            for reference, text in self.corpus_raw.items():
                doc = self.nlp(text)
                self._text_token_dict_clean[reference] = [str(word.lemma_).lower() for word in doc
                                                          if word.is_alpha and (str(word).lower() not in stopwords)]

        return self._text_token_dict_clean

    def text_tokens_dict(self):
        """
        Recreate dictionary, but transform strings into token lists of spaCy tokens. Don't remove anything. Uses: 
        * [this class]: TopicStudy.find_nouns
        :return: (dict) A dictionary of references and token lists: {reference: [first, sentence, second sentence]}
        """

        if not self._text_tokens_dict:
            for reference, text in self.corpus_raw.items():
                doc = self.nlp(text)
                self._text_tokens_dict[reference] = [word for word in doc]

        return self._text_tokens_dict

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
        # TODO: Blend with self.viz_topics and delete current self.topics
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
        self.text_tokens_dict()  # creates self.corpus_tokens

        for reference, text in self._text_tokens_dict.items():
            skip_ahead = -1

            for token in text:
                if token.pos in NOUNS and token.i > skip_ahead:

                    # Capitalize NERs (named entities)
                    topic = token.lemma_ if token.ent_type_ == '' else token.lemma_.upper()

                    # Increment topics dict
                    # if topic in self.topics:
                    #     self.topics[topic] += 1
                    # else:
                    #     self.topics[topic] = 1

                    # Loop through viz_topics to increment
                    found = False
                    for viz_topic in self.viz_topics:
                        if viz_topic['name'] == topic:
                            viz_topic['size'] += 1
                            viz_topic['count'] += 1
                            viz_topic['text_ids'].append(reference)
                            break

                    if not found:
                        self.viz_topics.append({'name': topic, 'size': 1, 'count': 1, 'children': [],
                                                'text_ids': [reference]})


                    found = False
                    for viz_text in self.viz_texts:
                        if viz_text['id'] == reference:
                            found = True
                            break

                    if not found:
                        self.viz_texts.append({'id': reference, 'text': self.corpus_raw[reference],
                                               'author': '', 'sentiment': 0.5, 'title': '', 'source': ''})


                    if self.use_graph_db:
                        skip_ahead = self.analyze_phrase(token, "TEXT", reference, skip_ahead)


        # format as a json-style list with name, size, rank (prepping for sunburst viz).
        topics = [topic for topic in self.viz_topics if topic['count'] > 5]
        topics = sorted(topics, key=lambda x: x['count'], reverse=True)

        rank = 1
        prev_count = 0
        for i, topic in enumerate(topics):
            cur_count = topic['count']
            rank = i + 1 if (cur_count < prev_count) else rank
            # TODO: max rank
            topic['rank'] = rank
            # Prune low-use phrases and the 'phrase' attribute
            topic['children'] = [{'name': child['name'], 'size': child['size']} for child
                                 in topic['children'] if child['size'] > 5]
            child_count = 0
            for child in topic['children']:
                child['rank'] = rank
                child_count += child['size']
            topic['size'] = topic['size'] - child_count
            prev_count = cur_count


        phrases = sorted(self.phrases.items(), key=lambda x: x[1], reverse=True)
        phrases_out = [{"name": k, "size": v} for k, v in phrases if v > 2]

        self.model_output["children"] = topics
        # self.model_output["phrases"] = phrases_out

        return self.topics

    def analyze_phrase(self, token, source_type, source_key, skip_ahead):
        """
        Start with a token, find it's contectual phrase. Then create Topic and Phrase nodes.  Then link those 
        together and to Post nodes.
        :param token: (spaCy token) A noun, pronoun, or proper noun; the topic
        :param source_type: (str) "TEXT" or "PHRASE"
        :param source_key: (str) A unique string representation of the source
        :param skip_ahead: (int) All words before this index (token.i) have been addressed; 
            avoids double-counting and loops 
        :return: (int) The new skip_ahead value
        """

        # Create Topic node and add to local dictionary; use the token lemma as the key.
        topic = token.lemma_ if token.ent_type_ == '' else token.lemma_.upper()
        self.gt.topic(topic)
        self.gt.corpus_to_topic(topic)

        # Get the subtree of the token.
        subtree = list(token.subtree)

        # If the Topic and Subtree Phrase are equal, write the Topic and link it directly to the original Text.
        if len(subtree) == 1:
            if source_type == "PHRASE":
                self.gt.phrase_to_topic(source_key, topic)
            else:  # source is a TEXT
                self.gt.text_to_topic(source_key, topic)

        # The Subtree Phrase is bigger than the Topic. Create the Phrase, then save to the db and link
        else:
            phrase = ''.join([(str(word) if word.lemma_ == '-PRON-' else word.lemma_) for word in subtree])
            phrase = ''.join(char for char in phrase if char not in string.punctuation)
            verbatim = ' '.join([str(word) for word in subtree]).replace(" ,", ",").replace(" ;", ";")
            verbatim = verbatim.strip(string.punctuation)

            # Track phrases in dictionary
            # TODO: Redundant with graph db. But easy for analysis
            if phrase in self.phrases:
                self.phrases[phrase] += 1
            else:
                self.phrases[phrase] = 1

            # Loop through viz_topics to find the Topic
            for viz_topic in self.viz_topics:
                if viz_topic['name'] == topic:

                    # Topic found! Now either increment the phrase or add it.
                    found = False
                    for child in viz_topic['children']:
                        # Compare based on phrase, which is a genericized version of the underlying text (fewer groups)
                        if child['phrase'] == phrase:
                            child['name'] = verbatim
                            child['size'] += 1
                            found = True
                            break

                    if not found:
                        viz_topic['children'].append({'name': verbatim, 'phrase': phrase, 'size': 1})

                    break

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

    def export_json(self):
        """
        Save json_results variable to the Output directory.
        :return: 
        """
        # with open(OUTPUT_DIR + 'topics_' + self.corpus_name + '.json', 'w') as f:
        with open(OUTPUT_DIR + 'corpusATopics.json', 'w') as f:
            json.dump(self.model_output, f)
        with open(OUTPUT_DIR + 'corpusATexts.json', 'w') as f:
            json.dump(self.viz_texts, f)
