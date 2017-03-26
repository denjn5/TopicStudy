"""
MATCH (ee:Person) WHERE ee.name = "Emil"
CREATE (js:Person { name: "Johan", from: "Sweden", learn: "surfing" }),
(ir:Person { name: "Ian", from: "England", title: "author" }),
(rvb:Person { name: "Rik", from: "Belgium", pet: "Orval" }),
(ally:Person { name: "Allison", from: "California", hobby: "surfing" }),
(ee)-[:KNOWS {since: 2001}]->(js),(ee)-[:KNOWS {rating: 5}]->(ir),
(js)-[:KNOWS]->(ir),(js)-[:KNOWS]->(rvb),
(ir)-[:KNOWS]->(js),(ir)-[:KNOWS]->(ally),
(rvb)-[:KNOWS]->(ally)

MATCH (ee:Person)-[:KNOWS]-(friends)
WHERE ee.name = "Emil" RETURN ee, friends

MATCH (js:Person)-[:KNOWS]-()-[:KNOWS]-(surfer)
WHERE js.name = "Johan" AND surfer.hobby = "surfing"
RETURN DISTINCT surfer
"""

# with self.session.begin_transaction() as tx:
#     tx.run(TEMPL_TOPIC, {'key': id, 'topic': lemma, 'count': 1})
#     tx.success = True


from neo4j.v1 import GraphDatabase, basic_auth

URI2 = 'bolt://localhost:7687'
URI = 'http://localhost:7474/browser/'
NODE_TOPIC = 'CREATE (a:Topic {topic: {topic}, keyid: {keyid}, count: 1})'  # {'key': id, 'name': lemma, 'count': 1}
NODE_PHRASE = 'CREATE ({key}:Phrase {topic: {phrase}, count: {count}})'  # {'key': id, 'phrase': phrase, 'count': 1}
LINK_TOP_PHR = 'CREATE ({orig_id)-[:KNOWS {since: 2001}]->({dest_id})'  # {'orig_id': orig_id, 'dest_id': dest_id}

class GraphManager:
    driver = None
    session = None

    def __init__(self):
        self.driver = GraphDatabase.driver(URI2, auth=basic_auth("neo4j", "nlp"))
        self.session = self.driver.session()

    def new_topic(self, keyid, lemma):
        topic_record = self.session.run("MATCH (a:Topic) WHERE a.keyid = {keyid} RETURN a", {"keyid": keyid})
        topic_record = list(topic_record)[0]
        topic_count = topic_record.values()[topic_record.index('a.count')]

        # self.session.run(NODE_TOPIC, {'keyid': keyid, 'name': lemma, 'count': 1})
        self.session.run(NODE_TOPIC, {'topic': lemma, 'keyid': keyid})
        print(id)


    def new_phrase(self, id, phrase):
        self.session.run(NODE_PHRASE, {'key': id, 'topic': phrase, 'count': 1})

    def link_topic_phrase(self, orig_id, dest_id):
        self.session.run(LINK_TOP_PHR, {'orig_id': orig_id, 'dest_id': dest_id})

    def find_topic(self):
        FINDER = 'MATCH (a:Topic) WHERE a.keyid = "{keyid}" RETURN ee;'
        result = self.session.run("MATCH (a:Topic) WHERE a.keyid = {keyid} RETURN a.topic AS topic, a.keyid AS id", {"keyid": 4291})

        for record in result:
            print("%s %s" % (record["title"], record["name"]))

        self.session.close()

        print("stop now")

    def close(self):
        self.session.close()

    def delete_all(self):
        self.session.run("MATCH (n) DETACH DELETE n")
