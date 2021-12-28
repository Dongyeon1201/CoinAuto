from time import sleep
from util import *
from util import account
from util import upbit
from util.coin import *
from util.upbit import *
from util.info import *
from util.account import *

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
CoinAccount = Account(upbitUtil.getAllCoinList())

CoinName = "KRW-BTC"

# 주문을 위한 헤더 설정
headers = upbitUtil.getHeaders(query={'market': CoinName})

# 코인 구입
# upbitUtil.orderMarketCoin(CoinName, BUY, order_krw=5000, headers=headers)

# orderable_volume = upbitUtil.getCanSellVolume(CoinName)
# upbitUtil.orderMarketCoin(CoinName, SELL, orderable_volume=orderable_volume, headers=headers)