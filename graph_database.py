"""
Graph DB Design
A KEY is unique, so new found instances are merged.

NODES
* top:Topic. KEY: "topic" = Single-word lemma; could be a single concept (e.g., StarWars).
    DEF: The simplest set of topics, usually nouns. This is what we'll study at the end of it all.
* phr:Phrase. KEY: "lemma" = Multi-word lemma.
    DEF: A, usually short, phrase intended to provide context for the topics.
    Phrases generally sit between Topics and Texts.
    PROPERTIES: "verbatim" = The 1st quoted example found. The lemma is good for grouping, this best for comprehension.
* txt:Text. KEY = The reference to a single text in the corpus. You must decide a unique key based on your application
    (e.g., for social, URL; For Bible, the verse reference).
    DEF: This would be a single text in social (Tweet, article) or verse in the Bible.
    PROPERTIES: "quote" = A quote from the text. Either the title or first couple of sentences.
* crp:Corpus Node. KEY = A single word identifier that helps group Texts (e.g., "Twitter", "Reddit", "John 3").
    DEF: A Corpus is a group of Texts. This node is optional.  It links Topics to a single Corpus.

LINKS
* crpref:Corpus->Text. DEF: A simple tracking link. No properties.
* txtphr:Text->Phrase. DEF: Count links between Texts and Phrases.
    PROPERTIES: "count" = An incremented value of how often this phrase was found in this text.
* topcnt:Phrase->Topic. DEF: Count links between Phrases and Topics.
    PROPERTIES: "count" = An incremented value of how often this topic was found in this phrase.
* topcnt:Text->Topic. DEF: Count links between Texts and Topics (used when the Phrase = Topic).
    PROPERTIES: "count" = An incremented value of how often this topic was found in this text.

"""
# TODO: Date tracking for social: (a) node (good design; pain for study), (b) link property (2016-04-05: 21).
# FIXME: Is this dropping transactions in neo4j? (Rerunning same text ends up with diff node / link count.)

# IMPORTS
from neo4j.v1 import GraphDatabase, basic_auth

# GLOBAL CONNECTION STRINGS
URI2 = 'bolt://127.0.0.1:7687'  # localhost
SHOW_LOG = False


# GLOBAL NODE (CYPHER)
TEXT_NODE = """MERGE (txt:Text {{ reference:'{r}' }}) 
    ON CREATE SET txt.quote = '{q}', txt.title = '{t}'
    RETURN txt.reference"""

PHRASE_NODE = """MERGE (phr:Phrase {{ lemma:'{l}' }}) 
    ON CREATE SET phr.verbatim = '{v}' 
    RETURN phr.lemma"""

CORPUS_NODE = """MERGE (crp:Corpus {{ corpus:'{c}' }}) 
    RETURN crp.corpus"""

TOPIC_NODE = """MERGE (top:Topic {{ topic:'{t}' }})
    RETURN top.topic, top.{c}"""


# GLOBAL INDEX (CYPHER)
TEXT_INDEX = 'CREATE CONSTRAINT ON (txt:Text) ASSERT txt.reference IS UNIQUE'
PHRASE_INDEX = 'CREATE CONSTRAINT ON (phr:Phrase) ASSERT phr.lemma IS UNIQUE'
CORPUS_INDEX = 'CREATE CONSTRAINT ON (crp:Corpus) ASSERT crp.corpus IS UNIQUE'
TOPIC_INDEX = 'CREATE CONSTRAINT ON (top:Topic) ASSERT top.topic IS UNIQUE'


# GLOBAL LINK (CYPHER)
# t = topic (word); g = corpus
CORPUS_TOPIC_LINK = """MATCH (crp:Corpus), (top:Topic)
    WHERE top.topic = '{t}' AND crp.corpus = '{c}'
    MERGE (crp)-[l:{c}]-(top)
    RETURN l"""

# t = topic (word); l = lemma (phrase); g = corpus (used for count by text and label)
PHRASE_TOPIC_LINK = """MATCH (p:Phrase), (t:Topic)
    WHERE t.topic = '{t}' AND p.lemma = '{l}'
    MERGE (p)-[l:{c}]-(t)
    ON CREATE SET l.count = 1
    ON MATCH SET l.count = l.count + 1
    RETURN l"""

# l1 = lemma (phrase 1); l2 = lemma (phrase 2); g = corpus
PHRASE_PHRASE_LINK = """MATCH (p1:Phrase), (p2:Phrase)
    WHERE p1.lemma = '{l1}' AND p2.lemma = '{l2}'
    MERGE (p1)-[l:{c}]-(p2)
    ON CREATE SET l.count = 1
    ON MATCH SET l.count = l.count + 1
    RETURN l"""

# t = topic (word); r = reference (text); g = corpus (used for count by text and label)
TEXT_TOPIC_LINK = """MATCH (x:Text), (t:Topic)
    WHERE t.topic = '{t}' AND x.reference = '{r}'
    MERGE (x)-[l:{c}]-(t)
    ON CREATE SET l.count = 1
    ON MATCH SET l.count = l.count + 1
    RETURN l"""

# l = lemma (phrase); r = reference (text); g = corpus
TEXT_PHRASE_LINK = """MATCH (x:Text), (p:Phrase)
    WHERE p.lemma = '{l}' AND x.reference = '{r}'
    MERGE (x)-[l:{c}]-(p)
    ON CREATE SET l.count = 1
    ON MATCH SET l.count = l.count + 1
    RETURN l"""


