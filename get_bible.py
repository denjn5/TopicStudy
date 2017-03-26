"""
Get bible text, return as dictionary; save to graph db.
"""

# IMPORTS
import pandas as pd
import graph_db

# GLOBALS
SRC_DIR = 'Texts/'


def main(reference):
    """
    Get a Bible chapter, book (or the whole Bible!)
    :param reference: bible or "luk 4" or "gen 2" or "john"
    :return: dictionary {reference: text}
    """
    # READ KJV CSV
    df = pd.read_csv(SRC_DIR + 'kjv.csv', sep='|')

    # GET SELECTION
    reference = reference.lower()
    if reference == 'bible':
        selection = df
    else:
        book = reference.split(' ')[0]
        chap = None if len(reference.split(' ')) == 1 else int(reference.split(' ')[1])

        if chap:
            selection = df[(df['book'] == book) & (df['chapter'] == chap)]
        else:
            selection = df[(df['book'] == book)]

    # CONCATENATE TO TEXT
    verses = {}
    for index, row in selection.iterrows():
        ref = str(row['book'] + ' ' + str(row['chapter']) + ':' + str(row['verse']))
        verses[ref] = row['text']

    return verses


def db_add_posts(posts, db_start_fresh=False):
    """
    Save each verse to the graph database.
    :param posts: A dictionary with each verse as an entry: {reference: text}
    :param db_start_fresh: Do we delete all on graph db before starting?
    :return: 
    """
    gt = graph_db.GraphManager()

    if db_start_fresh:
        gt.delete_all()

    for reference in posts:
        gt.post(reference, posts[reference])
    gt.close()


if __name__ == "__main__":
    main("psa 23")
