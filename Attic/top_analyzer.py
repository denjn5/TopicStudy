"""
source: 02a_analyze.py
author: david richards
date: 2017-02-03

purpose: Open tokenize text, analyze
* WordCount
* TopWords
* TopSentence
* Word2Vec Relationships
"""

# IMPORTS
import json
import gensim
import spacy
import spacy.symbols as ss
import top_graph

SRC_DIR = 'SourceText/'
MODEL_DIR = 'Models/'


class AnalyticsFactory:
    # INPUT
    pickle_name = 'general'     # name for saves and retrievals
    text = ''                   # The original string for analysis
    tokens = []                 # Text as a nested list of spaCy tokens (by sentence)
    clean_tokens = []           # Nested list of cleaned-up spaCy tokens (by sentence)
    clean_text = ''             # clean_tokens as string
    doc = None                  # spaCy doc (retained for debug analysis).

    # OUTPUT
    top_words = set()           # Keywords as a set
    summary_sent = ''           # Summary sentence or 3
    words = []                  # word2vec model words (string, count tuple)
    links = []                  # word2vec links (word1, word2, link strength tuple)
    noun_profile = []              # The top n nouns in the text.
    model_sets = []             # Model settings (for json output)

    def __init__(self, text, pickle_name):
        """
        Initialize the AnalyticsFactory!
        :param text: The text that we want to analyze.
        :param pickle_name: The differentiating file name for saving/retrieving
        """
        self.pickle_name = pickle_name
        self.text = text
        self._tokenizer()
        clean_token_count = sum([len(sent) for sent in self.clean_tokens])

        self.model_sets.append({'run_date': 'today', 'text_name': self.pickle_name, 'clean_token_count': clean_token_count})

    def _tokenizer(self):
        """
        Tokenize the text that we're studying.
        """
        nlp = spacy.load('en')
        self.doc = nlp(self.text)
        self.tokens = [[word for word in sent] for sent in self.doc.sents]

        # STOP WORDS
        with open(SRC_DIR + 'stopwords.txt', 'r') as file:
            stopwords = set(file.read().split(' '))

        # PARSE & CLEAN: lowercase; lemmatize; eliminate stopwords, punctuation, numbers
        self.clean_tokens = [[str(word.lemma_).lower() for word in sent
                              if (str(word).lower() not in stopwords) and word.is_alpha]  # str(word).isalpha()
                             for sent in self.tokens]  # eliminate single-use words?
        self.clean_tokens = [s for s in self.clean_tokens if s]  # remove empty sentences
        self.clean_text = ' '.join([' '.join([str(c) for c in lst]) for lst in self.clean_tokens])

    def find_top_words(self, top_word_count=5):
        """
        Find teh top n words in the text based on Gensim's model.
        :param top_word_count: How many words to find?
        :return: The top n words as a set.
        """
        # TODO: text vs clean_text?
        summary_words = gensim.summarization.keywords(self.text, words=top_word_count)
        self.top_words = set(summary_words.split('\n'))  # transform string of words to a set.

        return self.top_words

    def find_top_sentence(self, sentence_ratio=None):
        """
        Returns the best summary sentence based on Gensim's model.
        By default, we return the single best sentence. Use sentence_ratio to ask for a larger chunk.
        :param sentence_ratio: An integer between 1 and 99 representing the percentage of summary text you'd like.
        :return: The summary sentence
        """

        for ss_ratio in (sentence_ratio if sentence_ratio else range(2, 100, 1)):
            # ss_ratio = sentence_ratio if sentence_ratio else 20 / len(self.text.split(' '))
            self.summary_sent = gensim.summarization.summarize(self.text, ratio=(ss_ratio / 100))  # split=True?
            if sentence_ratio or len(self.summary_sent) > 0:
                sentence_ratio = ss_ratio
                break

        self.model_sets.append({'top_sentence_ratio': sentence_ratio})
        return self.summary_sent

    def build_word2vec(self, size=100, window=5, min_count=3, sg=0, max_words=100, min_link=0.1, pickle=False):
        """
        Train a Word2Vec model.
        Note: The "you must first build vocabulary before training the model" usually means that you haven't provided
        a properly tokenized text to the Word2Vec model.
        :param size: How many training nodes? Probably min 100, but could go much higher (it'll take longer).
        :param window: How many words on either side of word in question.
        :param min_count: The minimum number of times a word can appear in text and still be included.
        :param sg: 0 for bag of words; 1 for skip gram
        :param pickle: Should the model be saved?
        :return:
        """

        # WORD2VEC: create model
        tokens_str = [[str(word) for word in sent] for sent in self.clean_tokens]
        w2v = gensim.models.Word2Vec(tokens_str, size=size, window=window, min_count=min_count, sg=sg, workers=4)

        w2v.init_sims(replace=True)  # No further training?
        if pickle:
            w2v.save(MODEL_DIR + self.pickle_name + '_w2v.pickle')

        for word, vocab_obj in w2v.vocab.items():
            self.words.append((word, vocab_obj.count))
        self.words = sorted(self.words, key=lambda x: x[1], reverse=True)  # sort words by count, descending
        self.words = self.words[:max_words]  # limit word count

        # LINKS LIST: {"source": "god", "target": "man", "value": 1.5}
        for i1, word1 in enumerate(self.words):
            for i2, word2 in enumerate(self.words):
                sim = w2v.similarity(word1[0], word2[0])
                if i1 >= i2 or abs(sim) < min_link:  # skip duplicate and weak relationships
                    continue
                self.links.append((word1[0], word2[0], round(sim, 2)))
        self.model_sets.append({'w2v_size': size, 'w2v_window': window, 'w2v_min_count': min_count, 'w2v_sg': sg,
                                'w2v_word_count': len(self.words), 'max_words': max_words, 'min_link': min_link})

    def export_json(self):
        """
        Aggregates analytics results from word2vec (required), summary_sentence, and summary_words and save
        as a json file for presentation.
        :param max_words: Want to limit the number of words exported?
        :param min_link: Want to skip exporting weak links?
        :return: The json content
        """
        assert len(self.links) > 0, "export_json requires word2vec values. Run that first."

        # VOCAB LIST & COUNT: {"id": "god", "count": 32, "rank": 5}
        nodes = []
        i = 0
        for word in self.words:
            i += 1
            top = 'top' if word in self.top_words else 'other'
            nodes.append({'id': word[0], 'count': word[1], 'rank': i, 'top': top})

        # EDGES LIST: {"source": "god", "target": "man", "value": 1.5}
        j_links = []
        for link in self.links:
            j_links.append({'source': link[0], 'target': link[1], 'value': int(link[2] * 100)})

        # SAVE JSON (twice)
        json_content = {'model_settings': self.model_sets, 'nodes': nodes, 'links': j_links,
                        'top_sentence': self.summary_sent, 'noun_profile': self.noun_profile}
        with open(MODEL_DIR + 'top.json', 'w') as f:
            json.dump(json_content, f)

        return json_content

    def noun_profiler3(self, top_noun_count=5):
        """
        Create a list of all nouns with counts or interesting phrases.
        Saves 3 objects:
            * noun_profile:
            * models_sets:
        :param top_noun_count: How many top nouns do we want to keep?
        :return:
        """
        # COUNT AND INVENTORY NOUNS
        noun_counter = {}
        noun_phrases_old = {}
        noun_phrases = {}
        noun_occur_ct = 0
        for token in self.doc:
            if token.pos in {ss.NOUN, ss.PROPN, ss.PRON}:
                noun_occur_ct += 1
                word = str(token.lemma_)
                if word in noun_counter:
                    noun_counter[word] += 1
                else:
                    noun_counter[word] = 1

                # create the phrase
                # TODO: Look for NER bigrams...
                pre = self.doc[token.i - 1]
                head = token.head
                s = [token]
                s.append(head) if head not in {token, pre} and head.pos != ss.ADP else None
                s.insert(0, pre) if pre.pos in {ss.ADJ, ss.VERB, ss.NOUN, ss.PROPN, ss.PRON} else None

                # number 2
                if word in noun_phrases_old:
                    noun_phrases_old[word].append(s)
                else:
                    noun_phrases_old[word] = [s]

                # number 3
                lemma_phrase = [word.lemma_ for word in s]
                lemma_phrase = ' '.join(lemma_phrase)
                s.insert(0, 1)
                if word in noun_phrases:
                    word_dict = noun_phrases[word]
                    if lemma_phrase in word_dict:
                        word_dict[lemma_phrase][0] += 1
                    else:
                        word_dict[lemma_phrase] = s

                else:
                    word_dict = {lemma_phrase: s}
                    noun_phrases[word] = [word_dict]

        # sorted(sorted_noun_phrases[0][1], key=lambda x: len(x)) // sorted(sorted_noun_phrases[0][1], key=lambda x:
        sorted_noun_phrases = sorted(noun_phrases_old.items(), key=lambda x: len(x[1]), reverse=True)
        top_nth_count = min(sorted(noun_counter.values())[-top_noun_count:])  # find min count of top nth noun

        top_noun_occur_ct = 0
        for word, cnt in noun_counter.items():
            if cnt >= top_nth_count:
                top_noun_occur_ct += cnt
            if cnt / noun_occur_ct > 0.01:  # only words that account for 1% or more of the nouns
                # TODO: Should this be a tuple instead of dict?
                self.noun_profile.append({'word': word, 'count': cnt, 'percent': round(cnt / noun_occur_ct, 2)})

        top_noun_coverage = round(top_noun_occur_ct / noun_occur_ct, 2)  # % of noun occurrences accounted for
        self.model_sets.append({'top_noun_count': top_noun_count, 'top_noun_coverage': top_noun_coverage,
                                'noun_occur_ct': noun_occur_ct})
        return top_noun_coverage

    def noun_profiler(self, top_noun_count=5):
        noun_counter = {}
        noun_occur_ct = 0
        for token in self.doc:
            if token.pos in {ss.NOUN, ss.PROPN}:
                noun_occur_ct += 1
                word = str(token.lemma_)
                if word in noun_counter:
                    noun_counter[word] += 1
                else:
                    noun_counter[word] = 1

        top_nth_count = min(sorted(noun_counter.values())[-top_noun_count:])  # find min count of top nth noun

        top_noun_occur_ct = 0
        for word, cnt in noun_counter.items():
            if cnt >= top_nth_count:
                top_noun_occur_ct += cnt
            if cnt / noun_occur_ct > 0.01:  # only words that account for 1% or more of the nouns
                self.noun_profile.append({'word': word, 'count': cnt, 'percent': round(cnt / noun_occur_ct, 2)})

        top_noun_coverage = round(top_noun_occur_ct / noun_occur_ct, 2)  # % of noun occurrences accounted for
        self.model_sets.append({'top_noun_count': top_noun_count, 'top_noun_coverage': top_noun_coverage,
                                'noun_occur_ct': noun_occur_ct})
        return top_noun_coverage

    def graph_prep(self, top_noun_count=5):
        tg = top_graph.GraphManager()
        tg.delete_all()
        noun_counter = {}
        noun_phrases_old = {}
        noun_phrases = {}
        noun_occur_ct = 0
        for token in self.doc:
            if token.pos in {ss.NOUN, ss.PROPN}:
                noun_occur_ct += 1
                word = str(token.lemma_)
                if word in noun_counter:
                    x = 'put something here'
                else:

                    tg.new_topic(token.lex_id, token.lemma_)

        tg.close()

        # create the phrase
        # TODO: Look for NER bigrams...
        pre = self.doc[token.i - 1]
        head = token.head
        s = [token]
        s.append(head) if head not in {token, pre} and head.pos != ss.ADP else None
        s.insert(0, pre) if pre.pos in {ss.ADJ, ss.VERB, ss.NOUN, ss.PROPN, ss.PRON} else None

        # number 3
        lemma_phrase = [word.lemma_ for word in s]
        lemma_phrase = ' '.join(lemma_phrase)
        s.insert(0, 1)
        if word in noun_phrases:
            word_dict = noun_phrases[word]
            if lemma_phrase in word_dict:
                word_dict[lemma_phrase][0] += 1
            else:
                word_dict[lemma_phrase] = s

        else:
            word_dict = {lemma_phrase: s}
            noun_phrases[word] = [word_dict]

        top_nth_count = min(sorted(noun_counter.values())[-top_noun_count:])  # find min count of top nth noun

        top_noun_occur_ct = 0
        for word, cnt in noun_counter.items():
            if cnt >= top_nth_count:
                top_noun_occur_ct += cnt
            if cnt / noun_occur_ct > 0.01:  # only words that account for 1% or more of the nouns
                self.noun_profile.append({'word': word, 'count': cnt, 'percent': round(cnt / noun_occur_ct, 2)})

        top_noun_coverage = round(top_noun_occur_ct / noun_occur_ct, 2)  # % of noun occurrences accounted for
        self.model_sets.append({'top_noun_count': top_noun_count, 'top_noun_coverage': top_noun_coverage,
                                'noun_occur_ct': noun_occur_ct})
        return top_noun_coverage

    def key_phrases(self):
        # FIND KEY PHRASES
        # TODO: Finish this logic
        key_phrases = {}
        flat_tokens = [word for sent in self.tokens for word in sent]
        for word in flat_tokens[:-1]:
            word_next = flat_tokens[word.i + 1]
            if word.is_alpha is False or word_next.is_alpha is False:
                continue
            if (str(word).lower() in self.top_words) or (str(word_next).lower() in self.top_words):
                phrase = str(word).lower() + ' ' + str(word_next).lower()
                if phrase in key_phrases.keys():
                    key_phrases[phrase] += 1
                else:
                    key_phrases[phrase] = 1

                    # for sent in tbs:
                    #     print(list(zip(sent[0:], sent[1:], sent[2:])))

                    # PRINTS
                    # d = {dictionary.get(id): value for doc in corpus_tfidf for id, value in doc}
                    # word2vec['god']
                    # word2vec.most_similar("man")
                    # model.doesnt_match("sin death life temple".split())


if __name__ == "__main__":
    txt = """And the king of Egypt called for the midwives, and said unto them, Why have ye done this thing, and have
        saved the men children alive? And the midwives said unto Pharaoh, Because the Hebrew women are not as
        the Egyptian women; for they are lively, and are delivered ere the midwives come in unto them.
        Therefore God dealt well with the midwives: and the people multiplied, and waxed very mighty.
        And it came to pass, because the midwives feared God, that he made them houses. And Pharaoh charged
        all his people, saying, Every son that is born ye shall cast into the river, and every daughter ye
        shall save alive."""
    AnalyticsFactory(txt, 'exo1f')
