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
    parser.add_argument('-d', '--highdown', required=False, default=10, help='최고가에서 얼마나 떨어지면 매도할지 퍼센트', dest='highdown')
    parser.add_argument('-m', '--minprice', required=False, default=10, help='거래할 최소 금액', dest='minprice')
   
    return_arg_data['percent'] = parser.parse_args().percent
    return_arg_data['highdown'] = parser.parse_args().highdown
    return_arg_data['minprice'] = parser.parse_args().minprice

    return return_arg_data

# 코인이름 인자로 입력
INPUT_COIN_PROPORTION = float(get_arguments()['percent'])
INPUT_COIN_HIGH_DOWN = float(get_arguments()['highdown'])
INPUT_COIN_MINPRICE = float(get_arguments()['minprice'])

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
CoinAccount = Account(upbitUtil.getAllCoinList())

# 전체 코인 정보 초기 설정
frame = {
    "trade_price" : None, # 현재 가격
    "opening_price" : None, # 현재 캔들의 시가
    "BEFORE_MA5" : None,    # 직전 캔들의 MA5
    "MA5" : None,    # 현재의 MA5
    "BEFORE_MA60" : None,    # 직전 캔들의 MA60
    "MA60" : None  # 현재의 MA60
}
upbitUtil.setCoinInfo(frame)

#################### 일봉 스케줄 모음 ####################

# 오늘 판매한 코인 목록 초기화
# def daliyExec():
#     CoinAccount.ResetTodaySellList()

# 코인 정보 설정
def InfoExec():

    for CoinName in CoinAccount.watch_coin_list:

        # 정보 얻어오기
        res = upbitUtil.GetCoinCandles(CoinName, days=False, mins=240)

        if res == False:
            continue

        ## 얻어온 정보를 사용하여 MA 설정
        # MA5 설정 (현재가를 사용하여 유동적으로 MA5를 구하기 때문에, without_last 적용)
        upbitUtil.setMA(res, CoinName, 5, without_last=True)
        
        # BEFORE_MA5 설정
        upbitUtil.setBeforeMA(res, CoinName, 5)

        # MA60 설정 (현재가를 사용하여 유동적으로 MA5를 구하기 때문에, without_last 적용)
        upbitUtil.setMA(res, CoinName, 60, without_last=True)
        
        # BEFORE_MA60 설정
        upbitUtil.setBeforeMA(res, CoinName, 60)

        ## 얻어온 정보를 사용하여 현재 캔들의 시가 설정
        opening_price = res.json()[0]['opening_price']
        upbitUtil.setOpeningprice(opening_price=opening_price, market_name=CoinName)

######################################################

# 매일 9시에 각 MA 재 설정(15초 딜레이)
# schedule.every().day.at("09:00:15").do(daliyExec)

# 매 시간 MA 재 설정
# schedule.every().hour.at(":00").do(everyhourExec)

# 4시간마다 코인의 정보 재 설정
schedule.every().day.at("09:00:00").do(InfoExec)
schedule.every().day.at("13:00:00").do(InfoExec)
schedule.every().day.at("17:00:00").do(InfoExec)
schedule.every().day.at("21:00:00").do(InfoExec)
schedule.every().day.at("01:00:00").do(InfoExec)
schedule.every().day.at("05:00:00").do(InfoExec)

# 최초 시작 시 MA와 가격 설정 함수 동작
InfoExec()

#################################################

asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))

time.sleep(1)

# 매수 가능한 현금 확인
current_krw = upbitUtil.getCurrentKRW(INPUT_COIN_PROPORTION)

for CoinName in CoinAccount.watch_coin_list:

    # 코인을 기존에 보유하고 있을 때 (가장 처음 실행만)
    if upbitUtil.isCoinHold(CoinName):

        # 나의 코인 목록 추가
        MYCOIN = Coin(CoinName, INPUT_COIN_PROPORTION, INPUT_COIN_HIGH_DOWN)
        CoinAccount.AddCoin(MYCOIN)

        # 평균 매수가 재 설정
        MYCOIN.setBuyPrice(upbitUtil.getBuyprice(CoinName))

        # 최고 가격 초기 설정
        MYCOIN.SetHighPrice(MYCOIN.buy_price)

# 시작 메세지 전송
SendSlackMessage(INFO_MESSAGE + "[+] 코인 자동 매매 시작")

##################### 무한 반복 (5초마다 가격 확인 후 동작) ####################

