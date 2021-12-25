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
    parser.add_argument('-d', '--down', required=False, default=1.5, help='목표가에서 얼마나 떨어지면 매도할지 퍼센트', dest='down')
    parser.add_argument('-f', '--firstdown', required=False, default=3, help='매수가에서 얼마나 떨어지면 매도할지 퍼센트', dest='firstdown')
   
    return_arg_data['percent'] = parser.parse_args().percent
    return_arg_data['want'] = parser.parse_args().want
    return_arg_data['down'] = parser.parse_args().down
    return_arg_data['firstdown'] = parser.parse_args().firstdown

    return return_arg_data

# 코인이름 인자로 입력
INPUT_COIN_PROPORTION = float(get_arguments()['percent'])
INPUT_COIN_WANT = float(get_arguments()['want'])
INPUT_COIN_DOWN = float(get_arguments()['down'])
INPUT_COIN_FIRST_DOWN = float(get_arguments()['firstdown'])

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
CoinAccount = Account(upbitUtil.getAllCoinList())

# 전체 코인 정보 초기 설정
upbitUtil.setCoinInfo()

#################### 스케줄 모음 ####################

# 오늘 판매한 코인 목록 초기화
def dailyExec():
    CoinAccount.ResetTodaySellList()

# MA 재설정 함수(스케줄에 사용)
def everyhourExec():
    for CoinName in CoinAccount.watch_coin_list:
        upbitUtil.setMA(CoinName, 5)
        upbitUtil.setMA(CoinName, 30)
        time.sleep(0.5)

# 매일 0시에 각 MA 재 설정(15초 딜레이)
schedule.every().day.at("09:00:15").do(dailyExec)

# 매 시간 MA 초기화
schedule.every().hour.at(":00").do(everyhourExec)

##################################################

# 최초 시작 시 MA와 가격 설정 함수 동작
everyhourExec()
asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))
asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))

for CoinName in CoinAccount.watch_coin_list:

    # 코인을 기존에 보유하고 있을 때 (가장 처음 실행만)
    if upbitUtil.isCoinHold(CoinName):

        # 나의 코인 목록 추가
        MYCOIN = Coin(CoinName, INPUT_COIN_PROPORTION, INPUT_COIN_WANT, INPUT_COIN_DOWN, INPUT_COIN_FIRST_DOWN)
        CoinAccount.AddCoin(MYCOIN)

        # 평균 매수가 재 설정
        MYCOIN.setBuyPrice(upbitUtil.getBuyprice(CoinName))

        # 수익 실현 매수가 초기 설정
        MYCOIN.setReturnLinePrice(upbitUtil.coins_info[CoinName]['MA30'] * (1 + (MYCOIN.coin_want_return / 100)))

        # 손절 가격 초기 설정
        MYCOIN.setExitLinePrice(float(MYCOIN.buy_price) * (1 - (MYCOIN.first_down_line / 100)))

# 시작 메세지 전송
SendSlackMessage(INFO_MESSAGE + "[+] 코인 자동 매매 시작")

##################### 무한 반복 (5초마다 가격 확인 후 동작) ####################

