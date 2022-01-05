from util.base import *
from util.coin import *
from util.upbit import *
from util.info import SendSlackMessage

class Account:

    def __init__(self, watch_coin_list):
        self.watch_coin_list = watch_coin_list
        self.hold_coin_list = []
        self.num_hold_coins = 0

        self.favorite_coin_list = ["KRW-CHZ"]
        self.not_trade_coin_list = []

    def AddCoin(self, coin):
        self.hold_coin_list.append(coin)
        self.num_hold_coins += 1
    
    def DelCoin(self, coin):
        for i, item in enumerate(self.hold_coin_list):
            if item == coin:
                self.hold_coin_list.pop(i)
                self.num_hold_coins -= 1

    def GetCoin(self, market_name):
        for item in self.hold_coin_list:
            if item.market_name == market_name:
                return item
        
        return None

    def GetHoldCoinNum(self):
        return self.num_hold_coins

    def GetHoldCoinList(self):
        return [item.market_name for item in self.hold_coin_list]

    def AddFavoriteList(self, market_name):
        self.favorite_coin_list.append(market_name)

    def DeleteFavoriteList(self, market_name):
        for i, item in enumerate(self.favorite_coin_list):
            if item == market_name:
                self.favorite_coin_list.pop(i)
        
    def ResetFavoriteList(self):
        self.favorite_coin_list = []
    
    def AddNotTradeCoinList(self, market_name):
        self.not_trade_coin_list.append(market_name)

    def ResetNotTradeCoinList(self):
        self.not_trade_coin_list = []