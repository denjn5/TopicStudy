import gensim
from collections import defaultdict

def tfidf_tutorial(texts_in):

    texts = [text['tokensClean'] for id, text in texts_in.items()]

    # documents = ["Human machine interface for lab abc computer applications",
    #              "A survey of user opinion of computer system response time",
    #              "The EPS user interface management system",
    #              "System and human system engineering testing of EPS",
    #              "Relation of user perceived response time to error measurement",
    #              "The generation of random binary unordered trees",
    #              "The intersection graph of paths in trees",
    #              "Graph minors IV Widths of trees and well quasi ordering",
    #              "Graph minors A survey"]
    #
    # # remove common words and tokenize
    # stoplist = set('for a of the and to in'.split())
    # texts = [[word for word in document.lower().split() if word not in stoplist]
    #          for document in documents]
    #
    # # remove words that appear only once
    # frequency = defaultdict(int)
    # for text in texts:
    #     for token in text:
    #         frequency[token] += 1
    #
    # texts = [[token for token in text if frequency[token] > 1] for text in texts]
    #
    # print()
    # print('*'*10 + 'texts' + '*'*10)
    # print(texts)

    dictionary = gensim.corpora.Dictionary(texts)
    # dictionary.save('/tmp/texts.dict')  # store the dictionary, for future reference

    corpus = [dictionary.doc2bow(text) for text in texts]
    # gensim.corpora.MmCorpus.serialize('/tmp/texts.mm', corpus)  # store to disk, for later use

    tfidf = gensim.models.TfidfModel(corpus)
    corpus_tfidf = tfidf[corpus]

    print()
    print('*'*10 + 'results' + '*'*10)
    tfidf_result = [[dictionary.get(id), value] for doc in corpus_tfidf for id, value in doc]
    result = sorted(tfidf_result, key=lambda t: t[1], reverse=True)

    print(result)

    d = {}
    for t in tfidf_result:
        if t[0] in d:
            d[t[0]] += t[1]
        else:
            d[t[0]] = t[1]

    print(d)

    x = 'hello'
