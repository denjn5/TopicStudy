"""
Graph DB Design
A KEY is unique, so new found instances are merged.

NODES
* top:Topic. KEY: "topic" = Single-word lemma; could be a single concept (e.g., StarWars).
    DEF: The simplest set of topics, usually nouns. This is what we'll study at the end of it all.
* phr:Phrase. KEY: "lemma" = Multi-word lemma.
    DEF: A, usually short, phrase intended to provide context for the topics.
    Phrases generally sit between Topics and Sources.
    PROPERTIES: "verbatim" = The 1st quoted example found. The lemma is good for grouping, this best for comprehension.
* src:Source. KEY = The reference to a single text in the corpus. You must decide a unique key based on your application
    (e.g., for social, URL; For Bible, the verse reference).
    DEF: This would be a single source in social (Tweet, article) or verse in the Bible.
    PROPERTIES: "quote" = A quote from the source. Either the title or first couple of sentences.
* grp:Group Node. KEY = A single word identifier that helps group Sources (e.g., "Twitter", "Reddit", "John 3").
    DEF: An optional helper to allow topics to be grouped by Group.

LINKS
* grpref:Group->Source. DEF: A simple tracking link. No properties.
* srcphr:Source->Phrase. DEF: Count links between Sources and Phrases.
    PROPERTIES: "count" = An incremented value of how often this phrase was found in this source.
* topcnt:Phrase->Topic. DEF: Count links between Phrases and Topics.
    PROPERTIES: "count" = An incremented value of how often this topic was found in this phrase.
* topcnt:Source->Topic. DEF: Count links between Sources and Topics (used when the Phrase = Topic).
    PROPERTIES: "count" = An incremented value of how often this topic was found in this source.

QUERIES
* return all phrases and topics with links: MATCH (n:Phrase)-[:TOP]->(m:Topic) RETURN n,m
* return topics by count: MATCH (n:Topic) RETURN n ORDER BY n.count DESC
* return Topic nodes that have a mat2 link, but no mat2 count: 
    MATCH (top:Topic)-[l:mat2]-() 
    WHERE NOT EXISTS(top.mat2) 
    SET top.mat2 = 0
    RETURN top
* Return Topics and counts by Group (based on link):
    MATCH (top:Topic)
    WHERE (top)-[:mat1]-() OR (top)-[:mat2]-()
    RETURN top.topic, top.mat2, top.mat1
"""
# TODO: Date tracking for social: (a) node (good design; pain for study), (b) link property (2016-04-05: 21).

# IMPORTS
from neo4j.v1 import GraphDatabase, basic_auth

# GLOBAL CONNECTION STRINGS
URI2 = 'bolt://127.0.0.1:7687'  # localhost
SHOW_LOG = False


# GLOBAL NODE (CYPHER)
SOURCE_NODE = """MERGE (src:Source {{ reference:'{r}' }}) 
    ON CREATE SET src.quote = '{q}'
    RETURN src.reference"""

PHRASE_NODE = """MERGE (phr:Phrase {{ lemma:'{l}' }}) 
    ON CREATE SET phr.verbatim = '{v}' 
    RETURN phr.lemma"""

GROUP_NODE = """MERGE (grp:Group {{ group:'{g}' }}) 
    RETURN grp.group"""

TOPIC_NODE = """MERGE (top:Topic {{ topic:'{t}' }})
    ON CREATE SET top.{c} = 0
    RETURN top.topic, top.{c}"""

# GLOBAL INDEX (CYPHER)
SOURCE_INDEX = 'CREATE CONSTRAINT ON (src:Source) ASSERT src.reference IS UNIQUE'
PHRASE_INDEX = 'CREATE CONSTRAINT ON (phr:Phrase) ASSERT phr.lemma IS UNIQUE'
GROUP_INDEX = 'CREATE CONSTRAINT ON (grp:Group) ASSERT grp.group IS UNIQUE'
TOPIC_INDEX = 'CREATE CONSTRAINT ON (top:Topic) ASSERT top.topic IS UNIQUE'


