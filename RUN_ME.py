"""
Running this file makes all of the key stuff happen.
"""

import common
import get_bible
import tfidf
import topic_builder
import vec_relationships


MAX_TOPICS = 40
SAVE_SOURCE = True
USE_LOCAL_SOURCE=False


def main():
    # GET THE TEXTS
    bt = get_bible.GetBible("Psalms")  # Get properly formatted corpus (a python list of dictionaries).
    texts = bt.get_texts(save_source=SAVE_SOURCE, use_local_source=USE_LOCAL_SOURCE)
    corpus_name = bt.corpus_name

    if len(texts) == 0:
        print("No data from get_. Check your args.")
        return

    # ADD SENTIMENT
    sent = common.add_sentiment(texts)

    # FIND TOPICS
    tb = topic_builder.TopicBuilder(corpus_name, texts, max_topics=40)
    tb.ngram_detection()
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