while True:

    # 3초 딜레이
    time.sleep(3)
    
    # 코인의 현재 가격과 시가 설정
    asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))

    # 현재 소유중인 코인 이름 목록
    hold_coins = CoinAccount.GetHoldCoinList()
    logging.info("보유 코인 목록 : {}".format(hold_coins))

    # 투자 유의 코인 이름 목록
    warning_coins = upbitUtil.GetWarningcoin()

    # 모든 코인 조회
    for CoinName in CoinAccount.watch_coin_list:

        # 사전에 trade_able값을 False으로 처리된 코인은 거래하지 않음
        if upbitUtil.coins_info[CoinName]['trade_able'] == False:
            continue

        # 코인 보유 시(매도 조건 확인)
        if CoinName in hold_coins:

            if CoinName in warning_coins:
                SendSlackMessage(INFO_MESSAGE + "[+] {} 코인이 투자 유의 종목으로 지정되었습니다.\n확인을 권장드립니다.".format(CoinName))

            # 코인 정보 얻어오기
            MYCOIN = CoinAccount.GetCoin(CoinName)
                        
            logging.info("[-] {} 코인\n\t현재 가격 : {}\n\t매수 평균 : {}\n\tMA5 : {}\n\tMA60 : {}\n\BEFORE_MA5 : {}\n\BEFORE_MA60 : {}\n\t최고가 : {}\n\t현재 캔들 시가 : {}"
            .format(
                MYCOIN.market_name, 
                upbitUtil.coins_info[CoinName]['trade_price'],
                MYCOIN.buy_price,
                upbitUtil.coins_info[CoinName]['MA5'],
                upbitUtil.coins_info[CoinName]['MA60'],
                upbitUtil.coins_info[CoinName]['BEFORE_MA5'],
                upbitUtil.coins_info[CoinName]['BEFORE_MA60'],
                MYCOIN.high_price,
                upbitUtil.coins_info[CoinName]['opening_price']
            ))
            
            # 최고가 갱신 시 최고가 재 설정
            if upbitUtil.coins_info[CoinName]['trade_price'] > MYCOIN.high_price:
                
                MYCOIN.SetHighPrice(upbitUtil.coins_info[CoinName]['trade_price'])

                # 로그 설정
                logging.info("[+] {} 코인 최고가 달성!(+{:.2f}%) : {}".format(
                    MYCOIN.market_name, 
                    float(MYCOIN.high_price - MYCOIN.buy_price) / MYCOIN.buy_price * 100,
                    MYCOIN.high_price
                ))

            Current_MA5 = ((upbitUtil.coins_info[CoinName]['MA5'] * 4) + upbitUtil.coins_info[CoinName]['trade_price']) / 5                
            Current_MA60 = ((upbitUtil.coins_info[CoinName]['MA60'] * 59) + upbitUtil.coins_info[CoinName]['trade_price']) / 60 
            Exit_Price = MYCOIN.high_price * float(1-(INPUT_COIN_HIGH_DOWN/100))

            ## 손절 조건 만족 시 매도
            # 현재의 MA5가 MA60보다 낮을 때
            # 최고가에서 10%이상 낮아졌을 때
            # 둘 중 하나의 조건이라도 만족하면 매도
            if  Current_MA5 < Current_MA60 or \
                upbitUtil.coins_info[CoinName]['trade_price'] < Exit_Price:
                
                # 매도 가능한 수량 확인
                orderable_volume = upbitUtil.getCanSellVolume(MYCOIN.market_name)
                
                # 매도 가능할 때
                if orderable_volume > 0:
                    
                    # 주문을 위한 헤더 설정
                    headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

                    # 코인 판매 [시장가 매도]
                    upbitUtil.orderMarketCoin(CoinName, SELL, orderable_volume=orderable_volume, headers=headers)

                    # 코인 구입 [지정가 매도]
                    # upbitUtil.orderCoin(MYCOIN.market_name, SELL, orderable_volume, upbitUtil.coins_info[CoinName]['trade_price'], headers)
                    
                    # 오늘 판매한 코인 목록에 추가, 판매한 당일은 더이상 매수 / 매도를 하지 않음
                    CoinAccount.AddTodaySellList(MYCOIN.market_name)

                    # 로그 설정
                    logging.info("[+] {} 코인 {} 가격에 매도\n\t대략 {:.2f}% 변화".format(
                        MYCOIN.market_name,
                        upbitUtil.coins_info[CoinName]['trade_price'],
                        float(upbitUtil.coins_info[CoinName]['trade_price'] - MYCOIN.buy_price) / MYCOIN.buy_price * 100
                    ))

                    # 슬랙으로 전달
                    SendSlackMessage(INFO_MESSAGE + "[+] {} 코인 {} 가격에 매도\n\t대략 {:.2f}% 변화".format(
                        MYCOIN.market_name,
                        upbitUtil.coins_info[CoinName]['trade_price'],
                        float(upbitUtil.coins_info[CoinName]['trade_price'] - MYCOIN.buy_price) / MYCOIN.buy_price * 100
                    ))

                    # 보유 코인 목록 삭제
                    CoinAccount.DelCoin(MYCOIN)

                    time.sleep(0.1)

                    # 매수 가능한 현금량 갱신
                    current_krw = upbitUtil.getCurrentKRW(INPUT_COIN_PROPORTION)

        # 코인 미 보유 시(매수 조건 확인)
        else:
            
            # 현재 가격이 INPUT_COIN_MINPRICE 이상일때만 조회
            if upbitUtil.coins_info[CoinName]['trade_price'] > INPUT_COIN_MINPRICE:
                
                # 해당 코인의 MA값 설정
                Before_MA5 = upbitUtil.coins_info[CoinName]['BEFORE_MA5']
                Before_MA60 = upbitUtil.coins_info[CoinName]['BEFORE_MA60']
                Current_MA5 = ((upbitUtil.coins_info[CoinName]['MA5'] * 4) + upbitUtil.coins_info[CoinName]['trade_price']) / 5                
                Current_MA60 = ((upbitUtil.coins_info[CoinName]['MA60'] * 59) + upbitUtil.coins_info[CoinName]['trade_price']) / 60                

                # 관심 코인 목록에 존재하는 코인이, 현재의 MA5값도 MA60을 넘어섰을 때
                if CoinName in CoinAccount.favorite_coin_list:
                    
                    ## 매수 조건에 만족할 때
                    # 현재의 MA5가 현재의 MA60보다 높을 때
                    if Current_MA5 > Current_MA60 and current_krw > 5000:
                        # 매수 가능한 수량 확인 [지정가 매수에 사용]
                        # orderable_volume = upbitUtil.getCanBuyVolume(CoinName, upbitUtil.coins_info[CoinName]['trade_price'], current_krw)

                        # 매수 가능한 수량이 있을 때
                        # if orderable_volume > 0:

                        # 주문을 위한 헤더 설정
                        headers = upbitUtil.getHeaders(query={'market': CoinName})

                        # 코인 구입 [시장가 매수]
                        upbitUtil.orderMarketCoin(CoinName, BUY, order_krw=current_krw, headers=headers)

                        # 코인 구입 [지정가 매수]
                        # upbitUtil.orderCoin(CoinName, BUY, orderable_volume, upbitUtil.coins_info[CoinName]['trade_price'], headers)

                        # 코인 추가
                        MYCOIN = Coin(CoinName, INPUT_COIN_PROPORTION, INPUT_COIN_HIGH_DOWN)

                        # 보유 코인 목록 추가
                        CoinAccount.AddCoin(MYCOIN)

                        # 구입 가격 설정
                        MYCOIN.setBuyPrice(upbitUtil.coins_info[CoinName]['trade_price'])

                        # 최고 가격 초기 설정
                        MYCOIN.SetHighPrice(MYCOIN.buy_price)

                        # 로그 설정
                        logging.info("[+] {} 코인 매수 완료".format(
                            MYCOIN.market_name
                        ))

                        # SLACK 설정
                        SendSlackMessage(INFO_MESSAGE + "[+] {} 코인 매수 완료".format(
                            MYCOIN.market_name
                        ))

                        # 매수 가능한 현금 확인
                        current_krw = upbitUtil.getCurrentKRW(INPUT_COIN_PROPORTION)

                        # 관심 코인 목록에서 삭제
                        CoinAccount.DeleteFavoriteList(CoinName)

                # 관심 코인 목록에 존재하지 않는 코인일 때
                else:
                    # 이전 MA5 < 이전 MA60
                    # 현재 MA5 > 현재 MA60
                    # 관심 코인 추가 안되어 있는 경우
                    # 위 3개 모두 만족하는 코인 발견 시, 관심코인에 추가
                    if Before_MA5 < Before_MA60 and \
                        Current_MA5 > Current_MA60 and \
                        CoinName not in CoinAccount.favorite_coin_list:

                        CoinAccount.AddFavoriteList(CoinName)

    ########## 1회 작업이 끝난 후 ##########

    # 스케줄 확인
    schedule.run_pending()

    ########################################

######################################################################