"""
Review a series of texts and extract and group topics (nouns), maintaining a noun-phrase link to the original text.

Explains POS Tags: http://universaldependencies.org/en/pos/all.html#al-en-pos/DET
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

    def __init__(self, corpus_name, corpus, max_topics=40, data_date=''):
        """
        To initialize, we'll (a) create some regex expressions and sets that will get used later in topic_builder; (b)
        check the input arguments to ensure it's "as expected" for both topic_builder and the UI; (c) save the
        arguments to variables and set up our primary output variables; and (d), grab a couple of files that have
        contents that we'll use during processing.
        :param corpus_name: (str) A short (between 3 and 20 characters) human-readable name for this corpus of texts.
            It will show up in the UI and help us pass the file back-and-forth.
        :param corpus: (dict) A dictionary of texts that make up this corpus.
        :param max_topics: (int) What's the maximum number of topics to output to sunburst?
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
        assert type(max_topics) is int, 'The max_topics must be an integer.'
        assert max_topics > 0, 'max_topics should be 1 or higher (or I will not return anything.'

        # Topic metadata & settings
        self.corpus_name = corpus_name.replace(' ', '')  # (str) The name of the set (or corpus) of texts.
        self.max_topics = max_topics
        self.data_date = data_date

        # Primary Data Structures
        self.texts = corpus  # The passed in dict of all texts that we'll analyze
        self.summary = {}  # A dictionary that we'll create here that has summary stats
        self.topics = {}  # A dict that we'll populate with found Topics
        self.model_output = {'name': corpus_name,
                             'data_date': data_date,
                             'run_date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                             'text_count': len(corpus),
                             'max_topics': max_topics,
                             'dataDate': data_date,
                             'runDate': datetime.now().strftime("%Y-%m-%d %H:%M"),
                             'textCount': len(corpus),
                             'maxTopics': max_topics}  # For results as json

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

        self._tokenize()

    def _tokenize(self):
        """
        Create spaCy token lists from the original text strings from self.texts['text']. 
        :return: 
        """

        # Loop through texts looking for important known entities and entity n-grams
        for text_id, text in self.texts.items():
            doc = self.nlp(text['text'].strip())

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
            doc_len = len(doc)  # Helps us know when to exit the 'for loop' (since we change the # of items via merge)
            for token in doc:
                if token.i + 1 < doc_len and token.ent_type in self.entities and \
                                token.text.lower() not in self.stop_words and token.text not in ' ':
                    next_token = doc[token.i + 1]
                    while token.i + 1 < doc_len and next_token.ent_type == token.ent_type and \
                                    next_token.text.lower() not in self.stop_words and next_token.text not in ' ':
                        n_gram = doc[token.i:token.i + 2]
                        n_gram.merge()
                        doc_len -= 1  # the merge changes the list length, so we just shrunk the list!
                        # print(x)
                if token.i + 1 >= doc_len:
                    break

            text['doc'] = doc
            # text['tokens'] = [word for word in doc]
            # text['tokensClean'] = [str(word.lemma_).lower() for word in doc
            #                        if word.is_alpha and (str(word).lower() not in self.stop_words)]

            title_doc = self.nlp(text['title'])
            text['title_doc'] = title_doc

    def ngram_detection(self):
        """
        Create ngram counts (absolute and weighted) such that we can find most telling ngrams and know enough to 
        (a) prioritize by topic, (b) tie them back to their underlying topic, (c) highlight in the UI
        :return: 
        """

        # Build a series of dictionaries (could be all 1 dict, but thought performance would be better this way)
        zip_grams = {}
        for text_id, text in self.texts.items():

            # Find pentagrams - ngrams with 5 words
            for ngram in zip(text['doc'], text['doc'][1:], text['doc'][2:], text['doc'][3:], text['doc'][4:]):
                self.ngram_counter(ngram, 5, zip_grams, text_id)

            # Find pentagrams - ngrams with 5 words
            for ngram in zip(text['doc'], text['doc'][1:], text['doc'][2:], text['doc'][3:]):
                self.ngram_counter(ngram, 4, zip_grams, text_id)

            for ngram in zip(text['doc'], text['doc'][1:], text['doc'][2:]):
                self.ngram_counter(ngram, 3, zip_grams, text_id)

            for ngram in zip(text['doc'], text['doc'][1:]):
                self.ngram_counter(ngram, 2, zip_grams, text_id)

            # single-word topics act a bit different (no zips or comprehensions)
            for word in text['doc']:
                word_lemma = word.text.lower() if word.lemma_ == '-PRON-' else word.lemma_

                if ({word.text}.intersection(self.punct) or
                        {word.lemma_}.intersection(self.stop_words)):
                    continue
                elif not (word.pos in self.nouns or word.ent_type in self.entities):
                    continue
                elif word_lemma in self.topics:
                    self.topics[word_lemma]["count"] += 1
                    self.topics[word_lemma]["textIDs"] |= {text_id}
                    self.topics[word_lemma]["verbatims"] |= {word.text.lower()}
                else:
                    self.topics[word_lemma] = {"name": word_lemma,
                                               "count": 1,
                                               "textIDs": {text_id},
                                               "n": 1,
                                               "lemmas": {word_lemma},
                                               "verbatims": {word.text.lower()},
                                               "children": {}}  # TODO: This should go away...

        zip_grams = {k: v for k, v in zip_grams.items() if v['count'] > 2}
        for zip_key, zip_val in zip_grams.items():
            for zip_plus_key, zip_plus_val in zip_grams.items():
                if zip_key in zip_plus_key and zip_key != zip_plus_key:
                    if zip_plus_val['count'] + 3 >= zip_val['count'] and \
                                            len(zip_plus_val['textIDs']) + 3 >= len(zip_val['textIDs']):
                        # TODO: Is this the right action (deleting shorter, but not much more explanatory) phrase?
                        zip_val['count'] = -1

        zip_grams = {k: v for k, v in zip_grams.items() if v['count'] > 2}

        # TODO: verbatims sometimes have punctuation in them.
        # Let's find the top X topics (based on max_topics)
        # Create weighting, and count by bin.  Then determine biggest bin
        rank_tracker = {}
        for topic_lemma, topic in self.topics.items():

            text_count = topic['textCount'] = len(topic['textIDs'])
            if text_count in rank_tracker:
                rank_tracker[text_count] += 1
            else:
                rank_tracker[text_count] = 1

        max_bin = 0
        agg_count = 0
        for text_count in sorted(rank_tracker, reverse=True):
            agg_count += rank_tracker[text_count]
            if agg_count > self.max_topics:
                max_bin = text_count
                break

        # Add children
        for topic_lemma, topic in self.topics.items():
            if topic['textCount'] >= max_bin:
                topic['children'] = {k: v for k, v in zip_grams.items() if topic_lemma in k and topic_lemma != k}
                # topic['children'] = {k: v for k, v in self.topics.items() if topic_lemma in k}


    def ngram_counter(self, ngram, ngram_length, ngram_dict, text_id):
        """
        As we're looping through ngrams, handle the tests to see if we want to keep it (Does it contain a noun? Good.
         Does it contain punctuation? Bad. Does it begin (or end) with a stopword? Bad). If we keep the phrase, then
         we need to track a few things about it.
        :param ngram: The phrase that we're testing (
        :param ngram_length: int
        :param ngram_dict: dict
        :param text_id: The text that this ngram came from...
        :return:
        """

        # TODO: Some odd lemma_ behavior: other -> oth, bring -> br (Genesis)
        ngram_lemma = ' '.join(
            [word.text.lower() if word.lemma_ == '-PRON-' else word.lemma_ for word in ngram])

        # Only process this ngram is it's punctuation-free and the 1st / last words are not stopwords
        # TODO: Drop the requirement for the last word to be a non-stopword and see what happens.
        if ({word.text for word in ngram}.intersection(self.punct) or
                {ngram[0].lemma_, ngram[ngram_length - 1].lemma_}.intersection(self.stop_words)):
            return
        # Only keep this ngram is it has 1+ nouns in it
        elif len([word for word in ngram if word.pos in self.nouns or word.ent_type in self.entities]) == 0:
            return
        elif ngram_lemma in ngram_dict:
            ngram_dict[ngram_lemma]["count"] += 1
            ngram_dict[ngram_lemma]["textIDs"] |= {text_id}
            ngram_dict[ngram_lemma]["verbatims"] |= {' '.join([word.text.lower() for word in ngram])}
        else:
            ngram_dict[ngram_lemma] = {"name": ngram_lemma,
                                       "count": 1,
                                       "textIDs": {text_id},
                                       "n": ngram_length,
                                       "verbatims": {' '.join([word.text.lower() for word in ngram])},
                                       "lemmas": {lemma for lemma in ngram_lemma.split(' ') if
                                                  lemma not in self.stop_words},
                                       "children": {}}

    def summarize_texts(self):
        """
        Add an entry to the summary dict that contains all texts.
        :return: Return the summary dict.
        """
        summary = {'text': ''.join([text['text'] for text_id, text in self.texts.items()])}

        return summary


    def export_topics(self):
        """
        Save topics to Topics-XYZ.txt in the Output directory.  Along the way we'll sort, rank, recalculate at least
        on field for the UI, and prune the dataset (dropping low-usage topics).
        :return: 
        """

        # Calculate the importance of each ngram (used to determine relative explanatory power between ngrams
        # and in the UI to size and rank slices.

        # format as a json-style list with name, size, rank (prepping for sunburst viz).
        topics = [{'name': topic['name'], 'count': topic['count'],
                   'verbatims': list(topic['verbatims']), 'textIDs': list(topic['textIDs']),
                   # 'textCount': len(list(topic['textIDs'])),
                   'textCount': len(topic['textIDs']),
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

            # If the subtopic count is greater than the topic count, than calc a multiplier to size each subtopic
            child_count = sum([child['textCount'] for child in topic['children']])
            child_count_multiplier = 1 if child_count < topic['textCount'] else topic['textCount'] / child_count

            for child in topic['children']:
                child['rank'] = rank
                child['size'] = child['textCount'] * child_count_multiplier

            topic['size'] = topic['textCount'] - (child_count * child_count_multiplier)
            # topic['size'] = topic['textCount'] - child_count if topic['textCount'] >= child_count else 0
            prev_count = current_count

        # Prune topics over max_topics (default ~40): we stopped calc'ing rank over the max_topics
        self.model_output["children"] = [topic for topic in topics if 'rank' in topic]

        # Build file name and save
        if self.data_date:
            date = datetime.strptime(self.data_date, "%Y-%m-%d").strftime('%d')  # from YYYY-MM-DD to DD
            file_name = 'Topics-{}-{}.txt'.format(self.corpus_name, date)
        else:
            file_name = 'Topics-{}.txt'.format(self.corpus_name)

        with open(config.OUTPUT_DIR + file_name, 'w') as file:
            json.dump(self.model_output, file)
