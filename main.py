from abc import ABCMeta, abstractmethod
import json
import codecs
from math import ceil
import re
import sys

import nltk

from matplotlib import pyplot as plt
import pandas as pd
import numpy as np

from datetime import datetime as dt, timedelta
import pytz

import argparse

def colorGradientFunction(colorA, colorB, fac):
    cA = np.array(colorA)
    cB = np.array(colorB)
    cRes = cA + (cB - cA) * (1 - fac)

    return cRes

class Data:
    def __init__(self,
        path: str
        ) -> None:
        self.path = path
     
    def read(self):
        with codecs.open(self.path, "r", encoding="utf-8", errors="ignore") as f:
            self.f = f.read()
        return self.f
    def toJSON(self):
        if self.f:
            self.data = json.loads(self.f)
            return self.data

class Plot(metaclass=ABCMeta):
    df: pd.DataFrame

    def __init__(self,
        df: pd.DataFrame 
        ) -> None:
        self.df = df
    
    @abstractmethod
    def plot(self) -> None:
        pass

class TweetsPlot(Plot):
    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)
    
    def plot(self,
        figure = True,
        ) -> None:
        if figure:
            plt.figure("Tweet Plot")
        
        df = self.df

        df["created_at"] = pd.to_datetime(df["created_at"]).dt.tz_convert("Asia/Bangkok")

        x = df["created_at"].dt.dayofyear
        total = df.groupby(x).size().to_numpy()[::-1]
        replies = df[~df["replied_to"].isnull()].groupby(x).size().to_numpy()[::-1]

        retweets = df[~df["retweeted"].isnull()]
        retweets_x = retweets["created_at"].dt.dayofyear.drop_duplicates().to_numpy()[::-1]
        retweets = retweets.groupby(x).size().to_numpy()[::-1]

        qrts = df[~df["quoted"].isnull()]
        qrts_x = qrts["created_at"].dt.dayofyear.drop_duplicates().to_numpy()[::-1]
        qrts = qrts.groupby(x).size().to_numpy()[::-1]

        x = x.drop_duplicates().to_numpy()[::-1]
        retweets_x -= x[0]
        qrts_x -= x[0]
        x = x - x[0]

        plt.plot(x, total, label="Total")
        plt.plot(replies, label="Replies / Interactions")
        plt.plot(retweets_x, retweets, label="RT's")
        plt.plot(qrts_x, qrts, label="QRT's")
        plt.legend()

class InteractionPieChart(Plot):
    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)
    
    def plot(self) -> None:
        if True:
            plt.figure("Interaction Pie Chart")

        df = self.df

        # Filter reply username from text
        # Applies str.split()[0].slice(1) or str.split()[0][1:]
        # So from "@username ..." to "@username"
        interactions = df.loc[~df["replied_to"].isnull() & df["text"].str.startswith("@"), "text"].str.split().str.get(0).str.slice(start=1)
        df["interacting_with"] = interactions
        sum = interactions.groupby(interactions).size()

        users = sum.keys()
        vals = sum.values

        users = [x for _, x in sorted(zip(vals, users))][::-1]
        vals = np.sort(vals)[::-1]

        self.userInteractionSeries = pd.Series(vals, index = users)

        plt.pie(vals[:15], labels=users[:15])

class InteractionPlot(Plot):
    def __init__(self, df: pd.DataFrame, userInteractionSeries: pd.Series = None) -> None:
        self.userInteractionSeries = userInteractionSeries
        super().__init__(df)

    def plot(self) -> None:
        if True:
            plt.figure("Interaction plot")

            df = self.df

            if not "interacting_with" in df:
                return

            interactions = df.loc[~df["interacting_with"].isnull()]
            grouped = interactions.groupby("interacting_with")

            oldest_date = df["created_at"].dt.dayofyear.values[-1]
            dateRange = df["created_at"].dt.dayofyear.values[0] - oldest_date

            userInteractionSeries = self.userInteractionSeries

            for name, group in grouped:
                # if group.shape[0] < 10:
                    # continue

                dates = group["created_at"].dt.dayofyear
                dgroup = group.groupby(dates).size().to_numpy()[::-1]

                # x = dates.drop_duplicates().to_numpy() - oldest_date
                # x = x[::-1]

                x = np.arange(dateRange + 1)

                y = np.zeros(dateRange + 1)
                y[dates.drop_duplicates().to_numpy() - oldest_date] = dgroup

                if not userInteractionSeries is None and not userInteractionSeries.empty:
                    userIRank = userInteractionSeries.index.get_loc(name)

                    if not userIRank < 5:
                        continue

                    # print(userInteractionSeries.index.get_loc(name))
                    # cFac = userIRank / (userInteractionSeries.size - 1)
                    cFac = 1 - userIRank / 5
                    c = tuple(colorGradientFunction([255, 0 ,0], [0, 0, 255], cFac) / 255) + (1 - cFac,)

                plt.plot(x, y, label=name)
            plt.legend()

class TweetTimeHist(Plot):
    def __init__(self, df: pd.DataFrame) -> None:
        super().__init__(df)
    
    def plot(self) -> None:
        plt.figure("Time Histogram")

        df = self.df

        tweets = df.loc[
            df["interacting_with"].isnull() & 
            df["quoted"].isnull() &
            df["retweeted"].isnull()
        ]

        x = tweets["created_at"].dt.hour        
        y = tweets.groupby(x).size().to_numpy()

        plt.bar(x.drop_duplicates().to_numpy(), y)

class LanguageObservation():
    def __init__(self, df: pd.DataFrame) -> None:
        self.df = df
        pass
    
    def print(self):
        df = self.df

        sampleText = df.loc[df["replied_to"].isnull() & df["quoted"].isnull() & df["retweeted"].isnull(), "text"].sample().values[0]
        tokens = nltk.word_tokenize(sampleText)
        print(f"Text: {sampleText}")
        print("Tokens: ", end=" ")
        print(tokens)

        pass


def main():
    user = "nullluvsu"
    data = Data(f"./data/out-{user}_2.json")
    data.read()
    data.toJSON()
    dataPlus = Data(f"./data/out-{user}_3.json")
    dataPlus.read()
    dataPlus.toJSON()

    dataArr = dataPlus.data["data"] + data.data["data"]
    for tweet in dataArr:
        tweet["replied_to"] = None
        tweet["retweeted"] = None
        tweet["quoted"] = None

        referenced_tweets = tweet.pop("referenced_tweets", None)

        if referenced_tweets:
            for ref in referenced_tweets:
                tweet[ref["type"]] = ref["id"]
        
        public_metrics = tweet.pop("public_metrics", None)
        for public_metric, val in public_metrics.items():
            tweet[public_metric] = val


    df = pd.DataFrame(dataArr)

    # print(df.loc[df["text"].str.startswith("@caekyii"), ["text", "id"]])
    # return

    # print()

    tweetsPlot = TweetsPlot(df)
    tweetsPlot.plot()

    interactionPieChart = InteractionPieChart(df)
    interactionPieChart.plot()

    interactionPlot = InteractionPlot(df, interactionPieChart.userInteractionSeries)
    interactionPlot.plot()

    tweetTimeHist = TweetTimeHist(df)
    tweetTimeHist.plot()

    # print(df.loc[~df["interacting_with"].isnull(), "text"].tail(15))

    languageObservation = LanguageObservation(df)
    # languageObservation.print()

    plt.show()

if __name__ == "__main__":
    main()