while True:

    # # 5초 딜레이
    time.sleep(3)

    # 코인의 현재 가격과 시가 설정
    asyncio.get_event_loop().run_until_complete(upbitUtil.websocket_connect(CoinAccount.watch_coin_list))

    # 현재 소유중인 코인 이름 목록
    hold_coins = CoinAccount.GetHoldCoinList()
    logging.info("보유 코인 목록 : {}".format(hold_coins))

    # 투자 유의 코인 이름 목록
    warning_coins = upbitUtil.GetWarningcoin()

    for CoinName in CoinAccount.watch_coin_list:

        # 상장된지 30일도 되지 않은 코인은 거래하지 않음
        # 사전에 MA값을 None으로 처리
        if upbitUtil.coins_info[CoinName]['MA30'] == None and upbitUtil.coins_info[CoinName]['MA5'] == None:
            continue

        # 오늘 이미 판매한 코인들은 당일엔 더 이상 매수 / 매도를 하지 않음
        if CoinName in CoinAccount.today_sell_coin_list:
            continue

        # 코인 보유 시(매도 조건 확인)
        if CoinName in hold_coins:

            if CoinName in warning_coins:
                SendSlackMessage(INFO_MESSAGE + "[+] {} 코인이 투자 유의 종목으로 지정되었습니다.\n확인을 권장드립니다.".format(CoinName))

            # 코인 정보 얻어오기
            MYCOIN = CoinAccount.GetCoin(CoinName)
                        
            logging.info("[-] {} 코인\n\t현재 가격 : {}\n\t매수 평균 : {}\n\t{}차 목표가(+{}%) : {}\n\t손절 가격 : {}"
            .format(
                MYCOIN.market_name, 
                upbitUtil.coins_info[CoinName]['trade_price'],
                MYCOIN.buy_price,
                MYCOIN.jump_num + 1,
                (MYCOIN.jump_num + 1) * MYCOIN.coin_want_return,
                MYCOIN.return_line_price,
                MYCOIN.exit_line_price
            ))

            # 수익률 만족 => 목표 가격 & 손절 가격 재설정
            if upbitUtil.coins_info[CoinName]['trade_price'] > MYCOIN.return_line_price:
                
                MYCOIN.upJumpNum()

                # 손절 가격을 기존 목표가로 설정
                MYCOIN.setExitLinePrice(MYCOIN.return_line_price * (1 - (MYCOIN.down_line / 100)))

                # 재 목표 가격을 (기존 목표가 * 목표 상승률)값으로 재 설정
                MYCOIN.setReturnLinePrice(upbitUtil.coins_info[CoinName]['MA30'] * (1 + ((MYCOIN.coin_want_return * MYCOIN.jump_num + 1) / 100)))

                # 로그 설정
                logging.info("[+] {} 코인 {}차 목표가 달성!(+{}%)\n\t{}차 목표가(+{}%) : {} / 손절가 : {}".format(
                    MYCOIN.market_name, 
                    MYCOIN.jump_num, 
                    MYCOIN.jump_num * MYCOIN.coin_want_return,
                    MYCOIN.jump_num + 1,
                    (MYCOIN.jump_num + 1) * MYCOIN.coin_want_return,
                    MYCOIN.return_line_price,
                    MYCOIN.exit_line_price
                ))

                # 슬랙으로 전달
                SendSlackMessage(INFO_MESSAGE + "[+] {} 코인 {}차 목표가 달성!(+{}%)\n\t{}차 목표가(+{}%) : {} / 손절가 : {}".format(
                    MYCOIN.market_name, 
                    MYCOIN.jump_num, 
                    MYCOIN.jump_num * MYCOIN.coin_want_return,
                    MYCOIN.jump_num + 1,
                    (MYCOIN.jump_num + 1) * MYCOIN.coin_want_return,
                    MYCOIN.return_line_price,
                    MYCOIN.exit_line_price
                ))
            
            # 손절 가격 도달 시 매도
            elif upbitUtil.coins_info[CoinName]['trade_price'] < MYCOIN.exit_line_price:
                
                # 매도 가능한 수량 확인
                orderable_volume = upbitUtil.getCanSellVolume(MYCOIN.market_name)
                
                # 매도 가능할 때
                if orderable_volume > 0:
                    
                    # 주문을 위한 헤더 설정
                    headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

                    # 코인 판매
                    upbitUtil.orderCoin(MYCOIN.market_name, SELL, orderable_volume, upbitUtil.coins_info[CoinName]['trade_price'], headers)
                    
                    # 오늘 판매한 코인 목록에 추가, 판매한 당일은 더이상 매수 / 매도를 하지 않음
                    CoinAccount.AddTodaySellList(MYCOIN.market_name)

                    # 로그 설정
                    logging.info("[+] {} 코인 {} 가격에 매도\n\t목표가 총 {}번 달성!(+{}%)".format(
                        MYCOIN.market_name,
                        upbitUtil.coins_info[CoinName]['trade_price'],
                        MYCOIN.jump_num, 
                        MYCOIN.jump_num * MYCOIN.coin_want_return
                    ))

                    # 슬랙으로 전달
                    SendSlackMessage(INFO_MESSAGE + "[+] {} 코인 {} 가격에 매도\n\t목표가 총 {}번 달성!(+{}%)".format(
                        MYCOIN.market_name,
                        upbitUtil.coins_info[CoinName]['trade_price'],
                        MYCOIN.jump_num, 
                        MYCOIN.jump_num * MYCOIN.coin_want_return
                    ))

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
                    MYCOIN = Coin(CoinName, INPUT_COIN_PROPORTION, INPUT_COIN_WANT, INPUT_COIN_DOWN, INPUT_COIN_FIRST_DOWN)

                    # 보유 코인 목록 추가
                    CoinAccount.AddCoin(MYCOIN)

                    # 구입 가격 설정
                    MYCOIN.setBuyPrice(upbitUtil.coins_info[CoinName]['trade_price'])

                    # 수익 실현 매수가 초기 설정
                    MYCOIN.setReturnLinePrice(upbitUtil.coins_info[CoinName]['MA30'] * (1 + (MYCOIN.coin_want_return / 100)))

                    # 손절 가격 초기 설정
                    MYCOIN.setExitLinePrice(upbitUtil.coins_info[CoinName]['trade_price'] * (1 - (MYCOIN.first_down_line / 100)))

                    # 로그 설정
                    logging.info("[+] {} 코인 매수 완료\n\t{}차 목표가(+{}%) : {} / 손절가 : {}".format(
                        MYCOIN.market_name, 
                        MYCOIN.jump_num + 1, 
                        (MYCOIN.jump_num + 1) * MYCOIN.coin_want_return,
                        MYCOIN.return_line_price,
                        MYCOIN.exit_line_price
                    ))

                    # SLACK 설정
                    SendSlackMessage(INFO_MESSAGE + "[+] {} 코인 매수 완료\n\t{}차 목표가(+{}%) : {} / 손절가 : {}".format(
                        MYCOIN.market_name, 
                        MYCOIN.jump_num + 1, 
                        (MYCOIN.jump_num + 1) * MYCOIN.coin_want_return,
                        MYCOIN.return_line_price,
                        MYCOIN.exit_line_price
                    ))
        
    ########## 1회 작업이 끝난 후 ##########

    # 스케줄 확인
    schedule.run_pending()

    ########################################

######################################################################