"""

"""

from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# alt: from vaderSentiment import SentimentIntensityAnalyzer

class calculateSentiment(object):
    def __init__(self, texts):
        """
        
        :param texts: 
        """
        self.texts = texts


    def add_sentiment(self):
        """
        
        :return: 
        """
        analyzer = SentimentIntensityAnalyzer()
        for text in self.texts:
            vs = analyzer.polarity_scores(text['text'])
            text['sentiment'] = vs['compound']  # compound
            # print("{:-<65} {}".format(text['text'], str(vs)))

