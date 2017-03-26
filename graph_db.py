"""
Graph DB Design
A KEY is unique, so new found instances are merged.

NODES
* top:Topic. KEY: "topic" = Single-word lemma; could be a single concept (e.g., StarWars).
    DEF: The simplest set of topics, usually nouns. This is what we'll study at the end of it all.
* phr:Phrase. KEY: "lemma" = Multi-word lemma.
    DEF: A, usually short, phrase intended to provide context for the topics.
    Phrases generally sit between Topics and Posts.
    PROPERTIES: "verbatim" = The 1st quoted example found. The lemma is good for grouping, this best for comprehension.
* pst:Post. KEY = The reference to a single text in the corpus. You must decide a unique key based on your application
    (e.g., for social, URL; For Bible, the verse reference).
    DEF: This would be a single post in social (Tweet, article) or verse in the Bible.
    PROPERTIES: "quote" = A quote from the post. Either the title or first couple of sentences.
* src:Source Node. KEY = A single word identifier that helps group Posts (e.g., "Twitter", "Reddit", "John 3").
    DEF: An optional helper to allow topics to be grouped by Source.

LINKS
* srcref:Source->Post. DEF: A simple tracking link. No properties.
* pstphr:Post->Phrase. DEF: Count links between Posts and Phrases.
    PROPERTIES: "count" = An incremented value of how often this phrase was found in this post.
* topcnt:Phrase->Topic. DEF: Count links between Phrases and Topics.
    PROPERTIES: "count" = An incremented value of how often this topic was found in this phrase.
* topcnt:Post->Topic. DEF: Count links between Posts and Topics (used when the Phrase = Topic).
    PROPERTIES: "count" = An incremented value of how often this topic was found in this post.

QUERIES
* return all phrases and topics with links: MATCH (n:Phrase)-[:TOP]->(m:Topic) RETURN n,m
* return topics by count: MATCH (n:Topic) RETURN n ORDER BY n.count DESC
"""
# TODO: Date tracking for social: (a) node (good design; pain for study), (b) link property (2016-04-05: 21).

# IMPORTS
from neo4j.v1 import GraphDatabase, basic_auth

# GLOBAL CONNECTION STRINGS
URI2 = 'bolt://127.0.0.1:7687'  # localhost
SHOW_LOG = False


# GLOBAL NODE (CYPHER)
POST_NODE = """MERGE (pst:Post {{ reference:'{r}' }}) 
    ON CREATE SET pst.quote = '{q}'
    RETURN pst.reference"""

PHRASE_NODE = """MERGE (phr:Phrase {{ lemma:'{l}' }}) 
    ON CREATE SET phr.verbatim = '{v}' 
    RETURN phr.lemma"""

SOURCE_NODE = """MERGE (src:Source {{ source:'{s}' }}) 
    RETURN src.source"""

TOPIC_NODE2 = """MERGE (top:Topic {{ topic:'{t}' }})
    ON CREATE SET top.count = 0
    RETURN top.topic"""
TOPIC_NODE = """MERGE (top:Topic {{ topic:'{t}' }})
    ON CREATE SET top.{c} = 0
    RETURN top.topic"""

# GLOBAL INDEX (CYPHER)
POST_INDEX = 'CREATE CONSTRAINT ON (pst:Post) ASSERT pst.reference IS UNIQUE'
PHRASE_INDEX = 'CREATE CONSTRAINT ON (phr:Phrase) ASSERT phr.lemma IS UNIQUE'
SOURCE_INDEX = 'CREATE CONSTRAINT ON (src:Source) ASSERT src.source IS UNIQUE'
TOPIC_INDEX = 'CREATE CONSTRAINT ON (top:Topic) ASSERT top.topic IS UNIQUE'


# GLOBAL LINK (CYPHER)
SRC_TOP_LINK = """MATCH (src:Source), (top:Topic)
    WHERE top.topic = '{t}' AND src.source = '{s}'
    MERGE (src)-[srctop:SRC]->(top)
    RETURN srctop"""

PHR_TOP_LINK = """MATCH (phr:Phrase), (top:Topic)
    WHERE top.topic = '{t}' AND phr.lemma = '{l}'
    MERGE (phr)-[phrtop:TOP]->(top)
    SET top.{c} = top.{c} + 1
    RETURN phrtop"""

PHR_PHR_LINK = """MATCH (phr1:Phrase), (phr2:Phrase)
    WHERE phr1.lemma = '{l1}' AND phr2.lemma = '{l2}'
    MERGE (phr1)-[phrphr:PHR]->(phr2)
    RETURN phrphr"""

PST_TOP_LINK = """MATCH (pst:Post), (top:Topic)
    WHERE top.topic = '{t}' AND pst.reference = '{r}'
    MERGE (pst)-[psttop:TOP]->(top)
    SET top.{c} = top.{c} + 1
    RETURN psttop"""

PST_PHR_LINK = """MATCH (pst:Post), (phr:Phrase)
    WHERE phr.lemma = '{l}' AND pst.reference = '{r}'
    MERGE (pst)-[pstphr:PHR]->(phr)
    RETURN pstphr"""


class GraphManager:
    driver = GraphDatabase.driver(URI2, auth=basic_auth("neo4j", "nlp"))

    def __init__(self, source=""):
        # Connect to the Graph DB.
        self.session = self.driver.session()
        self.session.run(POST_INDEX)
        self.session.run(PHRASE_INDEX)
        self.session.run(SOURCE_INDEX)
        self.session.run(TOPIC_INDEX)
        self.source = source.lower().replace(' ', '')

    def post(self, reference, quote):
        # pst = self.session.run(POST_NODE, {"reference": reference, "quote": quote})

        pst = self.session.run(POST_NODE.format(r=reference, q=quote))
        self.print_log(pst)

    def topic(self, topic):
        top = self.session.run(TOPIC_NODE.format(t=topic, c=self.source))
        self.print_log(top)

    # def source(self, source):
    #
    #     src = self.session.run(SOURCE_NODE.format(s=source))
    #     self.source = source.lower().replace(' ', '')
    #     self.print_log(src)

    def phrase(self, lemma, verbatim):
        phr = self.session.run(PHRASE_NODE.format(l=lemma, v=verbatim))
        self.print_log(phr)

    def source_to_topic(self, source, topic):
        srctop = self.session.run(SRC_TOP_LINK.format(s=source, t=topic))
        self.print_log(srctop)

    def post_to_phrase(self, reference, lemma):
        pstphr = self.session.run(PST_PHR_LINK.format(r=reference, l=lemma))
        self.print_log(pstphr)

    def post_to_topic(self, reference, topic):
        psttop = self.session.run(PST_TOP_LINK.format(r=reference, t=topic, c=self.source))
        self.print_log(psttop)

    def phrase_to_topic(self, lemma, topic):
        phrtop = self.session.run(PHR_TOP_LINK.format(l=lemma, t=topic, c=self.source))
        self.print_log(phrtop)

    def phrase_to_phrase(self, lemma_1, lemma_2):
        phrphr = self.session.run(PHR_PHR_LINK.format(l1=lemma_1, l2=lemma_2))
        self.print_log(phrphr)

    def close(self):
        # self.session.close()
        jmm = "hmmm"

    def delete_all(self):
        self.session.run("MATCH (n) DETACH DELETE n")

    def print_log(self, return_object):
        if SHOW_LOG:
            new_objects = return_object.data()
            new_object = new_objects[0] if len(new_objects) > 0 else "###uh oh###"
            print(str(new_object))
