"""
Running this file makes all of the key stuff happen.
"""
# TODO: Add a C/H getter

# IMPORTS
import get_bible_texts
import topic_builder
import sentiment
import find_relationships

# GLOBALS: Used these variables to define most common run parameters.
# Note that most methods have settable parameters that you may want to adjust.
ORIG_CORPUS = ""  # An optional corpus (used for comparison); formatting may be critical for get_.
USE_GRAPH_DB = False


# RUN
# Get the Corpus
bt = get_bible_texts.getBibleTexts("Proverbs")  # Get properly formatted corpus (a python list of dictionaries).
texts = bt.get_texts()
corpus_name = bt.corpus_name
if USE_GRAPH_DB:
    get_bible_texts.db_add_posts(texts, db_start_fresh=False)


sent = sentiment.calculateSentiment(texts)
sent.add_sentiment()

# Run it through Topic Builder (tokenizer, graph db set up, find topics)
tb = topic_builder.TopicBuilder(corpus_name, texts, USE_GRAPH_DB)
tb.nouns()
summary = tb.summarize_texts()

# Word2Vec; find key sentences, and key words.
fr = find_relationships.FindRelationships(texts, corpus_name)

summary['keySentences'] = fr.key_sentences(summary['text'])
# TODO: send in clean tokens to keywords
summary['keyWords'] = fr.keywords(summary['text'])
# fr.word2vec(tb.text_token_concat_clean())
# fr.doc2vec(tb.text_token_dict_clean())
# fr.export_json()


# Compare with original Corpus.
if ORIG_CORPUS:
    # Get the Corpus
    orig_texts = get_bible_texts.main(ORIG_CORPUS)
    get_bible_texts.db_add_posts(orig_texts, db_start_fresh=True)

    # Run it through Topic Builder (tokenizer, graph db set up, find topics)
    orig_tb = topic_builder.TopicBuilder(ORIG_CORPUS, orig_texts, use_graph_db=False)
    tb.compare(orig_tb.nouns())  # note: based on the

tb.export_topics()
bt.export_texts()


