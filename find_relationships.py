"""
source: 02a_analyze.py
author: david richards
date: 2017-02-03

purpose: Open tokenize text, analyze
* WordCount
* TopWords
* TopSentence
* Word2Vec Relationships

doc2vec: https://github.com/linanqiu/word2vec-sentiments/blob/master/run.py
"""

# IMPORTS
import json
import datetime
import gensim
from gensim.models.doc2vec import TaggedDocument

TEXTS_DIR = 'Data/'
OUTPUT_DIR = 'Output/'


class FindRelationships(object):
    """
    Runs texts through a number of analytics to identify word relationships and key sentences.
    """

    def __init__(self, texts, corpus_name):
        """
        Initialize the AnalyticsFactory!
        :param texts: The texts that we want to analyze.
        :param corpus_name: The differentiating file name for saving/retrieving
        """
        self.corpus_name = corpus_name
        self.texts = texts
        self.model_output = {"AnalyticsFactor": {'run_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                                                 'corpus_name': self.corpus_name}}

    def keywords(self, raw, word_count=5):
        """
        Find the top n words in the texts based on Gensim's TextRank model.
        :param raw: Raw text, as a single string.
        :param word_count: How many words to find?
        :return: The top n words as a set.
        """
        # TODO: Uses all texts. Should we use clean_text?
        summary_words = gensim.summarization.keywords(raw, words=word_count)
        top_words = set(summary_words.split('\n'))  # transform string of words to a set.

        self.model_output["keywords"] = summary_words.split('\n')
        return top_words

    def key_sentences(self, raw, sentence_ratio=None):
        """
        Returns the best summary sentence based on Gensim's modified TextRank model (which sentence is most similar to
        all other sentences in the corpus?). We try to return as few sentences as possible, so we begin by asking for 
        a summary that is 0.25% of the entire corpus in length, then increase up to 25% from there.
        :param raw: Raw text, as a single string.
        :param sentence_ratio: An integer between 1 and 99 representing the percentage of summary texts you'd like.
        :return: The summary sentence(s)
        """
        # TODO: Be smarter: 20/wordcount for starters.  Ensure <1% of total text.
        summary_sent = ""
        for ss_ratio in (sentence_ratio if sentence_ratio else range(1, 100, 5)):
            summary_sent = gensim.summarization.summarize(raw, ratio=ss_ratio / 400)  # split=True?
            if sentence_ratio or len(summary_sent) > 0:
                sentence_ratio = ss_ratio
                break

        self.model_output["key_sentences"] = {'top_sentence_ratio': sentence_ratio,
                                              'summary_sentences': summary_sent}
        return summary_sent

    def doc2vec(self, texts, size=100, window=5, min_count=3, sample=1e-4, negative=5, min_link=0.2, pickle=False):
        """
        Train a Doc2Vec model. (https://radimrehurek.com/gensim/models/doc2vec.html). 
        
        Both d2v.docvecs.most_similar('mat_4:25') and d2v.docvecs.doctags provide some quick insight.
        :param texts: (dict) Clean (no stop words, only alpha word): {reference: [first, sentence, second sentence]}
        :param size: (int)
        :param window: (int) 
        :param min_count: (int) 
        :param sample: 
        :param negative: (int) 
        :param min_link: (int) 
        :param pickle: (bool)
        :return: 
        """

        # Format texts for Doc2Vec model
        sentences = []
        for ref, text in texts.items():
            sentences.append(TaggedDocument(text, [ref]))

        # Train, trim, save Doc2Vec model
        d2v = gensim.models.Doc2Vec(sentences, size=size, window=window, min_count=min_count, sample=sample,
                                    negative=negative, workers=7)

        d2v.docvecs.init_sims(replace=True)  # No further training?
        if pickle:
            d2v.save(OUTPUT_DIR + self.corpus_name + '_d2v.pickle')

        # Create output lists of nodes (docs) and doc_links
        docs = []  # docs: {"id": "doc1"}
        doc_links = []  # links: {"source": "doc1", "target": "doc2", "value": 1}
        for i1, doc1 in enumerate(texts):
            docs.append({'id': doc1})

            for i2, doc2 in enumerate(texts):
                if i1 > i2:  # skip duplicates
                    sim = d2v.docvecs.similarity(doc1, doc2)
                    if abs(sim) > min_link:  # skip weak relationships
                        # re-range sim from [1:0:-1] to [5:10:15] -- prep for force diagram
                        # TODO: Is this length value okay? Consider strength component to output.
                        doc_links.append({'source': doc1, 'target': doc2, 'value': int((sim * -5) + 10)})

        doc_count = len(docs)
        self.model_output["doc2vec"]: {"size": size, "window": window, "min_count": min_count, "doc_count": doc_count,
                                       "min_link": min_link, "docs": docs, "doc_links": doc_links}

    def word2vec(self, tokens, size=100, window=5, min_count=3, sg=0, max_words=100, min_link=0.2, pickle=False):
        """
        Train a Word2Vec model.
        Note: The "you must first build vocabulary before training the model" usually means that you haven't provided
        a properly tokenized texts to the Word2Vec model. Be sure to remove stopwords.
            tokens = 
        :param tokens: (list) [['first', 'sentence'], ['second', 'sentence']]
        :param size: (int) How many training nodes? Probably min 100, but could go much higher (it'll take longer).
        :param window: (int) How many words on either side of word in question.
        :param min_count: (int) The minimum number of times a word can appear in texts and still be included.
        :param sg: (int) 0 for bag of words; 1 for skip gram
        :param max_words: (ind)
        :param min_link: 
        :param pickle: (bool) Should the model be saved?
        :return:
        """

        # Train, trim, save Word2Vec model
        w2v = gensim.models.Word2Vec(tokens, size=size, window=window, min_count=min_count, sg=sg, workers=4)
        w2v.wv.init_sims(replace=True)  # No further training?
        if pickle:
            w2v.save(OUTPUT_DIR + self.corpus_name + '_w2v.pickle')

        # Groom the vocabulary list for output
        words = []
        for word, vocab_obj in w2v.wv.vocab.items():
            words.append((word, vocab_obj.count))

        words = sorted(words, key=lambda x: x[1], reverse=True)  # sort words by count, descending
        words = words[:max_words]  # limit word count

        # Create output lists of nodes (words) and word_links
        nodes = []  # nodes: {"id": "word1", "count": n, "rank": i}
        word_links = []  # links: {"source": "word1", "target": "word2", "value": 1}
        rank = 0
        last_count = 0
        for i1, word1 in enumerate(words, start=1):

            rank = rank if word1[1] == last_count else i1  # need to increment rank?
            nodes.append({'id': word1[0], 'count': word1[1], 'rank': rank})
            last_count = word1[1]

            for i2, word2 in enumerate(words, start=1):
                if i1 > i2:  # skip duplicates
                    sim = w2v.similarity(word1[0], word2[0])
                    if abs(sim) > min_link:  # skip weak relationships
                        # re-range sim from [1:0:-1] to [5:10:15] -- prep for force diagram
                        # TODO: Is this length value okay? Consider strength component to output.
                        word_links.append({'source': word1[0], 'target': word2[0], 'value': int((sim * -5) + 10)})

        # SAVE JSON (twice)
        self.model_output["word2vec"] = {'w2v_size': size, 'w2v_window': window, 'w2v_min_count': min_count,
                                         'w2v_sg': sg,
                                         'w2v_word_count': len(nodes), 'max_words': max_words, 'min_link': min_link}
        self.model_output['words'] = nodes
        self.model_output['word_links'] = word_links

    def export_json(self):
        """
        Aggregates analytics results from word2vec (required), summary_sentence, and summary_words and save
        as a json file for presentation.
        :return: None
        """

        # with open(OUTPUT_DIR + 'analysis_' + self.corpus_name + '.json', 'w') as f:
        with open(OUTPUT_DIR + 'analysis.json', 'w') as f:
            json.dump(self.model_output, f)


if __name__ == "__main__":
    txt = """And the king of Egypt called for the midwives, and said unto them, Why have ye done this thing, and have
        saved the men children alive? And the midwives said unto Pharaoh, Because the Hebrew women are not as
        the Egyptian women; for they are lively, and are delivered ere the midwives come in unto them.
        Therefore God dealt well with the midwives: and the people multiplied, and waxed very mighty.
        And it came to pass, because the midwives feared God, that he made them houses. And Pharaoh charged
        all his people, saying, Every son that is born ye shall cast into the river, and every daughter ye
        shall save alive."""
    AnalyticsFactory(txt, 'exo1f')
