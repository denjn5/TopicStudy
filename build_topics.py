"""
Explains POS Tags: http://universaldependencies.org/en/pos/all.html#al-en-pos/DET
"""


# IMPORTS
import spacy
import spacy.symbols as ss
import graph_db
import string

# GLOBALS
SRC_DIR = 'Texts/'
MODEL_DIR = 'Models/'
NOUNS = {ss.NOUN, ss.PROPN, ss.PRON}


class TopicBuilder:
    nlp = spacy.load('en')


    def __init__(self, source):
        """
        :param source: The name of the source (e.g., 20170101, Mat1)
        """
        self.source = source
        self.gt = graph_db.GraphManager(source)
        # self.gt.source = source.lower().replace(' ', '')
        # self.gt.source(source)

    def _tokenizer(self):
        """
        Tokenize the text that we're studying.
        """

        # STOP WORDS
        # with open(SRC_DIR + 'stopwords.txt', 'r') as file:
        #    stopwords = set(file.read().split(' '))

        # PARSE & CLEAN: lowercase; lemmatize; eliminate stopwords, punctuation, numbers
        # self.clean_tokens = [[str(word.lemma_).lower() for word in sent
        #                      if (str(word).lower() not in stopwords) and word.is_alpha]  # str(word).isalpha()
        #                      for sent in self.tokens]  # eliminate single-use words?
        # self.clean_tokens = [s for s in self.clean_tokens if s]  # remove empty sentences
        # self.clean_text = ' '.join([' '.join([str(c) for c in lst]) for lst in self.clean_tokens])

    def analyze_phrases(self, token, source_type, source_key, skip_ahead):
        """
        Start with a token, find it's explanatory phrase. Then create Topic and Phrase nodes.  Then link those 
        together and to Post nodes.
        :param token: A noun, pronoun, or proper noun; the topic
        :param source_type: "POST" or "PHRASE"
        :param source_key: A unique string representation of the source
        :param skip_ahead: All words before this index (token.i) have been addressed; avoids double-counting and loops 
        :return: The new skip_ahead value
        """

        # Create Topic node; use the token lemma as the key.
        topic = token.lemma_
        self.gt.topic(topic)
        self.gt.source_to_topic(self.source, topic)

        # Get the subtree of the token.
        subtree = list(token.subtree)

        # If the Topic and Subtree Phrase are equal, write the topic and link it to the post.
        if len(subtree) == 1:
            if source_type == "PHRASE":
                self.gt.phrase_to_topic(source_key, topic)
            else:  # source is POST
                self.gt.post_to_topic(source_key, topic)

        # The Subtree Phrase is bigger than the Topic. Create the Phrase, then save to the db and link
        else:
            phrase = ''.join([word.lemma_ for word in subtree])
            phrase = ''.join(char for char in phrase if char not in string.punctuation)
            verbatim = ' '.join([str(word) for word in subtree]).replace(" ,", ",").replace(" ;", ";")
            verbatim = verbatim.strip(string.punctuation)

            self.gt.phrase(phrase, verbatim)
            self.gt.phrase_to_topic(phrase, topic)

            if source_type == "PHRASE":
                self.gt.phrase_to_phrase(source_key, phrase)
            else:  # source is POST
                self.gt.post_to_phrase(source_key, phrase)

            # Are there additional nouns in the Subtree? Loop through them and call this method recursively.
            nouns = [word for word in subtree if word.pos in NOUNS and word.i > skip_ahead]
            for n in range(0, len(nouns)):
                if n > 0 and nouns[n].i > skip_ahead:
                    skip_ahead = self.analyze_phrases(nouns[n], "PHRASE", phrase, skip_ahead)

        # skip_ahead: The index of the final word addressed in the Subtree. This avoids dupe work.
        return subtree[-1].i

    def find_phrases(self, texts):
        """
        Loop through each dictionary entry in texts; analyze the text for nouns
        :param texts: 
        :return: 
        """
        for reference in texts:
            skip_ahead = -1

            tokens = [word for word in self.nlp(texts[reference])]
            for token in tokens:
                if token.pos in NOUNS and token.i > skip_ahead:
                    skip_ahead = self.analyze_phrases(token, "POST", reference, skip_ahead)
