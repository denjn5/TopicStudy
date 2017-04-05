"""
Running this file makes all of the key stuff happen.
"""
# TODO: How do I let users choose which options to output simply?
# TODO: Add option for users who don't have neo4j installed.
# TODO: Create a very simple raw dictionary file for input as an example.
# TODO: Add a C/H getter

# IMPORTS
import get_bible
import ana_topics
import ana_factory

# GLOBALS: Used these variables to define most common run parameters.
# Note that most methods have settable parameters that you may want to adjust.
NEW_CORPUS = "Mat"  # (str) The corpus where we'll do detailed analysis; formatting may be critical for get_.
ORIG_CORPUS = ""  # (str) An optional corpus (used for comparison); formatting may be critical for get_.

USE_GRAPH_DB = False


# RUN
# Get the Corpus
new_texts = get_bible.main(NEW_CORPUS)  # Get properly formatted corpus (dictionary: { reference: text })
get_bible.db_add_posts(new_texts, db_start_fresh=False)

# Run it through Topic Builder (tokenizer, graph db set up, find topics)
tb = ana_topics.TopicBuilder(NEW_CORPUS, new_texts, USE_GRAPH_DB)
new_topics = tb.nouns()

# Word2Vec; find key sentences, and key words.
ana = ana_factory.AnalyticsFactory(new_texts, NEW_CORPUS)

ana.key_sentences(tb.text_concat_raw())
ana.keywords(tb.text_concat_raw())
ana.word2vec(tb.text_token_concat_clean())
ana.doc2vec(tb.text_token_dict_clean())
ana.export_json()


# Compare with original Corpus.
if ORIG_CORPUS:
    # Get the Corpus
    orig_texts = get_bible.main(ORIG_CORPUS)
    get_bible.db_add_posts(orig_texts, db_start_fresh=True)

    # Run it through Topic Builder (tokenizer, graph db set up, find topics)
    orig_tb = ana_topics.TopicBuilder(ORIG_CORPUS, orig_texts, use_graph_db=False)
    orig_topics = orig_tb.nouns()

    # Run comparison
    tb.compare(orig_topics)  # note: based on the

tb.export_json()
