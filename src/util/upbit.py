from util.base import *
from util.info import SendSlackMessage

class UpbitUtil:
    
    # API KEY 설정
    def __init__(self, access_key, secret_key):
        self.server_url = API_SERVER_URL
        self.access_key = API_ACCESS_KEY
        self.secret_key = API_SECRET_KEY

        self.coins_info = {}

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

            if res.text == None:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : isCoinHold() ]\n[+] 현재 {} 의 소유 여부를 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```NONE```".format(market_name, res.status_code))
            else:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : isCoinHold() ]\n[+] 현재 {} 의 소유 여부를 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_name, res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

    # 모든 코인의 목록 확인
    def getAllCoinList(self):
        headers = {"Accept": "application/json"}
        res = requests.request("GET", API_SERVER_URL + "/v1/market/all?isDetails=true", headers=headers)
        return [item['market'] for item in json.loads(res.text) if "KRW-" in item['market'] and item['market_warning'] == "NONE"]

    # 투자 유의 종묙 코인 확인
    def GetWarningcoin(self):
        headers = {"Accept": "application/json"}
        res = requests.request("GET", API_SERVER_URL + "/v1/market/all?isDetails=true", headers=headers)
        return [item['market'] for item in json.loads(res.text) if "KRW-" in item['market'] and item['market_warning'] == "CAUTION"]

    # MarketName을 사용하여 해당 코인의 가격 반환
    def getCurrentPrice(self, market_name):

        res = requests.get(self.server_url + "/v1/ticker", params={'markets' : market_name})

        if res.status_code == 200:
            current_price = res.json()[0]['trade_price']
            return current_price
        
        else:
            logging.error("[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}".format(res.status_code))

            if res.text == None:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```NONE```".format(res.status_code))
            else:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

    # MarketName을 사용하여 해당 코인의 가격 반환
    def getTodayOpeningprice(self, market_name):

        param = {
            "count": 1,
            "market" : market_name
        }

        res = requests.get(self.server_url + "/v1/candles/days", headers=self.getHeaders(), params=param)
        
        if res.status_code == 200:
            return res.json().pop()['opening_price']

        else:
            logging.error("[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}".format(res.status_code))
            
            if res.text == None:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```NONE```".format(res.status_code))
            else:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

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

            if res.text == None:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(res.status_code))
            else:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

    # MarketName을 이용하여 해당 코인의 평균 매수가 확인
    def getBuyprice(self, market_Name):
        
        res = requests.get(self.server_url + "/v1/accounts", headers=self.getHeaders())
        
        # 평균 매수가 확인
        for item in res.json():
            if item['currency'] == market_Name.split('-').pop():
                return item['avg_buy_price']
        
        logging.error("[ Function Name : getBuyprice() ]\n[+] {} 코인의 평균매수가를 받아올 수 없습니다. STATUS CODE : {}".format(market_Name, res.status_code))

        if res.text == None:
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getBuyprice() ]\n[+] {} 코인의 평균매수가를 받아올 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_Name, res.status_code))
        else:
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getBuyprice() ]\n[+] {} 코인의 평균매수가를 받아올 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_Name, res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

        return False

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
        orderable_volume = truncate(current_krw * (1-float(bid_fee)) / current_price, 8)
        return orderable_volume

    # 매도 가능한 코인의 수량 확인
    def getCanSellVolume(self, market_name):

        res = requests.get(self.server_url + "/v1/accounts", headers=self.getHeaders())

        for item in res.json():
            if 'KRW-' + item['currency'] == market_name:
                return float(item['balance'])
        
        logging.error("[ Function Name : getCanSellVolume() ]\n[+] {} 코인의 정보를 확인할 수 없습니다.".format(market_name))

        if res.text == None:
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCanSellVolume() ]\n[+] {} 코인의 정보를 확인할 수 없습니다.\n[ ERROR ] ```{}```".format(market_name))
        else:
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCanSellVolume() ]\n[+] {} 코인의 정보를 확인할 수 없습니다.\n[ ERROR ] ```{}```".format(market_name, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

    # 코인 주문
    # order_side : bid -> 매수
    # order_side : ask -> 매도
    def orderCoin(self, market_name, order_side, orderable_volume, order_price, headers):

        query = {
            'market': market_name,
            'volume': orderable_volume,
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

                if res.text == None:
                    SendSlackMessage(ERROR_MESSAGE + "[ Function Name : orderCoin() ]\n[+] {} 항목의 매수를 성공하지 못하였습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_name, res.status_code))
                else:
                    SendSlackMessage(ERROR_MESSAGE + "[ Function Name : orderCoin() ]\n[+] {} 항목의 매수를 성공하지 못하였습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_name, res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

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

                if res.text == None:
                    SendSlackMessage(ERROR_MESSAGE + "[ Function Name : orderCoin() ]\n[+] {} 항목의 매도를 성공하지 못하였습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_name, res.status_code))
                else:
                    SendSlackMessage(ERROR_MESSAGE + "[ Function Name : orderCoin() ]\n[+] {} 항목의 매도를 성공하지 못하였습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(market_name, res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

    # 현재 거래량 확인 (5분 기준)
    def getTradeRecent(self, market_name):

        param = {
            "market": market_name,
            "count": 1
        }
        res = requests.get(self.server_url + "/v1/candles/minutes/5", headers=self.getHeaders(), params=param)

        # 현재 포함한 이전 5분동안 거래 내역 확인
        trade_data = json.loads(res.text)

        # 현재 거래 내역은 따로 저장
        return trade_data[0]

    # 평균 거래량 확인 (5분 거래량)
    def getTradeVolAvg(self, count, market_name):

        param = {
            "market": market_name,
            "count": count
        }
        res = requests.get(self.server_url + "/v1/candles/minutes/5", headers=self.getHeaders(), params=param)

        # 현재 포함한 이전 5분동안 거래 내역 확인
        trade_data = json.loads(res.text)

        # 현재 거래 내역은 따로 저장
        Recent = trade_data.pop(0)

        # 현재 제외 이전 5분동안 거래량 평균 구하기
        trade_all = 0
        for item in trade_data:
            trade_all += item['candle_acc_trade_volume']

        trade_vol_avg = trade_all / count

        return trade_vol_avg

    # 현재 변화상태 확인
    def getTradeChange(self, market_name):

        param = {
            "markets": market_name
        }
        res = requests.get(self.server_url + "/v1/ticker", headers=self.getHeaders(), params=param)

        # 현재 상태 확인
        return res.json()[0]['change']

    # 코인의 초기 상태 설정
    def setCoinInfo(self):

        for CoinName in self.getAllCoinList():

            self.coins_info[CoinName] = {
                "trade_price" : None,
                "opening_price" : None,
                "MA30" : None,
                "MA5" : None
            }

    # MA 구하기
    def setMA(self, market_name, count):

        MA = 0

        param = {
            "count": count,
            "market" : market_name
        }

        res = requests.get(self.server_url + "/v1/candles/days", headers=self.getHeaders(), params=param)
        
        # 상장된지 30일도 되지 않은 코인은 MA를 None으로 처리, 거래를 하지 않음
        if len(res.json()) < count:
            self.coins_info[market_name]['MA30'] = None
            self.coins_info[market_name]['MA5'] = None

        else:
            for item in res.json():
                MA += item['trade_price']

            if count == 30:
                self.coins_info[market_name]['MA30'] = MA / 30
            elif count == 5:
                self.coins_info[market_name]['MA5'] = MA / 5
    
    # 일봉(당일 포함) 3일 연속 양봉인지 확인
    def isRise(self, market_name):

        param = {
            "count": 3,
            "market" : market_name
        }

        res = requests.get(self.server_url + "/v1/candles/days", headers=self.getHeaders(), params=param)

        for item in res.json():

            # 3일(당일 포함) 중 하루라도 양봉이 아닐 경우 바로 False 반환
            if item['trade_price'] < item['opening_price']:
                return False

        return True
    
    # 현재 가격을 웹 소켓을 통해 얻어온다.
    async def websocket_connect(self, market_items):

        # 웹 소켓에 접속을 합니다.
        async with websockets.connect(WEBSOCKET_URL) as websocket:        

            for market_name in market_items:

                send_data = str([{"ticket":"GetPrice"},{"type":"ticker","codes":[market_name]}])
                await websocket.send(send_data)
            
                # 웹 소켓 서버로 부터 메시지가 오면 콘솔에 출력합니다.
                try:
                    data = await websocket.recv()
                    data = json.loads(data.decode('utf-8'))

                    self.coins_info[data['code']]["trade_price"] = data['trade_price']
                    self.coins_info[data['code']]["opening_price"] = data['opening_price']

                except websockets.ConnectionClosed:
                    break