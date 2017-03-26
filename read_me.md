

#TODO
1) Calc shallow 
    * Denominator: Count the total number of topics (topics in both chapters are counted twice)
    * Numerator: Count of shared topics * 2
        - Find ("Mat 1")-[SRC]-(top:Topic)-[SRC]-("Mat 2")
        - List topics
    * "New Topics": What are the topics that aren't connected to both
        - Find ("Mat 2")-[SRC]-(top:Topic)
1) transactions to neo4j dropping?

#Topic Modeler
A series of helper functions to find topics in context, and compare topics across texts and visualize.

Summary
* run_me.py: Open and click go and you'll get example output.
* get_bible.py: 
* build_topics.py: Find topics (nouns) with context. Keep everything linked with original posts.
* Compare topics between 2 texts
* Word2Vec
* Summarized sentence(s) of text(s)
*  


## Topic Summary (single corpus)
Goal: Find topics and illustrate 

### Topic profile
Nouns by count or as a percentage across whole text. 

        Corp1_Ct  Corp2_Ct  Corp1_%  Corp2_%  Corp1_Ct_Rm  Corp2_Ct_Rm          
WordA:  12        8         1.5%     1.8%     4            0


Bar Graph: 
1) Corp1 & Corp2 (diff bars)
2) 



## Regex for alternate Bibles
F: <c n="([0-9]+)">
R: ~\1

F: (<c n="([0-9]+)">)([^,]|\n)*<v n="([0-9]+)">
R: \1\n|\2|\3|

