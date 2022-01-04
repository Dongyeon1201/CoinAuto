from util.base import *
from util.info import SendSlackMessage

class Coin:

    def __init__(self, market_name, coin_proportion, high_down_line):

        # 서버 주소
        self.server_url = API_SERVER_URL    

        # 코인의 전체 자산 최대 비율
        self.coin_proportion = coin_proportion

        # 목표가에서 몇% 떨어졌을 때 매도할지 수치
        self.high_down_line = high_down_line

        # 코인 이름
        self.market_name = market_name

        # 목표가 도달 횟수
        self.jump_num = 0

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

            if res.text == None:
                SendSlackMessage("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```NONE```".format(korean_name, res.status_code))
            else:
                SendSlackMessage("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(korean_name, res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))
            

        else:
            logging.error("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}".format(korean_name, res.status_code))
            SendSlackMessage("[ Function Name : getMarketName() ]\n[+] {} 의 검색 결과를 확인할 수 없습니다. STATUS CODE : {}\n[ ERROR ] ```{}```".format(korean_name, res.status_code, json.dumps(json.loads(res.text),indent=4, sort_keys=True)))

    # 코인의 현재 가격 설정
    def setCurrentPrice(self, current_price):
        self.current_price = current_price
    
    # 코인의 이전 가격 설정
    def setBeforePrice(self, before_price):
        self.before_price = before_price

    # 코인의 수익 실현 지점 가격
    # 예시 : 수익 실현률 5% 일때, 수익 실현 가격은 (평단가 * 1.05)
    def setReturnLinePrice(self, return_price):
        self.return_line_price = return_price

    def setExitLinePrice(self, set_price):
        self.exit_line_price = set_price

    # 코인의 보유 여부 확인
    def setisCoinHold(self, is_coin_hold):
        self.is_coin_hold = is_coin_hold
    
    # 코인의 현재 거래량
    def setTradeRecent(self, trade_recent):
        self.trade_recent = trade_recent

    # 코인의 평균거래량
    def setTradeVolAvg(self, trade_vol_avg):
        self.trade_vol_avg = trade_vol_avg

    # 코인의 평균매수가
    def setBuyPrice(self, buy_price):
        self.buy_price = float(buy_price)

    def setTodayOpeningprice(self, opening_price):
        self.opening_price = opening_price

    def setIsRise(self, isRise):
        self.isRise = isRise

    def upJumpNum(self):
        self.jump_num += 1

    def SetHighPrice(self, high_price):
        self.high_price = float(high_price)