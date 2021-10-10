from util import *

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
BEFORE_ALL_KRW = 0

def InfoGetAllKRW():

    global BEFORE_ALL_KRW

    now_time = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    NOW_ALL_KRW = upbitUtil.getAllKRW()
    UP_DOWN_CHAR = ""
    UP_DOWN_CHAR2 = ""

    if BEFORE_ALL_KRW == 0:
        SendSlackMessage(KRW_MESSAGE + "[ TODAY ] {}\n[ 자산 ] {:,}₩".format(now_time, NOW_ALL_KRW))
    else:
        amount = NOW_ALL_KRW - BEFORE_ALL_KRW
        percent = (abs(amount) / BEFORE_ALL_KRW) * 100

        if amount == 0:
            UP_DOWN_CHAR = '😐'
            UP_DOWN_CHAR2 = ''
        elif amount > 0:
            UP_DOWN_CHAR = '👍'
            UP_DOWN_CHAR2 = '+'
        elif amount < 0:
            UP_DOWN_CHAR = '👎'
            UP_DOWN_CHAR2 = '-'

        SendSlackMessage(KRW_MESSAGE + "[ TODAY ] {}\n[ 자산 ] {:,}₩\n[ AMOUNT ] {} {:,}₩ *[ {}{:.2f}% ]*".format(now_time, NOW_ALL_KRW, UP_DOWN_CHAR, amount, UP_DOWN_CHAR2, percent))

    BEFORE_ALL_KRW = NOW_ALL_KRW - 10000

# 매일 18시에 현재 나의 총 자산이 얼마인지 알림
schedule.every().day.at("18:00").do(InfoGetAllKRW)

while True:
    schedule.run_pending()
    time.sleep(1)