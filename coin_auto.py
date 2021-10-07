from util import *
import argparse

# 인자 값 받아오기
def get_arguments():

    return_arg_data = {}

    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', required=True, help='coin korean name', dest='name')
    parser.add_argument('-p', '--percent', required=False, default=100, help='The proportion(percent) of A coin in total assets', dest='percent')
    parser.add_argument('-u', '--upline', required=False, default=2, help='Up line percent', dest='upline')
    parser.add_argument('-d', '--downline', required=False, default=3, help='Down line percent', dest='downline')
   
    return_arg_data['name'] = parser.parse_args().name
    return_arg_data['percent'] = parser.parse_args().percent
    return_arg_data['upline'] = parser.parse_args().upline
    return_arg_data['downline'] = parser.parse_args().downline

    return return_arg_data

# 코인이름 인자로 입력
INPUT_COIN_NAME = get_arguments()['name']
INPUT_COIN_PROPORTION = int(get_arguments()['percent'])
INPUT_UP_LINE = int(get_arguments()['upline'])
INPUT_DOWN_LINE = int(get_arguments()['downline'])

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
MYCOIN = Coin(INPUT_COIN_NAME, INPUT_COIN_PROPORTION, up_line_per=INPUT_UP_LINE, down_line_per=INPUT_DOWN_LINE)

# 현재 해당 코인 보유하고 있지 않을 때 (가장 처음 실행만)
if not upbitUtil.isCoinHold(MYCOIN.market_name):

    # 현재 가격 설정
    # 이전 가격 & 체크라인 가격도 기본값으로 현재 가격과 동일하게 설정
    MYCOIN.setCurrentPrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))
    MYCOIN.setBeforePrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))
    MYCOIN.setCheckLinePrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))

    # 매수 가능한 수량 확인
    current_krw = upbitUtil.getCurrentKRW(MYCOIN.coin_proportion)

    order_volume = upbitUtil.getCanBuyVolume(MYCOIN.market_name, MYCOIN.current_price, current_krw)

    # 주문을 위한 헤더 설정
    headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

    # 코인 구입
    upbitUtil.orderCoin(MYCOIN.market_name, BUY, order_volume, MYCOIN.current_price, headers)

    # 코인 보유 여부 True로 변경
    MYCOIN.setisCoinHold(True)

# 현재 해당 코인을 보유하고 있을 때 (가장 처음 실행만)
else:

    # 현재 가격 설정
    # 이전 가격 & 체크라인 가격도 기본값으로 현재 가격과 동일하게 설정
    MYCOIN.setCurrentPrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))
    MYCOIN.setBeforePrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))
    MYCOIN.setCheckLinePrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))

    # 코인 보유 여부 True로 변경
    MYCOIN.setisCoinHold(True)

SendSlackMessage(INFO_MESSAGE + "[+] {} 코인({}) 자동 매매 시작".format(MYCOIN.market_name, MYCOIN.coin_korean_name))