class GraphManager:
    """
    Manages the interaction with the graph db.
    """


    def __init__(self, corpus=""):
        """
        Fire up the GraphManager!  
        :param corpus: (str) The title of the set of texts that we're reviewing (a date or set of references).
        """
        # Connect to the Graph DB.
        self.driver = GraphDatabase.driver(URI2, auth=basic_auth("neo4j", "nlp"))
        self.session = self.driver.session()
        self.session.run(TEXT_INDEX)
        self.session.run(PHRASE_INDEX)
        self.session.run(CORPUS_INDEX)
        self.session.run(TOPIC_INDEX)
        self.corpus = corpus.lower().replace(' ', '')
        crp = self.session.run(CORPUS_NODE.format(c=self.corpus))
        self.print_log(crp)

    def text(self, reference, quote, title=""):
        """
        Add a Text to our graph db.
        :param reference: (str) The unique reference for this texts (e.g., URL).
        :param quote: (str) The actual texts (or a subset of it)
        :param title: (str) The title of the texts (optional)
        :return: 
        """
        # TODO: Add title as property (only when filled in?)
        quote = quote.replace("'", "").replace('"', '')
        title = title.replace("'", "").replace('"', '')
        txt = self.session.run(TEXT_NODE.format(r=reference, q=quote, t=title))
        self.print_log(txt)

    def texts(self, texts):
        """
        Add a series of Input to our graph db (s a transaction).
        :param texts: (str) A dictionary of entries.
        :return: 
        """
        # FIXME: Complete this method
        with self.driver.session() as session:
            for ref in texts:
                quote = texts[ref].replace("'", "").replace('"', '')
                session.write_transaction(TEXT_NODE.format(r=ref, q=quote))

            # session.read_transaction(print_friends, "Arthur")

    def topic(self, topic):
        """
        Add a Topic node to our graph db.
        :param topic: (str) The name of the topic.
        :return: none
        """
        top = self.session.run(TOPIC_NODE.format(t=topic, c=self.corpus))
        self.print_log(top)

    def phrase(self, lemma, verbatim):
        """
        Add a Phrase node to our graph db.
        :param lemma: The lemmatized version of our phrase (helps with grouping)
        :param verbatim: The verbatim quote of the phrase (show to users). All but the first instance is ignored.
        :return: 
        """
        verbatim = verbatim.replace("'", "").replace('"', '')
        phr = self.session.run(PHRASE_NODE.format(l=lemma, v=verbatim))
        self.print_log(phr)

    def corpus_to_topic(self, topic):
        """
        Add a Corpus node to Topic node link.
        :param topic: (str) Topic that the Corpus should link to.
        :return: 
        """
        link = self.session.run(CORPUS_TOPIC_LINK.format(c=self.corpus, t=topic))
        self.print_log(link)

    def text_to_phrase(self, reference, lemma):
        """
        Add a link between a Text node and a Phrase node.
        :param reference: The unique identifier for the Text node.
        :param lemma: The unique identifier for the Phrase node.
        :return: 
        """
        link = self.session.run(TEXT_PHRASE_LINK.format(r=reference, l=lemma, c=self.corpus))
        self.print_log(link)

    def text_to_topic(self, reference, topic):
        """
        Add a link between a Text node and a Topic node.
        :param reference: the unique identifier for the Text node.
        :param topic: The unique identifier for the Topic node.
        :return: 
        """
        link = self.session.run(TEXT_TOPIC_LINK.format(r=reference, t=topic, c=self.corpus))
        self.print_log(link)

    def phrase_to_topic(self, lemma, topic):
        """
        Add a link between a Phrase node and a Topic node.
        :param lemma: The unique identifier for the Phrase node.
        :param topic: The unique identifier for the Topic node.
        :return: 
        """
        link = self.session.run(PHRASE_TOPIC_LINK.format(l=lemma, t=topic, c=self.corpus))
        self.print_log(link)

    def phrase_to_phrase(self, lemma_1, lemma_2):
        """
        Add a link between a Phrase node and a Topic node.
        :param lemma_1: The unique identifier for the first Phrase node (the one closer to the Text).
        :param lemma_2: The unique identifier for the second Phrase node (the one closer to the Topic).
        :return: 
        """
        link = self.session.run(PHRASE_PHRASE_LINK.format(l1=lemma_1, l2=lemma_2, c=self.corpus))
        self.print_log(link)

    def delete_all(self):
        """
        Delete all nodes and links in the graph db.
        :return: 
        """
        self.session.run("MATCH (n) DETACH DELETE n")

    def close(self):
        """
        Close the graph db session after a transaction.
        :return: 
        """
        # TODO: Do I need to close my session? (Calling this currently produces error.)
        self.session.close()

    @staticmethod
    def print_log(neo4j_object):
        """
        Print a "log" to screen of the returned object. Note if the object wasn't returned successfully.
        :rtype: object
        """
        neo4j_props = neo4j_object.data()

        if SHOW_LOG:
            new_object = neo4j_props[0] if len(neo4j_props) > 0 else "###UH OH###"
            print(str(new_object))

        return neo4j_props
