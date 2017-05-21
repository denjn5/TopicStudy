"""
Running this file makes all of the key stuff happen.
"""

# IMPORTS
import get_bible_texts
import topic_builder
import sentiment
import find_relationships
import tfidf


# GLOBALS: Used these variables to define most common run parameters.
# Note that most methods have settable parameters that you may want to adjust.
ORIG_CORPUS = ""  # An optional corpus (used for comparison); formatting may be critical for get_.



# GET THE TEXTS
bt = get_bible_texts.getBibleTexts("Mark")  # Get properly formatted corpus (a python list of dictionaries).
texts = bt.get_texts()
corpus_name = bt.corpus_name


# ADD SENTIMENT
sent = sentiment.calculateSentiment(texts)
sent.add_sentiment()

# FIND TOPICS
tb = topic_builder.TopicBuilder(corpus_name, texts, max_topics=65)
tb.topic_finder()
# summary = tb.summarize_texts()

# tfidf.tfidf_tutorial(texts)

# Word2Vec; find key sentences, and key words.
# fr = find_relationships.FindRelationships(texts, corpus_name)

# summary['keySentences'] = fr.key_sentences(summary['text'])
# TODO: send in clean tokens to keywords
# summary['keyWords'] = fr.keywords(summary['text'])
# fr.word2vec(tb.text_token_concat_clean())
# fr.doc2vec(tb.text_token_dict_clean())
# fr.export_json()

# SEND IT TO JSON
tb.export_topics()
bt.export_texts()