# 무한 반복 (5초마다 가격 확인 후 동작)
while True:

    # 코인의 현재 가격 설정
    MYCOIN.setCurrentPrice(upbitUtil.getCurrentPrice(MYCOIN.market_name))

    # 코인의 보유 여부 확인
    MYCOIN.setisCoinHold(upbitUtil.isCoinHold(MYCOIN.market_name))

    # 코인 보유 시
    if MYCOIN.is_coin_hold:

        # 하락 기준에 충족할 때 -> down 모드 [ 매도 ]
        if MYCOIN.current_price < MYCOIN.down_line_price:
            
            # 매도 가능한 수량 확인
            order_volume = upbitUtil.getCanSellVolume(MYCOIN.market_name)

            # 주문을 위한 헤더 설정
            headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

            # 코인 판매
            upbitUtil.orderCoin(MYCOIN.market_name, SELL, order_volume, MYCOIN.current_price, headers)

            # down 모드 설정
            MYCOIN.setCoinMode("down")

            # 코인 보유 여부 False로 변경
            MYCOIN.setisCoinHold(False)

            # 기준 가격 다시 설정
            MYCOIN.setCheckLinePrice(MYCOIN.current_price)

            # 로그 프린트
            logging.info("\t[-] ALL 매도 & {} 가격으로 ALL 매수 설정 [ 코인 이름 : {} / Mode : {} / isHold : {} ]".format(MYCOIN.up_line_price, MYCOIN.market_name, MYCOIN.coin_mode, MYCOIN.is_coin_hold))

        # 상승 기준에 충족할 때 -> up 모드
        elif MYCOIN.current_price > MYCOIN.check_line_price:
            
            # up 모드 설정
            MYCOIN.setCoinMode("up")

            # 기준 가격 다시 설정
            MYCOIN.setCheckLinePrice(MYCOIN.current_price)

            # 로그 프린트
            logging.info("\t[-]{} 가격으로 ALL 매도 설정 [ 코인 이름 : {} / Mode : {} / isHold : {} ]".format(MYCOIN.down_line_price, MYCOIN.market_name, MYCOIN.coin_mode, MYCOIN.is_coin_hold))

        # 그 외 -> pass 모드
        else:
            
            # pass 모드 설정
            MYCOIN.setCoinMode("pass")

            # 로그 프린트
            logging.info("\t[-]현재 가격 : {} [ 코인 이름 : {} / Mode : {} / isHold : {} ]".format(MYCOIN.current_price, MYCOIN.market_name, MYCOIN.coin_mode, MYCOIN.is_coin_hold))

    # 코인 미 보유 시
    else:

        # 하락 중 일 때 -> down 모드 설정 후 기준 가격 변경
        if MYCOIN.current_price < MYCOIN.check_line_price:
            
            # down 모드 설정
            MYCOIN.setCoinMode("down")

            # 기준 가격 다시 설정
            MYCOIN.setCheckLinePrice(MYCOIN.current_price)

            # 로그 프린트
            logging.info("\t[-]{} 가격으로 ALL 매수 설정 [ 코인 이름 : {} / Mode : {} / isHold : {} ]".format(MYCOIN.up_line_price, MYCOIN.market_name, MYCOIN.coin_mode, MYCOIN.is_coin_hold))

        # 매수 기준 가격보다 높을 때 -> up 모드 [ 매수 ]
        elif MYCOIN.current_price > MYCOIN.up_line_price:

            # 매수 가능한 수량 확인
            current_krw = upbitUtil.getCurrentKRW(MYCOIN.coin_proportion)
            order_volume = upbitUtil.getCanBuyVolume(MYCOIN.market_name, MYCOIN.current_price, current_krw)

            # 주문을 위한 헤더 설정
            headers = upbitUtil.getHeaders(query={'market': MYCOIN.market_name})

            # 코인 구입
            upbitUtil.orderCoin(MYCOIN.market_name, BUY, order_volume, MYCOIN.current_price, headers)

            # up 모드로 설정
            MYCOIN.setCoinMode("up")

            # 코인 보유 여부 True로 변경
            MYCOIN.setisCoinHold(True)

            # 기준 가격 다시 설정
            MYCOIN.setCheckLinePrice(MYCOIN.current_price)

            # 로그 프린트
            logging.info("\t[-]{} 가격으로 ALL 매도 설정 [ 코인 이름 : {} / Mode : {} / isHold : {} ]".format(MYCOIN.down_line_price, MYCOIN.market_name, MYCOIN.coin_mode, MYCOIN.is_coin_hold))

        # 그 외 -> pass 모드
        else:

            # pass 모드로 설정
            MYCOIN.setCoinMode("pass")

            # 로그 프린트
            logging.info("\t[-] 현재 가격 : {} [ 코인 이름 : {} / Mode : {} / isHold : {} ]".format(MYCOIN.current_price, MYCOIN.market_name, MYCOIN.coin_mode, MYCOIN.is_coin_hold))
    
    # 모든 작업 끝난 후, 이전 가격을 현재 가격으로 설정
    MYCOIN.setBeforePrice(MYCOIN.current_price)
    time.sleep(5)