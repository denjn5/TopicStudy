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
import datetime

TEXTS_DIR = 'Texts/'
OUTPUT_DIR = 'Output/'


class AnalyticsFactory:
    """
    Runs texts through a number of analytics to identify word relationships and key sentences.
    """
    # FEATURE: Incorporate doc2vec

    # # INPUT
    # tokens = []                 # Text as a nested list of spaCy tokens (by sentence)
    # clean_tokens = []           # Nested list of cleaned-up spaCy tokens (by sentence)
    # clean_text = ''             # clean_tokens as string
    # doc = None                  # spaCy doc (retained for debug analysis).
    #
    # # OUTPUT
    # top_words = set()           # Keywords as a set
    # summary_sent = ''           # Summary sentence or 3
    # words = []                  # word2vec model words (string, count tuple)
    # links = []                  # word2vec links (word1, word2, link strength tuple)
    # noun_profile = []              # The top n nouns in the texts.
    # model_sets = []             # Model settings (for json output)

    def __init__(self, texts, corpus_name):
        """
        Initialize the AnalyticsFactory!
        :param texts: The texts that we want to analyze.
        :param corpus_name: The differentiating file name for saving/retrieving
        """
        self.corpus_name = corpus_name
        self.texts = texts
        self.words = []
        self.links = []
        self.noun_profile = []

        now = datetime.datetime.now()
        self.model_sets = [{'run_date': now.strftime("%Y-%m-%d %H:%M"), 'corpus_name': self.corpus_name}]


    def keywords(self, raw, word_count=5):
        """
        Find teh top n words in the texts based on Gensim's model.
        :param word_count: How many words to find?
        :return: The top n words as a set.
        """
        # TODO: texts vs clean_text?
        summary_words = gensim.summarization.keywords(raw, words=word_count)
        self.top_words = set(summary_words.split('\n'))  # transform string of words to a set.

        return self.top_words

    def key_sentence(self, raw, sentence_ratio=None):
        """
        Returns the best summary sentence based on Gensim's model.
        By default, we return the single best sentence. Use sentence_ratio to ask for a larger chunk.
        :param sentence_ratio: An integer between 1 and 99 representing the percentage of summary texts you'd like.
        :return: The summary sentence
        """

        for ss_ratio in (sentence_ratio if sentence_ratio else range(2, 100, 1)):
            # ss_ratio = sentence_ratio if sentence_ratio else 20 / len(self.texts.split(' '))
            self.summary_sent = gensim.summarization.summarize(raw, ratio=(ss_ratio / 100))  # split=True?
            if sentence_ratio or len(self.summary_sent) > 0:
                sentence_ratio = ss_ratio
                break

        self.model_sets.append({'top_sentence_ratio': sentence_ratio})
        return self.summary_sent

    def build_word2vec(self, tokens, size=100, window=5, min_count=3, sg=0, max_words=100, min_link=0.1, pickle=False):
        """
        Train a Word2Vec model.
        Note: The "you must first build vocabulary before training the model" usually means that you haven't provided
        a properly tokenized texts to the Word2Vec model. Be sure to remove stopwords.
            tokens = [['first', 'sentence'], ['second', 'sentence']]
        :param size: How many training nodes? Probably min 100, but could go much higher (it'll take longer).
        :param window: How many words on either side of word in question.
        :param min_count: The minimum number of times a word can appear in texts and still be included.
        :param sg: 0 for bag of words; 1 for skip gram
        :param pickle: Should the model be saved?
        :return:
        """

        # WORD2VEC: create model
        #tokens_str = [[str(word) for word in sent] for sent in self.clean_tokens]
        w2v = gensim.models.Word2Vec(tokens, size=size, window=window, min_count=min_count, sg=sg, workers=4)

        w2v.init_sims(replace=True)  # No further training?
        if pickle:
            w2v.save(OUTPUT_DIR + self.corpus_name + '_w2v.pickle')

        for word, vocab_obj in w2v.wv.vocab.items():
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
        with open(OUTPUT_DIR + 'top.json', 'w') as f:
            json.dump(json_content, f)

        return json_content


if __name__ == "__main__":
    txt = """And the king of Egypt called for the midwives, and said unto them, Why have ye done this thing, and have
        saved the men children alive? And the midwives said unto Pharaoh, Because the Hebrew women are not as
        the Egyptian women; for they are lively, and are delivered ere the midwives come in unto them.
        Therefore God dealt well with the midwives: and the people multiplied, and waxed very mighty.
        And it came to pass, because the midwives feared God, that he made them houses. And Pharaoh charged
        all his people, saying, Every son that is born ye shall cast into the river, and every daughter ye
        shall save alive."""
    AnalyticsFactory(txt, 'exo1f')
