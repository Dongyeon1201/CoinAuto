import jwt
import uuid
import hashlib
from urllib.parse import urlencode
import requests
import time
import sys
import logging
import schedule
import json

# 소수점 자르기 함수
def truncate(num,n):
    temp = str(num)
    for x in range(len(temp)):
        if temp[x] == '.':
            try:
                return float(temp[:x+n+1])
            except:
                return float(temp)      
    return float(temp)

logging.basicConfig(
    filename='/usr/src/app/logs/coin.log',
    level=logging.INFO,
    format = '%(asctime)s:%(levelname)s:%(message)s',
    datefmt = '%Y-%m-%d %H:%M:%S %p',
)

API_SERVER_URL = "https://api.upbit.com"
API_ACCESS_KEY = "gdD6NqXZ4jI6AR5bDMn3b0w5yoTdex6vTdY8zyzi"
API_SECRET_KEY = "1DI4qxHDm1sjdC7G6D4zRI32GGTvvs0LCnvUseUd"

BUY = "bid"
SELL = "ask"

SLACK_TOKEN = "xoxb-2451513405360-2547455344711-oI4UayIywovAqCkMX8YK9Kvp"
SLACK_CHANNEL = "#upbit-알림봇"
ERROR_MESSAGE = "*[+] MESSAGE TYPE : `ERROR`*\n"
INFO_MESSAGE = "*[+] MESSAGE TYPE : `INFO`*\n"
KRW_MESSAGE = "*[💰] 내 총 자산 알림*\n"