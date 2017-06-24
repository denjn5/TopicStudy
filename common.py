"""
A series of functions that'll be used commonly by other classes throughout TopicStudy
"""

import json
from datetime import datetime

import pandas as pd

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

import config


# alt: from vaderSentiment import SentimentIntensityAnalyzer


def export_texts(texts, corpus_name, data_date='', text_length_max=16000):
    """
    Prepare analyzed texts for UI, then saves. Create htmlCard, format sentiment, jettison fields we no longer need.

    :param texts: A dict of dicts containing our text. We assume it contains the following:
        {text_id: {text: 'abc', title: 'xyz', time: '10:15', sentiment: 0, logoFile: 'esv.png', url: 'www.esv.com?a=b'}}
    :param corpus_name:
    :param data_date:
    :param text_length_max:
    :return:
    """

    # TODO: sentiment could be 0 to 1 or -1 to 1

    assert len(texts) > 0, "No text data to export."

    # A template for the html card that will get presented in the UI
    html_card = "<div class='card bs-callout {card_sent}' id='card_{id}'>" \
                "<div class='cardTime'>{time_and_count}</div>" \
                "<a href='{url}' target='_blank'><img src='{logo_path}' class='cardImage' /></a>" \
                "<div class='cardTitle h4'>" \
                "<a href='javascript:void(0);' onclick='cardToggle({id})'>{card_title}</a></div>" \
                "<a href='javascript:void(0);' onclick='cardToggle({id})'>" \
                "<i class='fa fa-minus-square-o fa-lg cardToggle'></i></a>" \
                "<div class='cardText' id='text_{id}'>{card_text}</div>" \
                "</div>"

    save_texts = []
    for _, row in texts.iterrows():
        # for text_id, text in texts.items():
        sent_class = 'bs-callout-neg' if row['sentiment'] < -0.33 else ('bs-callout-pos'
                                                                        if row['sentiment'] > 0.33 else '')

        # Are either (or both) post time and text count available?
        time_and_count = (('' if pd.isnull(row['time']) else row['time']) + ' | ' +
                          ('' if pd.isnull(row['count']) else 'text count: <i>' + row['count'] + '</i>')).strip(' |')

        card = html_card.format(id=row['textId'], card_sent=sent_class,
                                time_and_count=time_and_count,
                                logo_path=r'Logos\\' + row['logoFile'],
                                card_title=row['title'],
                                url='https://{}'.format(row['url']),
                                card_text=row['text'][:text_length_max])

        save_texts.append({"id": row['textId'], "title": row['title'], "sentiment": row['sentiment'],
                           "text": row['text'], "source": row['source'], "htmlCard": card})

        # Build file name and save
        if data_date:
            date = datetime.strptime(data_date, "%Y-%m-%d").strftime('%d')  # from YYYY-MM-DD to DD
            file_name = '{}-{}-Texts.txt'.format(corpus_name, date)
        else:
            file_name = '{}-Texts.txt'.format(corpus_name)

        with open(config.OUTPUT_DIR + file_name, 'w') as file:
            json.dump(save_texts, file)


def add_sentiment(texts):
    """
    Calculates sentiment for a text using VaderSentiment as a sentiment calculation between -1 and 1.
    :param texts: A dict of texts: {text_id: {text: 'abc', title: 'xyz'}}
    :return: No explicit return. Adds (or updates) a sentiment to texts:
        {text_id: {text: 'abc', title: 'xyz', sentiment: 0}}
    """
    analyzer = SentimentIntensityAnalyzer()
    # df_texts['sentiment'] = analyzer.polarity_scores(df_texts['text'].str)

    for index, row in texts.iterrows():
        sentiment = analyzer.polarity_scores(row['text'])
        row['sentiment'] = sentiment['compound']