# GLOBAL LINK (CYPHER)
# t = topic (word); g = group
GRP_TOP_LINK = """MATCH (grp:Group), (top:Topic)
    WHERE top.topic = '{t}' AND grp.group = '{g}'
    MERGE (grp)-[gt:{g}]-(top)
    RETURN gt"""

# t = topic (word); l = lemma (phrase); g = group (used for count by source and label)
PHR_TOP_LINK = """MATCH (phr:Phrase), (top:Topic)
    WHERE top.topic = '{t}' AND phr.lemma = '{l}'
    MERGE (phr)-[pt:{g}]-(top)
    SET top.{g} = top.{g} + 1
    RETURN pt"""

# l1 = lemma (phrase 1); l2 = lemma (phrase 2); g = group
PHR_PHR_LINK = """MATCH (phr1:Phrase), (phr2:Phrase)
    WHERE phr1.lemma = '{l1}' AND phr2.lemma = '{l2}'
    MERGE (phr1)-[pp:{g}]-(phr2)
    RETURN pp"""

# t = topic (word); r = reference (source); g = group (used for count by source and label)
SRC_TOP_LINK = """MATCH (src:Source), (top:Topic)
    WHERE top.topic = '{t}' AND src.reference = '{r}'
    MERGE (src)-[st:{g}]-(top)
    SET top.{g} = top.{g} + 1
    RETURN st"""

# l = lemma (phrase); r = reference (source); g = group
SRC_PHR_LINK = """MATCH (src:Source), (phr:Phrase)
    WHERE phr.lemma = '{l}' AND src.reference = '{r}'
    MERGE (src)-[sp:{g}]-(phr)
    RETURN sp"""


class GraphManager:
    driver = GraphDatabase.driver(URI2, auth=basic_auth("neo4j", "nlp"))

    def __init__(self, group=""):
        # Connect to the Graph DB.
        self.session = self.driver.session()
        self.session.run(SOURCE_INDEX)
        self.session.run(PHRASE_INDEX)
        self.session.run(GROUP_INDEX)
        self.session.run(TOPIC_INDEX)
        self.group = group.lower().replace(' ', '')

    def source(self, reference, quote):
        # src = self.session.run(POST_NODE, {"reference": reference, "quote": quote})

        src = self.session.run(SOURCE_NODE.format(r=reference, q=quote.replace("'","")))
        self.print_log(src)

    def topic(self, topic):
        top = self.session.run(TOPIC_NODE.format(t=topic, c=self.group))
        top = self.print_log(top)

    def grouping(self):
        grp = self.session.run(GROUP_NODE.format(g=self.group))
        self.print_log(grp)

    def phrase(self, lemma, verbatim):
        phr = self.session.run(PHRASE_NODE.format(l=lemma, v=verbatim.replace("'","")))
        self.print_log(phr)

    def group_to_topic(self, group, topic):
        gt = self.session.run(GRP_TOP_LINK.format(s=group, t=topic, g=self.group))
        self.print_log(gt)

    def source_to_phrase(self, reference, lemma):
        sp = self.session.run(SRC_PHR_LINK.format(r=reference, l=lemma, g=self.group))
        self.print_log(sp)

    def source_to_topic(self, reference, topic):
        st = self.session.run(SRC_TOP_LINK.format(r=reference, t=topic, g=self.group))
        self.print_log(st)

    def phrase_to_topic(self, lemma, topic):
        pt = self.session.run(PHR_TOP_LINK.format(l=lemma, t=topic, g=self.group))
        self.print_log(pt)

    def phrase_to_phrase(self, lemma_1, lemma_2):
        pp = self.session.run(PHR_PHR_LINK.format(l1=lemma_1, l2=lemma_2, g=self.group))
        self.print_log(pp)

    def delete_all(self):
        self.session.run("MATCH (n) DETACH DELETE n")

    def close(self):
        # TODO: Do I need to close my session? (Calling this currently produces error.)
        self.session.close()

    @staticmethod
    def print_log(neo4j_object):
        neo4j_props = neo4j_object.data()

        if SHOW_LOG:
            new_object = neo4j_props[0] if len(neo4j_props) > 0 else "###uh oh###"
            print(str(new_object))

        return neo4j_props
