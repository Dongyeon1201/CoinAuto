from logging import warning
from time import sleep
from util import *
from util import account
from util import upbit
from util.coin import *
from util.upbit import *
from util.info import *
from util.account import *

import argparse

# 인자 값 받아오기
def get_arguments():

    return_arg_data = {}

    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--percent', required=False, default=100, help='이 코인이 전체 자산에서 차지하는 비율', dest='percent')
    parser.add_argument('-w', '--want', required=False, default=10, help='원하는 수익률(퍼센트)', dest='want')
    parser.add_argument('-d', '--down', required=False, default=1.5, help='5일장에서 얼마나 떨어지면 매도할지 퍼센트', dest='down')
   
    return_arg_data['percent'] = parser.parse_args().percent
    return_arg_data['want'] = parser.parse_args().want
    return_arg_data['down'] = parser.parse_args().down

    return return_arg_data

# 코인이름 인자로 입력
INPUT_COIN_PROPORTION = int(get_arguments()['percent'])
INPUT_COIN_WANT = int(get_arguments()['want'])
INPUT_COIN_DOWN = int(get_arguments()['down'])

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
CoinAccount = Account(upbitUtil.getAllCoinList())

# 전체 코인 정보 초기 설정
upbitUtil.setCoinInfo()

for CoinName in CoinAccount.watch_coin_list:

    # 코인을 기존에 보유하고 있을 때 (가장 처음 실행만)
    if upbitUtil.isCoinHold(CoinName):

        # 나의 코인 목록 추가
        MYCOIN = Coin(CoinName, INPUT_COIN_PROPORTION, INPUT_COIN_WANT, INPUT_COIN_DOWN)
        CoinAccount.AddCoin(MYCOIN)

        # 평균 매수가 재 설정
        MYCOIN.setBuyPrice(upbitUtil.getBuyprice(CoinName))

        # 수익 실현 매수가 재 설정
        MYCOIN.setReturnLinePrice()

##################################################

#################### 스케줄 모음 ####################

# 30일, 5일 MA 재설정 함수(스케줄에 사용)
def dailyExec():
    for CoinName in CoinAccount.watch_coin_list:
        upbitUtil.setMA(CoinName, 5)
        upbitUtil.setMA(CoinName, 30)
        time.sleep(0.5)

# 매일 0시에 각 MA 재 설정(15초 딜레이)
schedule.every().day.at("00:00:15").do(dailyExec)

##################################################

# 최초 시작 시 MA와 가격 설정 함수 동작
dailyExec()
asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))
asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))

# 시작 메세지 전송
SendSlackMessage(INFO_MESSAGE + "[+] 코인 자동 매매 시작")

##################### 무한 반복 (5초마다 가격 확인 후 동작) ####################

while True:

    # 코인의 현재 가격과 시가 설정
    asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))

    # 현재 소유중인 코인 이름 목록
    hold_coins = CoinAccount.GetHoldCoinList()

    # 투자 유의 코인 이름 목록
    warning_coins = upbitUtil.GetWarningcoin()

    for CoinName in CoinAccount.watch_coin_list:

        # 코인 보유 시(매도 조건 확인)
        if CoinName in hold_coins:

            if CoinName in warning_coins:
                SendSlackMessage(INFO_MESSAGE + "[+] {} 코인이 투자 유의 종목으로 지정되었습니다.\n확인을 권장드립니다.".format(CoinName))

            MYCOIN = CoinAccount.GetCoin(CoinName)
            
            logging.info("\t[-] {} 코인 / 매수 평균 : {}".format(MYCOIN.market_name, MYCOIN.buy_price))

            # 수익률 만족 or 5일선이 꺾일 때 [ 매도 ]
            if upbitUtil.coins_info[CoinName]['trade_price'] > MYCOIN.return_line_price or \
                upbitUtil.coins_info[CoinName]['trade_price'] < upbitUtil.coins_info[CoinName]['MA5'] * (1 - (MYCOIN.down_line / 100)):
                
                # 매도 가능한 수량 확인
                orderable_volume = upbitUtil.getCanSellVolume(MYCOIN.market_name)
                
                # 매도 가능할 때
                if orderable_volume > 0:
                    
                    # 주문을 위한 헤더 설정
                    headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

                    # 코인 판매
                    upbitUtil.orderCoin(MYCOIN.market_name, SELL, orderable_volume, MYCOIN.current_price, headers)
                    
                    # 보유 코인 목록 삭제
                    CoinAccount.DelCoin(MYCOIN)

        # 코인 미 보유 시(매수 조건 확인)
        else:

            # 현재 가격이 30일선 넘을 때 [ 매수 ]
            # 시가가 30일선 밑 일때
            if  upbitUtil.coins_info[CoinName]['trade_price'] > upbitUtil.coins_info[CoinName]['MA30'] and \
                upbitUtil.coins_info[CoinName]['opening_price'] < upbitUtil.coins_info[CoinName]['MA30']:

                # 매수 가능한 수량 확인
                current_krw = upbitUtil.getCurrentKRW(INPUT_COIN_PROPORTION)
                orderable_volume = upbitUtil.getCanBuyVolume(CoinName, upbitUtil.coins_info[CoinName]['trade_price'], current_krw)

                # 매수 가능한 수량이 있을 때
                if orderable_volume > 0:

                    # 주문을 위한 헤더 설정
                    headers = upbitUtil.getHeaders(query={'market': CoinName})

                    # 코인 구입
                    upbitUtil.orderCoin(CoinName, BUY, orderable_volume, upbitUtil.coins_info[CoinName]['trade_price'], headers)

                    # 코인 추가
                    MYCOIN = Coin(CoinName, INPUT_COIN_PROPORTION, INPUT_COIN_WANT, INPUT_COIN_DOWN)

                    # 보유 코인 목록 추가
                    CoinAccount.AddCoin(MYCOIN)

                    # 평균 매수가 재 설정
                    MYCOIN.setBuyPrice(upbitUtil.getBuyprice(CoinName))

                    # 수익 실현 매수가 재 설정
                    MYCOIN.setReturnLinePrice()

                    logging.info("\t[-] {:,} 가격으로 ALL 매수 [ 코인 이름 : {} / isHold : {} ]".format(MYCOIN.return_line_price, MYCOIN.market_name, MYCOIN.is_coin_hold))
        
    ########## 1회 작업이 끝난 후 ##########

    # 스케줄 확인
    schedule.run_pending()

    ########################################

    # 5초 딜레이
    time.sleep(5)

######################################################################