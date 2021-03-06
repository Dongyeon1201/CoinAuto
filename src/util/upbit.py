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

    # 투자 유의 종목 코인 확인
    def GetWarningcoin(self):
        headers = {"Accept": "application/json"}
        res = requests.request("GET", API_SERVER_URL + "/v1/market/all?isDetails=true", headers=headers)
        return [item['market'] for item in json.loads(res.text) if "KRW-" in item['market'] and item['market_warning'] == "CAUTION"]

    # MarketName을 사용하여 해당 코인의 가격 반환
    async def getCurrentPrice(self, market_items):

        current_price_info = {}

        # 웹 소켓에 접속을 합니다.
        async with websockets.connect(WEBSOCKET_URL, ping_interval=60) as websocket:        

            send_data = str([{"ticket":"CurrentPrice"},{"type":"ticker","isOnlySnapshot":True,"codes": market_items}])
            await websocket.send(send_data)
        
            # 웹 소켓 서버로 부터 메시지가 오면 콘솔에 출력합니다.
            for item in market_items:

                try:
                    data = await websocket.recv()
                    data = json.loads(data.decode('utf-8'))
                    current_price_info[item] = data['trade_price']

                except websockets.ConnectionClosed:
                    current_price_info[item] = 0
                    logging.error("[ Function Name : websocket_connect ]\n[+] 웹 소켓의 연결이 종료되었습니다.")

                except TimeoutError as e:
                    current_price_info[item] = 0
                    logging.error("[ Function Name : websocket_connect ]\n[+] 웹 소켓의 연결 가능 시간이 초과되었습니다.")

            
            return current_price_info

            # send_data = str([{"ticket":"GetPrice"},{"type":"ticker","isOnlySnapshot":True,"codes":[market_name]}])
            # await websocket.send(send_data)
        
            # # 웹 소켓 서버로 부터 메시지가 오면 콘솔에 출력합니다.
            # data = await websocket.recv()
            
            # if data == None:
            #     SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getCurrentPrice() ]\n[+] 현재 가격을 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```NONE```".format(res.status_code))
            # else:
            #     data = json.loads(data.decode('utf-8'))
            #     return data['trade_price']

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
            logging.error("[ Function Name : getWaitOrderList() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}".format(res.status_code))

            if res.text == None:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getWaitOrderList() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(res.status_code))
            else:
                SendSlackMessage(ERROR_MESSAGE + "[ Function Name : getWaitOrderList() ]\n[+] 주문 목록을 받아올 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

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

        account_info = res.json()

        if account_info[0]['currency'] == 'KRW':
            ALL_KRW += int(float(account_info[0]['balance']))
            account_info.pop(0)

        hold_coin_names = ["KRW-" + item['currency'] for item in account_info]
        hold_coin_current_price = asyncio.get_event_loop().run_until_complete(self.getCurrentPrice(hold_coin_names))

        for item in account_info:
            ALL_KRW += float(item['balance']) * float(hold_coin_current_price["KRW-" + item['currency']])
        
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

    # 시장가 코인 주문
    # order_krw : 총 주문 금액(10만원 주문 시 100000 으로 설정) [시장가 매수에 사용]
    # orderable_volume : 총 매도할 코인의 갯수 [시장가 매도에 사용] 
    def orderMarketCoin(self, market_name, order_side, headers, orderable_volume=None, order_krw=None):

        query = {
            'market': market_name,
        }

        # 매수
        if order_side == "bid":
            
            # 매수로 설정
            query['side'] = "bid"

            # 시장가 매수 주문 설정
            query['ord_type'] = 'price'

            # 총 주문 금액을 설정
            query['price'] = int(order_krw * (1-BID_FEE_KRW))

            # 주문 요청을 위한 헤더 생성
            headers = self.getHeaders(query=query)

            # 주문 요청
            res = requests.post(self.server_url + "/v1/orders", params=query, headers=headers)

            if res.status_code == 201:

                logging.info("{} 코인 매수 완료".format(market_name))
                # SendSlackMessage(INFO_MESSAGE + "{} 코인 매수 완료".format(market_name))

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

            # 시장가 매도 주문 설정
            query['ord_type'] = 'market'

            # 총 주문할 양을 설정
            query['volume'] = orderable_volume

            # 주문 요청을 위한 헤더 생성
            headers = self.getHeaders(query=query)
            res = requests.post(self.server_url + "/v1/orders", params=query, headers=headers)

            if res.status_code == 201:
                logging.info("{} 코인 매도 완료".format(market_name))
                SendSlackMessage(INFO_MESSAGE + "{} 코인 매도 완료".format(market_name))

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
    def setCoinInfo(self, frame):
        for CoinName in self.getAllCoinList():
            self.coins_info[CoinName] = copy.deepcopy(frame)

    # MA 구하기
    # without_last : 가장 최근 캔들에 대한 정보를 제외한 MA를 구해준다.
    # 30개 요청 후 without_last True로 실행 시 -> 가장 최근 캔들을 제외한 29개의 MA가 반환
    def setMA(self, res, market_name, count, without_last=False):

        MA = 0

        # 요청한 count보다 적은 코인은 MA를 None으로 처리, 거래를 하지 않음
        if len(res.json()) < count:
            self.coins_info[market_name]['trade_able'] = False
            return

        if without_last: 
            array = res.json()[1:count]
        else:
            array = res.json()[:count]
        
        for item in array:
            MA += item['trade_price']
                
        if without_last:
            self.coins_info[market_name]['MA{}'.format(count)] = MA / (count-1)
        else:
            self.coins_info[market_name]['MA{}'.format(count)] = MA / count

        self.coins_info[market_name]['trade_able'] = True

    # 현재 캔들 바로 직전의 MA를 구한다.
    def setBeforeMA(self, res, market_name, count):

        MA = 0
        
        # 요청한 count+1보다 적은 코인은 MA를 None으로 처리, 거래를 하지 않음
        if len(res.json()) < count+1:
            self.coins_info[market_name]['trade_able'] = False
            return

        array = res.json()[1:count+1]
        
        for item in array:
            MA += item['trade_price']

        self.coins_info[market_name]['BEFORE_MA{}'.format(count)] = MA / count
        self.coins_info[market_name]['trade_able'] = True

    # MarketName을 사용하여 해당 코인의 당일 시가 반환
    def setOpeningprice(self, opening_price, market_name):
        self.coins_info[market_name]['opening_price'] = opening_price

    # 일봉(당일 포함) 3일 연속 양봉인지 확인
    def isRise(self, market_name):

        param = {
            "count": 3,
            "market" : market_name
        }

        res = requests.get(self.server_url + "/v1/candles/days", headers=self.getHeaders(), params=param)
        # res = requests.get(self.server_url + "/v1/candles/minutes/60", headers=self.getHeaders(), params=param)

        for item in res.json():

            # 3일(당일 포함) 중 하루라도 양봉이 아닐 경우 바로 False 반환
            if item['trade_price'] < item['opening_price']:
                return False

        return True
    
    # 현재 가격을 웹 소켓을 통해 얻어온다.
    async def websocket_connect(self, market_items):

        # 웹 소켓에 접속을 합니다.
        async with websockets.connect(WEBSOCKET_URL, ping_interval=60) as websocket:        

            send_data = str([{"ticket":"GetPrice"},{"type":"ticker","isOnlySnapshot":True,"codes": market_items}])
            await websocket.send(send_data)
            
            for market_name in market_items:
            
                # 웹 소켓 서버로 부터 메시지가 오면 콘솔에 출력합니다.
                try:
                    data = await websocket.recv()
                    data = json.loads(data.decode('utf-8'))

                    self.coins_info[data['code']]['trade_price'] = data['trade_price']
                    # self.coins_info[data['code']]['opening_price'] = data['opening_price']

                except Exception as e:
                    print(e, flush=True)
                    logging.error(e)
                    SendSlackMessage(ERROR_MESSAGE + "현재가 조회를 위한 웹 소켓의 오류가 발생하였습니다.")
    
    # 캔들 정보 얻어오기
    def GetCoinCandles(self, market_name, count=200, days=True, mins=60):

        param = {
            "count": count,
            "market" : market_name
        }

        if days:
            res = requests.get(self.server_url + "/v1/candles/days", headers=self.getHeaders(), params=param)
        else:
            res = requests.get(self.server_url + "/v1/candles/minutes/{}".format(mins), headers=self.getHeaders(), params=param)

        if res.status_code == 200:
            return res
        else:
            logging.error("[ Function Name : GetCoinCandles() ]\n[+] {} 코인의 캔들 조회를 실패하였습니다.\n[-] ERROR : {}".format(market_name, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))
            SendSlackMessage(ERROR_MESSAGE + "[ Function Name : GetCoinCandles() ]\n[+] {} 코인의 캔들 조회를 실패하였습니다.\n[-] ERROR : {}".format(market_name, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))
            return False