"""
Running this file makes all of the key stuff happen.
"""
# TODO: Add a C/H getter

# IMPORTS
import get_bible_texts
import topic_builder
import ana_factory

# GLOBALS: Used these variables to define most common run parameters.
# Note that most methods have settable parameters that you may want to adjust.
OUTPUT_DIR = 'Output/'
ORIG_CORPUS = ""  # An optional corpus (used for comparison); formatting may be critical for get_.

USE_GRAPH_DB = False
MAX_TOPICS = 50


# RUN
# Get the Corpus
bt = get_bible_texts.getBibleTexts("Hosea")  # Get properly formatted corpus (dictionary: { reference: text })
texts = bt.get_texts()
reference = bt.reference
if USE_GRAPH_DB:
    get_bible_texts.db_add_posts(texts, db_start_fresh=False)


# Run it through Topic Builder (tokenizer, graph db set up, find topics)
tb = topic_builder.TopicBuilder(reference, texts, USE_GRAPH_DB, MAX_TOPICS)
tb.nouns()

# Word2Vec; find key sentences, and key words.
# ana = ana_factory.AnalyticsFactory(new_texts, NEW_CORPUS)
# ana.key_sentences(tb.text_concat_raw())
# ana.keywords(tb.text_concat_raw())
# ana.word2vec(tb.text_token_concat_clean())
# ana.doc2vec(tb.text_token_dict_clean())
# ana.export_json()


# Compare with original Corpus.
if ORIG_CORPUS:
    # Get the Corpus
    orig_texts = get_bible_texts.main(ORIG_CORPUS)
    get_bible_texts.db_add_posts(orig_texts, db_start_fresh=True)

    # Run it through Topic Builder (tokenizer, graph db set up, find topics)
    orig_tb = topic_builder.TopicBuilder(ORIG_CORPUS, orig_texts, use_graph_db=False)
    tb.compare(orig_tb.nouns())  # note: based on the

tb.export_topics(OUTPUT_DIR, date_file_name=False)
bt.export_texts(OUTPUT_DIR)


