"""
Running this file makes all of the key stuff happen.
"""

import common
import bible
import tfidf
import topic
import vec_relationships


MAX_TOPICS = 40
SAVE_SOURCE = False
USE_LOCAL_SOURCE=True


def main():
    # GET THE TEXTS
    bib = bible.Bible("Proverbs")  # Get properly formatted corpus (a python list of dictionaries).
    texts = bib.get_texts(save_source=SAVE_SOURCE, use_local_source=USE_LOCAL_SOURCE)
    corpus_name = bib.corpus_name

    if len(bib) == 0:  # calls bible.__len__
        print("No data from get_. Check your args.")
        return

    # ADD SENTIMENT
    common.add_sentiment(texts, bib.df_texts)


    # FIND TOPICS
    tb = topic.Topic(corpus_name, texts)
    tb.detect_ngram()
    tb.prune_topics_and_adopt()
    # summary = tb.summarize_texts()

    # tfidf.tfidf_tutorial(texts)

    vr = vec_relationships.VecRelationships(corpus_name, texts)
    # vr.doc2vec()
    vr.word2vec()
    vr.export_json()

    # summary['keySentences'] = fr.key_sentences(summary['text'])
    # TODO: send in clean tokens to keywords
    # summary['keyWords'] = fr.keywords(summary['text'])
    # fr.word2vec(tb.text_token_concat_clean())
    # fr.export_json()

    # SEND IT TO JSON
    tb.export_topics()
    common.export_texts(texts, corpus_name)


if __name__ == "__main__":
    main()


