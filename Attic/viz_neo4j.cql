/*
http://www.lyonwj.com/LazyWebCypher/
*/


// QUERIES
// return all phrases and topics with links
MATCH (n:Phrase)-[:TOP]->(m:Topic) RETURN n,m;


// return topics by count:
MATCH (n:Topic) RETURN n ORDER BY n.count DESC;

// return Topic nodes that have a mat2 link, but no mat2 count:
MATCH (top:Topic)-[l:mat2]-()
WHERE NOT EXISTS(top.mat2)
SET top.mat2 = 0
RETURN top;


//Return Topics and counts by Corpus (based on link):
MATCH (top:Topic)
WHERE (top)-[:mat1]-() OR (top)-[:mat2]-()
RETURN top.topic, top.mat2, top.mat1;

/*
    * Numerator: Count of shared topics * 2
        - Find ("Mat 1")-[SRC]-(top:Topic)-[SRC]-("Mat 2")
        - List topics
    * "New Topics": What are the topics that aren't connected to both
        - Find ("Mat 2")-[SRC]-(top:Topic)
*/