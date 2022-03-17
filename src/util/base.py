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
import asyncio
import websockets   # 웹 소켓 모듈을 선언한다.
import copy

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
WEBSOCKET_URL = "wss://api.upbit.com/websocket/v1"
API_ACCESS_KEY = ""
API_SECRET_KEY = ""

BUY = "bid"
SELL = "ask"
BID_FEE_KRW = float(0.05/100)

SLACK_TOKEN = ""
SLACK_CHANNEL = "#upbit-알림봇"
ERROR_MESSAGE = "*[+] MESSAGE TYPE : `ERROR`*\n"
INFO_MESSAGE = "*[+] MESSAGE TYPE : `INFO`*\n"
KRW_MESSAGE = "*[💰] 내 총 자산 알림*\n"
