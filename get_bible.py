"""
Get bible text, return as dictionary; save to graph db.
"""
# FEATURE: Can I run a compare of all chapters in the Bible to see which ones have the greatest overlap?

# IMPORTS
import pandas as pd
import viz_graph_db


# GLOBALS
SRC_DIR = 'Texts/'


def main(reference):
    """
    Get a Bible chapter, book (or the whole Bible!)
    :param reference: bible or "luk 4" or "gen 2" or "john"
    :return: dictionary {reference: texts}
    """
    # READ KJV (kjv.csv) or ov.csv file
    df = pd.read_csv(SRC_DIR + 'ov.csv', sep='|')

    # GET SELECTION
    if reference == 'bible':
        selection = df
    else:
        book = reference.split(' ')[0]
        chap = None if len(reference.split(' ')) == 1 else int(reference.split(' ')[1])

        if chap:
            selection = df[(df['book'] == book) & (df['chapter'] == chap)]
        else:
            selection = df[(df['book'] == book)]

    # Move to dictionary
    verses = {}
    # {"id": "id", "author": "author", "title": "title", "sentiment": 0.5, "source": "source", "url": "http...", "htmlCard": "<div></div>"}
    for i, row in selection.iterrows():
        ref = str(row['book'] + '_' + str(int(row['chapter'])) + ':' + str(int(row['verse'])))
        verses[ref] = row['text'].replace("'", "").replace('"', '')


    return verses


def db_add_posts(posts, db_start_fresh=False):
    """
    Save each verse to the graph database.
    :param posts: A dictionary with each verse as an entry: {reference: texts}
    :param db_start_fresh: Do we delete all on graph db before starting?
    :return: 
    """
    # TODO: Add "title" to Text node.
    gt = viz_graph_db.GraphManager()

    if db_start_fresh:
        gt.delete_all()

    for reference in posts:
        gt.text(reference, posts[reference])
    # gt.close()


if __name__ == "__main__":
    main("psa 23")
