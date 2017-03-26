
# IMPORTS
import get_bible
import build_topics

# GLOBALS

chapter1 = "Mat 1"
posts = get_bible.main(chapter1)
get_bible.db_add_posts(posts, db_start_fresh=True)
tb = build_topics.TopicBuilder(chapter1)
tb.find_phrases(posts)

# chapter2 = "Mat 2"
# posts = get_bible.main(chapter2)
# get_bible.db_add_posts(posts, db_start_fresh=False)
# tb = build_topics.TopicBuilder(chapter2)
# tb.find_phrases(posts)