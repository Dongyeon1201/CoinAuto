import jwt
import uuid
import hashlib
from urllib.parse import urlencode
import requests
import time
import sys
import logging
import schedule

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
ERROR_MESSAGE = "[+] MESSAGE TYPE : `ERROR`\n"
INFO_MESSAGE = "[+] MESSAGE TYPE : `INFO`\n"
KRW_MESSAGE = "[💰] 내 총 자산 알림\n"

# 슬랙으로 메세지 전송
def SendSlackMessage(msg):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer " + SLACK_TOKEN},
        data={"channel": SLACK_CHANNEL,"text": msg}
    )

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

# 코인의 이름으로 해당 코인의 정보 조회 / 주문 등 기능 모음
class UpbitUtil:
    
    # API KEY 설정
    def __init__(self, access_key, secret_key):
        self.server_url = API_SERVER_URL
        self.access_key = API_ACCESS_KEY
        self.secret_key = API_SECRET_KEY

    # API 요청을 위한 header 반환
    # 결제시에는 market name을 포함한 쿼리를 이용한 query_hash / query_hash_alg 추가 페이로드 필요
    def getHeaders(self, query=None):
        
        # 쿼리가 존재할 때 (결제 관련 요청)
        if query:

            query_string = urlencode(query).encode()

            m = hashlib.sha512()
            m.update(query_string)
            query_hash = m.hexdigest()

            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
                'query_hash': query_hash,
                'query_hash_alg': 'SHA512',
            }
        
        # 쿼리가 존재하지 않을 때(일반적인 조회 등 요청[기본 값])
        else:
            payload = {
                'access_key': self.access_key,
                'nonce': str(uuid.uuid4()),
            }
        
        # token이 포함된 헤더 설정
        try:
            jwt_token = jwt.encode(payload, self.secret_key)
            authorize_token = 'Bearer {}'.format(jwt_token)
            headers = {"Authorization": authorize_token}

        except Exception as e:
            logging.error("[ Function Name : getHeaders() ]\n[+] 헤더 생성에 실패하였습니다.\n[-] ERROR : {}".format(e))
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getHeaders() ]\n[+] 헤더 생성에 실패하였습니다.".format(e))

        return headers
        
    # MarketName을 사용하여 해당 코인의 소유 여부 반환
    def isCoinHold(self, market_name):

        res = requests.get(self.server_url + "/v1/accounts", headers=self.getHeaders())

        if res.status_code == 200:
            COIN_NAME = market_name.split('-')[1]

            for item in res.json():
                if COIN_NAME == str(item['currency']):
                    return True

            return False
        
        else:
            logging.error("[ Function Name : isCoinHold() ]\n[+] 현재 {} 의 소유 여부를 확인할 수 없습니다. STATUS CODE : {}".format(market_name, res.status_code))
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : isCoinHold() ]\n[+] 현재 {} 의 소유 여부를 확인할 수 없습니다. STATUS CODE : {}\nERROR : {}".format(market_name, res.status_code, res.text))

    # MarketName을 사용하여 해당 코인의 가격 반환
    def getCurrentPrice(self, market_name):

        res = requests.get(self.server_url + "/v1/ticker", params={'markets' : market_name})

        if res.status_code == 200:
            current_price = res.json()[0]['trade_price']
            return current_price
        
        else:
            logging.error("[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}".format(res.status_code))
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}\nERROR : {}".format(res.status_code, res.text))

    # MarketName을 이용하여 해당 코인의 미 체결 주문 목록을 반환
    def getWaitOrderList(self, market_name):
        query = {
            'market':market_name,
            'state': 'wait'
        }

        res = requests.post(self.server_url + "/v1/orders", params=query, headers=self.getHeaders(query))

        if res.status_code == 200:
            return res.json()

        else:
            logging.error("[ Function Name : getCurrentPrice() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}".format(res.status_code))
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}\nERROR : {}".format(res.status_code, res.text))
    
    # 사용가능한 원화 반환
    def getCurrentKRW(self, percent=100):

        res = requests.get(self.server_url + "/v1/accounts", headers=self.getHeaders())
        
        # 현재 원화 보유량 확인
        for item in res.json():
            if item['currency'] == 'KRW':
                KRW = int(float(item['balance']))

        # 최대 사용가능한 원화 확인
        max_use_KRW = int(self.getAllKRW() * (percent / 100))
        
        return max_use_KRW if KRW > max_use_KRW else KRW

    # 모든 자산의 가치를 원화로 확인
    def getAllKRW(self):

        ALL_KRW = 0

        res = requests.get(self.server_url + "/v1/accounts", headers=self.getHeaders())
        
        for item in res.json():
            if item['currency'] == 'KRW':
                ALL_KRW += int(float(item['balance']))
            else:
                ALL_KRW += float(item['balance']) * float(item['avg_buy_price'])
        
        return int(ALL_KRW)

    # MarketName을 이용하여 해당 코인의 주문 가능한 현재 가격과 주문량 반환
    def getCanBuyVolume(self, market_name, current_price, current_krw):

        query = {'market': market_name}
        res = requests.get(self.server_url + "/v1/orders/chance", params=query, headers=self.getHeaders(query=query))

        # 매수 수수료 조회
        bid_fee = res.json()['bid_fee']

        # 주문 가능한 코인의 수량 구하기
        
        # 주문 가능한 원화가 없을 땐 0 반환
        # 최소 주문금액(5000원) 보다 적을때는 0 반환
        if current_krw < 5000:
            return 0

        # 매수 시 매수 량 구하기
        # (주문하려는 금액 * (1-bid_fee) / 현재 가격) -> 8자리에서 버림
        order_volume = truncate(current_krw * (1-float(bid_fee)) / current_price, 8)
        return order_volume

    # 매도 가능한 코인의 수량 확인
    def getCanSellVolume(self, market_name):

        res = requests.get(self.server_url + "/v1/accounts", headers=self.getHeaders())

        for item in res.json():
            if 'KRW-' + item['currency'] == market_name:
                return float(item['balance'])
        
        logging.error("[ Function Name : getCanSellVolume() ]\n[+] {} 코인의 정보를 확인할 수 없습니다.".format(market_name))
        SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCanSellVolume() ]\n[+] {} 코인의 정보를 확인할 수 없습니다.\nERROR : {}".format(market_name, res.text))

    # 코인 주문
    # order_side : bid -> 매수
    # order_side : ask -> 매도
    def orderCoin(self, market_name, order_side, order_volume, order_price, headers):

        query = {
            'market': market_name,
            'volume': order_volume,
            'price': order_price,
            'ord_type': 'limit'
        }

        # 매수
        if order_side == "bid":
            
            # 매수로 설정
            query['side'] = "bid"

            # 주문 요청을 위한 헤더 생성
            headers = self.getHeaders(query=query)
            res = requests.post(self.server_url + "/v1/orders", params=query, headers=headers)

            if res.status_code == 201:

                logging.info("{} 코인 {:,} 가격에 ALL 매수 완료".format(market_name, order_price))
                SendSlackMessage(INFO_MESSAGE + "{} 코인 *{:,}* 가격에 ALL 매수 완료".format(market_name, order_price))

            else:
                logging.error("[ Function Name : orderCoin() ]\n[+] {} 항목의 매수를 성공하지 못하였습니다. STATUS CODE : {}".format(market_name, res.status_code))
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : orderCoin() ]\n[+] {} 항목의 매수를 성공하지 못하였습니다. STATUS CODE : {}\nERROR : {}".format(market_name, res.status_code, res.text))

        # 매도
        elif order_side == "ask":
            
            # 매도로 설정
            query['side'] = "ask"

            # 주문 요청을 위한 헤더 생성
            headers = self.getHeaders(query=query)
            res = requests.post(self.server_url + "/v1/orders", params=query, headers=headers)

            if res.status_code == 201:
                logging.info("{} 코인 {:,} 가격에 ALL 매도 완료".format(market_name, order_price))
                SendSlackMessage(INFO_MESSAGE + "{} 코인 *{:,}* 가격에 ALL 매도 완료".format(market_name, order_price))

            else:
                logging.error("[ Function Name : orderCoin() ]\n[+] {} 항목의 매도를 성공하지 못하였습니다. STATUS CODE : {}".format(market_name, res.status_code))
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : orderCoin() ]\n[+] {} 항목의 매도를 성공하지 못하였습니다. STATUS CODE : {}\nERROR : {}".format(market_name, res.status_code, res.text))

