from util import *
from util.coin import *
from util.upbit import *
from util.info import *

import argparse

# 인자 값 받아오기
def get_arguments():

    return_arg_data = {}

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', required=True, help='코인의 한글명', dest='name')
    parser.add_argument('-p', '--percent', required=False, default=100, help='이 코인이 전체 자산에서 차지하는 비율', dest='percent')
    parser.add_argument('-w', '--want', required=False, default=10, help='원하는 수익률(퍼센트)', dest='want')
    parser.add_argument('-d', '--down', required=False, default=1.5, help='5일장에서 얼마나 떨어지면 매도할지 퍼센트', dest='down')
   
    return_arg_data['name'] = parser.parse_args().name
    return_arg_data['percent'] = parser.parse_args().percent
    return_arg_data['want'] = parser.parse_args().want
    return_arg_data['down'] = parser.parse_args().down

    return return_arg_data

# 코인이름 인자로 입력
INPUT_COIN_NAME = get_arguments()['name']
INPUT_COIN_PROPORTION = int(get_arguments()['percent'])
INPUT_COIN_WANT = int(get_arguments()['want'])
INPUT_COIN_DOWN = int(get_arguments()['down'])

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
MYCOIN = Coin(INPUT_COIN_NAME, INPUT_COIN_PROPORTION, INPUT_COIN_WANT, INPUT_COIN_DOWN)

########## 실행 전 코인 현재 정보 받아오기 ##########
MYCOIN.setCurrentPrice(upbitUtil.getCurrentPrice(MYCOIN.market_name)) # 현재 가격 설정
MYCOIN.setBeforePrice(upbitUtil.getCurrentPrice(MYCOIN.market_name)) # 이전 가격은 초기값으로 현재 가격과 동일하게 설정
MYCOIN.setMA_5(upbitUtil.getMA(MYCOIN.market_name, 5)) # 5일 MA 설정
MYCOIN.setMA_30(upbitUtil.getMA(MYCOIN.market_name, 30)) # 30일 MA 설정
# MYCOIN.setTradeVolAvg(upbitUtil.getTradeVolAvg(4, MYCOIN.market_name)) # 거래량 설정

# 코인을 기존에 보유하고 있을 때 (가장 처음 실행만)
if upbitUtil.isCoinHold(MYCOIN.market_name):

    # 평균 매수가 설정
    MYCOIN.setBuyPrice(upbitUtil.getBuyprice(MYCOIN.market_name))

    # 수익 실현 가격 설정
    MYCOIN.setReturnLinePrice()

    # 코인 보유 여부 True로 변경
    MYCOIN.setisCoinHold(True)

##################################################

#################### 스케줄 모음 ####################

# 30일, 5일 MA 재설정 함수(스케줄에 사용)
def dailyExec():
    MYCOIN.setMA_5(upbitUtil.getMA(MYCOIN.market_name, 5))
    MYCOIN.setMA_30(upbitUtil.getMA(MYCOIN.market_name, 30))
    MYCOIN.setTodayOpeningprice(upbitUtil.getTodayOpeningprice(MYCOIN.market_name))

# 매일 0시에 각 MA 재 설정(15초 딜레이)
schedule.every().day.at("00:00:15").do(dailyExec)

##################################################
    
# 시작 메세지 전송
SendSlackMessage(INFO_MESSAGE + "[+] {} 코인({}) 자동 매매 시작".format(MYCOIN.market_name, MYCOIN.coin_korean_name))

##################### 무한 반복 (5초마다 가격 확인 후 동작) ####################
while True:

    # 코인의 현재 가격 설정
    MYCOIN.setCurrentPrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))

    # 코인의 보유 여부 확인
    MYCOIN.setisCoinHold(upbitUtil.isCoinHold(MYCOIN.market_name))

    # 코인 보유 시
    if MYCOIN.is_coin_hold:

        # 수익률 만족 or 5일선이 꺾일 때 [ 매도 ]
        if MYCOIN.current_price > MYCOIN.return_line_price and \
            MYCOIN.current_price < MYCOIN.MA_5 * (1 - (MYCOIN.down_line / 100)):
            
            # 매도 가능한 수량 확인
            orderable_volume = upbitUtil.getCanSellVolume(MYCOIN.market_name)
            
            # 매도 가능할 때
            if orderable_volume > 0:
                # 주문을 위한 헤더 설정
                headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

                # 코인 판매
                upbitUtil.orderCoin(MYCOIN.market_name, SELL, orderable_volume, MYCOIN.current_price, headers)
                
                # 평균 매수가 재 설정
                MYCOIN.setBuyPrice(upbitUtil.getBuyprice(MYCOIN.market_name))

                # 코인 보유 여부 False로 변경
                MYCOIN.setisCoinHold(False)

    # 코인 미 보유 시
    else:

        # 현재 가격이 30일선 넘을 때 [ 매수 ]
        # 시가가 30일선 밑 일때
        if  MYCOIN.current_price > MYCOIN.MA_30 and \
            MYCOIN.opening_price < MYCOIN.MA_30:

            # 매수 가능한 수량 확인
            current_krw = upbitUtil.getCurrentKRW(MYCOIN.coin_proportion)
            orderable_volume = upbitUtil.getCanBuyVolume(MYCOIN.market_name, MYCOIN.current_price, current_krw)

            # 매수 가능한 수량이 있을 때
            if orderable_volume > 0:
                # 주문을 위한 헤더 설정
                headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

                # 코인 구입
                upbitUtil.orderCoin(MYCOIN.market_name, BUY, orderable_volume, MYCOIN.current_price, headers)

                # 평균 매수가 재 설정
                MYCOIN.setBuyPrice(upbitUtil.getBuyprice(MYCOIN.market_name))

                # 수익 실현 매수가 재 설정
                MYCOIN.setReturnLinePrice()

                # 코인 보유 여부 True로 변경
                MYCOIN.setisCoinHold(True)

                logging.info("\t[-] {:,} 가격으로 ALL 매수 [ 코인 이름 : {} / isHold : {} ]".format(MYCOIN.return_line_price, MYCOIN.market_name, MYCOIN.is_coin_hold))
    
    ########## 1회 작업이 끝난 후 ##########
    # 모든 작업 끝난 후, 이전 가격을 현재 가격으로 설정
    MYCOIN.setBeforePrice(MYCOIN.current_price)

    # 스케줄 확인
    schedule.run_pending()

    ########################################

    # 5초 딜레이
    time.sleep(5)

######################################################################