import yfinance as yf
import pandas as pd
import numpy as np
import math
import json
from datetime import datetime, timedelta
import requests
import urllib.request, urllib.parse, urllib.error


now = datetime.now()
last_month = (now - timedelta(weeks=4)).replace(day=30)
last_month_timestamp = datetime.timestamp(last_month)
month_year_ago = last_month - timedelta(weeks=52)
month_year_ago_timestamp = datetime.timestamp(month_year_ago)


def check_nan(num):
    if math.isnan(num):
    #if num is None:
        num = 0.0
        return num
    else:
        return num


class Momentum:
    @staticmethod
    def get_momentum_avg(ticker):
        """
        Average momentum for last 3,6,12 months:
        a) price_1: end of last month price
        b) price_3: close price of three months ago
        c) price_6: close price of six months ago price
        d) price_12: close price of twelve months ago price
        """
        try:

            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?symbol={ticker}&period1={int(month_year_ago_timestamp)}&period2={int(last_month_timestamp)}&interval=1mo"
            fhand = urllib.request.urlopen(url).read()
            data = json.loads(fhand)
            price_1 = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][0]
            price_3 = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][2]
            price_6 = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][5]
            price_12 = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][11]
            momentum_avg = (
                (price_1 / price_3) + (price_1 / price_6) + (price_1 / price_12)
            ) / 3
            result = check_nan(momentum_avg)
        except:
            result = 0.0
        finally:
            return round(result, 2)

    @staticmethod
    def get_momentum_12_1(ticker):
        """
        Get momentum:
        close price for end of last month / close price twelve month ago
        """
        try:
            url = f"https://query2.finance.yahoo.com/v8/finance/chart/{ticker}?symbol={ticker}&period1={int(month_year_ago_timestamp)}&period2={int(last_month_timestamp)}&interval=1mo"
            fhand = urllib.request.urlopen(url).read()
            data = json.loads(fhand)
            price_1 = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][0]
            price_12 = data["chart"]["result"][0]["indicators"]["quote"][0]["close"][11]
            momentum = (price_1 / price_12) - 1
        except:
            momentum = 0.0
        finally:
            # check_nan(momentum)
            return round(momentum, 3)


class DivP:
    @staticmethod
    def get_div_p(ticker):
        """
        Average dividends for last 4 years / last close price
        Yahoo finance yfinance
        """
        try:
            stock = yf.Ticker(ticker)
            dividends = stock.dividends
            dividends_for_last_years = dividends[-20:].mean() * 4
            div_p = dividends_for_last_years / stock.info["currentPrice"]
            if math.isnan(div_p):
                div_p = 0
        except:
            div_p = 0.0
        finally:
            # result = check_nan(div_p)
            # print(div_p)
            return round(div_p, 2)


# class Ma10:
#     @staticmethod
#     def get_ma_10(ticker):
