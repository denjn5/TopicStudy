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

# GLOBALS
# TODO: Handle globals consistently: either jump into middle or pass through as properties. Prob'ly that one.
NEW_CORPUS = "Mat 4"  # (str) The corpus where we'll do detailed analysis; formatting may be critical for get_.
ORIG_CORPUS = "Mat 3"  # (str) An optional corpus (used for comparison); formatting may be critical for get_.

USE_GRAPH_DB = False


# RUN
# Get the Corpus
new_texts = get_bible.main(NEW_CORPUS)  # Get properly formatted corpus (dictionary: { reference: text })
get_bible.db_add_posts(new_texts, db_start_fresh=False)

# Run it through Topic Builder (tokenizer, graph db set up, find topics)
new_tb = ana_topics.TopicBuilder(NEW_CORPUS, new_texts, USE_GRAPH_DB)
new_topics = new_tb.find_nouns()

# Word2Vec; find key sentences, and key words.
ana = ana_factory.AnalyticsFactory(new_texts, NEW_CORPUS)

ana.key_sentence(new_tb.texts_concat_raw())
ana.keywords(new_tb.texts_concat_raw())
ana.build_word2vec(new_tb.tokens_concat_clean())
ana.build_doc2vec(new_tb.tokens_dict_clean())
ana.export_json()

# Compare with original Corpus.
if ORIG_CORPUS:
    # Get the Corpus
    orig_texts = get_bible.main(ORIG_CORPUS)
    get_bible.db_add_posts(orig_texts, db_start_fresh=True)

    # Run it through Topic Builder (tokenizer, graph db set up, find topics)
    orig_tb = ana_topics.TopicBuilder(ORIG_CORPUS, orig_texts, use_graph_db=False)
    orig_topics = orig_tb.find_nouns()

    # Run comparison
    new_tb.compare(orig_topics)  # note: based on the

new_tb.json_export()