# 각 코인에 대한 정보를 담은 클래스
class Coin:

    def __init__(self, korean_name, coin_proportion, up_line_per, down_line_per):

        self.server_url = API_SERVER_URL    # 서버 주소

        self.up_line_per = 0.01 * (100 + up_line_per)      # 코인의 상승 라인
        self.down_line_per = 0.01 * (100 - down_line_per)  # 코인의 하락 라인

        # 코인의 한글 이름
        self.coin_korean_name = korean_name

        # 코인의 전체 자산 최대 비율
        self.coin_proportion = coin_proportion

        # upbit API 동작에 사용될 market_name
        self.market_name = self.getMarketName(self.coin_korean_name)

        # 코인 보유 여부는 초기에 False로 설정
        self.is_coin_hold = False

        # 코인 확인 모드 설정
        # up : 기준에 따라 오르는 중
        # down : 기준에 따라 떨어지는 중
        # pass : 가만히 지켜보는 중 [기본 값]
        self.coin_mode = 'pass'

    # 코인 이름(한글)을 입력받아 MarketName 반환
    def getMarketName(self, korean_name, monetary="KRW"):

        monetary = monetary.upper()

        res = requests.get(self.server_url + "/v1/market/all")

        if res.status_code == 200:
            for item in res.json():
                if item['korean_name'] == korean_name:
                    if monetary + "-" in item['market']:
                        return item['market']
            
            logging.error("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}".format(korean_name, res.status_code))
            SendSlackMessage("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}".format(korean_name, res.status_code))

        else:
            logging.error("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}".format(korean_name, res.status_code))
            SendSlackMessage("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}".format(korean_name, res.status_code))

    # 코인의 현재 가격 설정
    def setCurrentPrice(self, current_price):
        self.current_price = current_price
    
    # 코인의 이전 가격 설정
    def setBeforePrice(self, before_price):
        self.before_price = before_price

    # 코인의 체크라인 가격 설정
    # 체크라인 가격에 따라 상승 기준가, 하락 기준가 결정
    def setCheckLinePrice(self, check_line_price):

        # 체크라인 가격 설정
        self.check_line_price = check_line_price

        # 상승 기준가
        self.up_line_price = check_line_price * self.up_line_per

        # 하락 기준가
        self.down_line_price = check_line_price * self.down_line_per

    # 코인의 보유 여부 확인
    def setisCoinHold(self, is_coin_hold):
        self.is_coin_hold = is_coin_hold

    # 코인의 모드 설정
    def setCoinMode(self, coin_mode):
        self.coin_mode = coin_mode