"""
Review a list of texts. Extract and group topics (nouns), and contextual ngrams.
Author: David Richards
Date: June 2017

Helpful links:
* POS Tags: http://universaldependencies.org/en/pos/all.html#al-en-pos/DET
"""

from datetime import datetime
import json
import re
import string

import spacy
import spacy.symbols as ss

import config


class TopicBuilder(object):
    """
    Review a series of texts and extract topics (nouns), maintaining a noun-phrase link to the original texts.
    """
    nlp = spacy.load('en')

    def __init__(self, corpus_name, corpus, data_date=''):
        """
        By the end of __init__ we'll have everything we need to study our texts. To get ready, we'll (a) create some
        regex expressions and sets that we'll use later in topic_builder; (b) check the input arguments to ensure
        they are "as expected" for both the class and the final UI; (c) save the arguments to variables and set up
        our primary output variables; and (d), grab a couple of files that have contents that we'll use during
        processing.

        :param corpus_name: (str) A short (3 to 20 characters) human-readable name for this corpus of texts.
            It will show up in the UI and help us pass the file back-and-forth.
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param data_date: (str: YYYY-MM-DD) The date of the data we're pulling. Passed through to the JSON.
            Required for the UI.
        """

        # Test Patterns and sets for use later in our topic model
        # '^[a-z0-9 _-]{2,}$' --> Match letters, numbers, spaces, underscores, dashes. Ignore case. Length of 2 or more.
        self.phrase_pattern = re.compile('^[a-z0-9 _-]{2,}$', re.IGNORECASE)
        self.date_pattern = re.compile('20[0-9]{2}-[0-1][0-9]-[0-3][0-9]$')
        self.punct = {p for p in string.punctuation}
        self.empty_words = {'a', 'an', 'that', 'the', 'this'}
        self.nouns = {ss.NOUN, ss.PROPN}
        self.entities = {ss.PERSON, ss.NORP, ss.FACILITY, ss.ORG, ss.GPE, ss.LOC, ss.PRODUCT, ss.EVENT, ss.WORK_OF_ART,
                         ss.LANGUAGE}  # spaCy entities that indicate a proper noun.

        # Check the user arguments
        # TODO: What data to I expect in the dictionary passed from the "get_" class?
        assert 2 < len(corpus_name) < 21 and re.match(self.phrase_pattern, corpus_name), \
            'A corpus_name (between 3 and 20 characters; made of letters, numbers, underscores, or dashes) is required.'
        assert data_date == '' or re.match(self.date_pattern, data_date), \
            'If you include a data_date, it must match the form 20YY-MM-DD.'
        assert type(corpus) is dict, 'The corpus must be a dictionary.'
        assert len(corpus) > 0, 'The corpus of texts has no data.'

        # Topic metadata & settings
        self.corpus_name = corpus_name.replace(' ', '')  # (str) The name of the set (or corpus) of texts.
        self.data_date = data_date

        # Primary Data Structures
        self.texts = corpus  # The dict of dicts that contains all of our texts for analysis: {text_id: {}}
        self.topics = {}  # A dict of dicts for primary topics: {topic: {}}
        self.ngrams = {}  # A dict of dicts for ngrams that will help us understand primary topics: {ngram_lemma: {}}
        self.model_output = {'name': corpus_name,
                             'dataDate': data_date,
                             'runDate': datetime.now().strftime("%Y-%m-%d %H:%M"),
                             'textCount': len(corpus)}  # For results as json

        # Get known entities
        try:
            with open(config.INPUT_DIR + 'known_entities.txt', 'r') as file:
                self.known_entities = set(file.read().split(' '))
        except IOError:
            print('Add a text file named "known_entities.txt" that lists named entities (space-delimited) that we '
                  'want to be sure are treated as proper nouns.')
            self.known_entities = set()

        # Stop Words
        try:
            with open(config.INPUT_DIR + 'stop_words.txt', 'r') as file:
                self.stop_words = set(file.read().split(' '))
        except IOError:
            print('Add a text file named "stop_words.txt" that lists common words (space-delimited) that we should '
                  'ignore in most text processing.')
            self.stop_words = set()

        # Loop through texts and tokenize: 'doc' and 'titleDoc' are lists of spaCy tokens, with named entities called
        # recognized and joined. 'textClean' is a string of lemmatized words, excluding stopwords and punctuation.
        # It's used by Doc2Vec.
        for text_id, text in self.texts.items():
            text['doc'] = self._tokenize(text['text'])
            text['titleDoc'] = self._tokenize(text['title'])
            text['textClean'] = ' '.join([token.text.lower() if token.lemma_ == '-PRON-' else token.lemma_ for
                                          token in text['doc'] if token.lemma_ not in
                                          self.stop_words and token.text not in self.punct])

    def _tokenize(self, raw_text):
        """
        Called by __init__, _tokenize begins with the plain text from our source, text['text'], applies the spaCy
        language model to create a token list. Then we loop through each token, looking for 'known entities'. Known
        Entities are from our own file; we use this check to ensure that the language modeler (specifically the POS,
        part of speech, tagger) correctly recognizes important named entities (proper nouns that we think are really
        important, but that are sometimes mis-typed by the model). Second, we look for, then join, multi-word named
        entities.  These are nearly always referring to the same thing (e.g., first name, last name).

        :param raw_text: (str) The raw text for analysis.
        :return: (spaCy tokens) The processed text in the form of spaCy tokens.
        """

        doc = self.nlp(raw_text.strip())

        # Loop through tokens and find known entities aren't already marked
        for token in doc:
            # Is this word in our known_entities, but is not recognized by the spaCy parser?
            if token.text.lower() in self.known_entities and token.ent_type not in self.entities:
                # We need to set the new entity to doc.ents directly (I believe the getter for doc.ents does
                #     some important massaging.  However, counter to the online docs, setting doc.ents wipes out
                #     all of the previously recognized ents, so we stash the value, then we combine and reset.
                stash = doc.ents
                doc.ents = [(token.text.title(), doc.vocab.strings['PERSON'], token.i, token.i + 1)]
                doc.ents = doc.ents + stash

        # Find proper noun n-grams: (a) find a known entity, (b) is the next word also a known entity?,
        #   (c) merge, (d) repeat
        # TODO: Joining mult-word named entities sometimes causes us trouble.
        doc_len = len(doc)  # Helps us know when to exit the 'for loop' (since we change the # of items via merge)
        for token in doc:
            # if we're not at the end of the loop, and we recognize this as a proper noun and it's not a stop word
            # and the token isn't a space...
            if token.i + 1 < doc_len and token.ent_type in self.entities and \
                            token.text.lower() not in self.stop_words and token.text not in ' ':
                next_token = doc[token.i + 1]
                # keep looping while we're not at the end of the loop and this token has the same entity type as
                # the previous token and it's not a stop word or a space.
                while token.i + 1 < doc_len and next_token.ent_type == token.ent_type and \
                                next_token.text.lower() not in self.stop_words and next_token.text not in ' ':
                    n_gram = doc[token.i:token.i + 2]
                    n_gram.merge()
                    doc_len -= 1  # the merge changes the list length, so we just shrunk the list!
                    # print(x)
            if token.i + 1 >= doc_len:
                break

        return doc

    def ngram_detection(self, min_topic_count=5, min_text_id_count=5):
        """
        Find all ngrams within our raw text
        Create ngram counts (absolute and weighted) such that we can find most telling ngrams and know enough to 
        (a) prioritize by topic, (b) tie them back to their underlying topic, (c) highlight in the UI
        :return: 
        """

        # Populate self.ngrams and self.topics
        for text_id, text in self.texts.items():

            # Find pentagrams - ngrams with 5 words
            for ngram in zip(text['doc'], text['doc'][1:], text['doc'][2:], text['doc'][3:], text['doc'][4:]):
                self._ngram_counter(ngram, 5, text_id)

            # Find pentagrams - ngrams with 4 words
            for ngram in zip(text['doc'], text['doc'][1:], text['doc'][2:], text['doc'][3:]):
                self._ngram_counter(ngram, 4, text_id)

            for ngram in zip(text['doc'], text['doc'][1:], text['doc'][2:]):
                self._ngram_counter(ngram, 3, text_id)

            for ngram in zip(text['doc'], text['doc'][1:]):
                self._ngram_counter(ngram, 2, text_id)

            # single-word topics act a bit different (no zips or comprehensions)
            # store data in self.topics, not zip_grams
            for word in text['doc']:
                word_lemma = word.text.lower() if word.lemma_ == '-PRON-' else word.lemma_

                if {word.text}.intersection(self.punct) or {word.lemma_}.intersection(self.stop_words):
                    continue

                if not (word.pos in self.nouns or word.ent_type in self.entities):
                    continue

                if word_lemma in self.topics:
                    self.topics[word_lemma]["count"] += 1
                    self.topics[word_lemma]["textIDs"] |= {text_id}
                    self.topics[word_lemma]["verbatims"] |= {word.text.lower()}
                else:
                    self.topics[word_lemma] = {"name": word_lemma,
                                               "count": 1,
                                               "textIDs": {text_id},
                                               "verbatims": {word.text.lower()}}

        # Add text_id_count (the number of texts that the topic occurs in; so a topic might occur 50 times,
        # but it's only mentioned in 3 different texts, we'd show 3.
        for _, topic in self.topics.items():
            topic['text_id_count'] = len(topic['textIDs'])
        for _, ngram in self.ngrams.items():
            ngram['text_id_count'] = len(ngram['textIDs'])

        # Eliminate rarely occurring topics and ngrams.
        self.topics = {k: v for k, v in self.topics.items() if
                       v['text_id_count'] >= min_text_id_count and v['count'] >= min_topic_count}
        self.ngrams = {k: v for k, v in self.ngrams.items() if
                       v['text_id_count'] >= min_text_id_count}


        # Loop through each ngram pair: outer loop is all ngrams, inner loop is all ngrams
        for ngram_lemma, ngram in self.ngrams.items():
            for ngram_plus_lemma, ngram_plus in self.ngrams.items():
                # only stay in this loop if the inner ngram is one word longer than the outer loop and if the
                # inner loop lemma contains the outer group lemma (avoid partial word matches like man in woman)
                # r'\b' + ngram_lemma + r'\b' --> does the ngram lemma fit in ngram_plus lemma (\b is word boundary)
                if ngram['n'] + 1 != ngram_plus['n']:
                    continue

                if not re.search(r'\b' + ngram_lemma + r'\b', ngram_plus_lemma):
                    continue

                # Is the absolute count of occurrences and the count of text_id occurrences both big enough to use it
                # instead of the other loop?
                if ngram_plus['count'] + 3 >= ngram['count'] and \
                                        ngram_plus['text_id_count'] + 3 >= ngram['text_id_count']:
                    # TODO: Is this the right action (deleting shorter, but not much more explanatory) phrase?
                    # TODO: Is this enough?  Or will I end up double explaining things sometimes?
                    ngram['count'] = -1

        # Eliminate newly demoted items
        self.ngrams = {ngram_lemma: ngram for ngram_lemma, ngram in self.ngrams.items() if ngram['count'] > 0}

    def _ngram_counter(self, ngram, ngram_length, text_id):
        """
        As we're looping through ngrams, handle the tests to see if we want to keep it (Does it contain a noun? Good.
         Does it contain punctuation? Bad. Does it begin (or end) with a stopword? Bad). If we keep the phrase, then
         we need to track a few things about it.
        :param ngram: (spaCy tokens tuple) The phrase that we're testing
        :param ngram_length: (int) The length of the ngram
        :param ngram_dict: (dict)
        :param text_id: The text that this ngram came from...
        :return:
        """

        # Only process this ngram is it's punctuation-free and the 1st / last words are not stopwords
        # Tried allowing last word to be stopwords, quality suffered.
        # Line mechanics: make a set, look for an intersection with another set
        # TODO: verbatims sometimes have punctuation in them.
        if ({word.text for word in ngram}.intersection(self.punct) or
                {ngram[0].lemma_, ngram[ngram_length - 1].lemma_}.intersection(self.stop_words)):
            return

        # Only keep this ngram is it has 1+ nouns in it
        if len([word for word in ngram if word.pos in self.nouns or word.ent_type in self.entities]) == 0:
            return

        # TODO: Some odd lemma_ behavior: other -> oth, bring -> br (Genesis)
        ngram_lemma = ' '.join([word.text.lower() if word.lemma_ == '-PRON-' else word.lemma_ for word in ngram])
        verbatim = ' '.join([word.text.lower() for word in ngram])

        # Keep it! And it's not the first time we've found it.
        if ngram_lemma in self.ngrams:
            self.ngrams[ngram_lemma]["count"] += 1
            self.ngrams[ngram_lemma]["textIDs"] |= {text_id}
            self.ngrams[ngram_lemma]["verbatims"] |= {verbatim}
        # Keep it! This is the 1st instance.
        else:
            self.ngrams[ngram_lemma] = {"name": ngram_lemma,
                                        "count": 1,
                                        "textIDs": {text_id},
                                        "n": ngram_length,
                                        "verbatims": {verbatim}}

    def prune_topics_and_adopt(self, max_topics=40):

        # To find the top X topics (based on max_topics), we'll create a dict that counts the number of topics at
        # each "text ID count" (text ID count = the number of texts that the topic occurs in; so a topic might occur
        # 50 times, but it's only mentioned in 3 different texts, we'd show 3).
        rank_tracker = {}  # {text_id_count: X}
        for topic_lemma, topic in self.topics.items():

            text_id_count = topic['textIDCount'] = len(topic['textIDs'])
            if text_id_count in rank_tracker:
                rank_tracker[text_id_count] += 1
            else:
                rank_tracker[text_id_count] = 1

        # How low do we need to go in text_id_counts to get to get our max_topic count?.
        min_text_id_count = 0  # the min text_id_count that's allowable in the final output
        aggregate_topic_count = 0  # tracks the number of topics that we've found at this text_id_count and higher
        for text_id_count in sorted(rank_tracker, reverse=True):
            aggregate_topic_count += rank_tracker[text_id_count]
            if aggregate_topic_count > max_topics:  # once we've crossed our max, we'll add these in and stop looping
                min_text_id_count = text_id_count
                break

        # Only keep topics that fit within our max_topics list
        self.topics = {k: v for k, v in self.topics.items() if v['textIDCount'] >= min_text_id_count}

        # Add children
        for topic_lemma, topic in self.topics.items():
            topic['children'] = {k: v for k, v in self.ngrams.items() if re.search(r'\b{}\b'.format(topic_lemma), k)}

    def export_topics(self):
        """
        Save topics data to XYZ-Topics.txt. Along the way we'll sort, rank, recalculate some fields (to prep for UI).
         Then prune the dataset (dropping low-usage topics, subtopics).
        :param min_topic_occurs: (int)
        :param min_subtopic_occurs: (int)
        :param max_topics: (int) What's the maximum number of topics to output to sunburst?
        :return:
        """

        # format as a list (for json output), then sort descending by textIDCount
        topics = [{'name': topic['name'], 'count': topic['count'],
                   'verbatims': list(topic['verbatims']), 'textIDs': list(topic['textIDs']),
                   'textIDCount': topic['textIDCount'],
                   'children': '' if 'children' not in topic else topic['children']}
                  for topic_id, topic in self.topics.items()]
        topics = sorted(topics, key=lambda topic: topic['textIDCount'], reverse=True)

        rank = 1
        prev_count = 0
        for i, topic in enumerate(topics):
            current_count = topic['textIDCount']

            if current_count < prev_count:  # this topic occurs less often than the last one
                rank = i + 1

            topic['rank'] = rank
            # Prune low-use phrases and the 'phrase' attribute
            # topic['children'] = []
            topic['children'] = [{'name': child['name'], 'count': child['count'],
                                  'verbatims': list(child['verbatims']), 'textIDs': list(child['textIDs']),
                                  'textIDCount': len(list(child['textIDs']))}
                                 for child_id, child in topic['children'].items() if child['count'] > 3]

            topic['children'] = sorted(topic['children'], key=lambda lemma: lemma['textIDCount'], reverse=True)

            # If the subtopic count is greater than the topic count, than calc a multiplier to size each subtopic
            child_count = sum([child['textIDCount'] for child in topic['children']])
            child_count_multiplier = 1 if child_count < topic['textIDCount'] else topic['textIDCount'] / child_count

            for child in topic['children']:
                child['rank'] = rank
                child['size'] = child['textIDCount'] * child_count_multiplier

            topic['size'] = topic['textIDCount'] - (child_count * child_count_multiplier)
            # topic['size'] = topic['textCount'] - child_count if topic['textCount'] >= child_count else 0
            prev_count = current_count

        # Prune topics over max_topics (default ~40): we stopped calc'ing rank over the max_topics
        self.model_output["children"] = [topic for topic in topics if 'rank' in topic]

        # Build file name and save
        if self.data_date:
            date = datetime.strptime(self.data_date, "%Y-%m-%d").strftime('%d')  # from YYYY-MM-DD to DD
            file_name = '{}-{}-Topics.txt'.format(self.corpus_name, date)
        else:
            file_name = '{}-Topics.txt'.format(self.corpus_name)

        with open(config.OUTPUT_DIR + file_name, 'w') as file:
            json.dump(self.model_output, file)
