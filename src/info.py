from util import *
from util.upbit import *
from util.info import *
import schedule
import time

logging.disable()

upbitUtil = UpbitUtil(API_ACCESS_KEY, API_SECRET_KEY)
BEFORE_ALL_KRW = upbitUtil.getAllKRW()

def InfoGetAllKRW():

    global BEFORE_ALL_KRW

    now_time = time.strftime('%Y-%m-%d', time.localtime(time.time()))
    NOW_ALL_KRW = upbitUtil.getAllKRW()
    UP_DOWN_CHAR = ""
    UP_DOWN_CHAR2 = ""

    amount = NOW_ALL_KRW - BEFORE_ALL_KRW
    percent = (abs(amount) / BEFORE_ALL_KRW) * 100

    if amount == 0:
        UP_DOWN_CHAR = 'π'
        UP_DOWN_CHAR2 = ''
    elif amount > 0:
        UP_DOWN_CHAR = 'π'
        UP_DOWN_CHAR2 = '+'
    elif amount < 0:
        UP_DOWN_CHAR = 'π'
        UP_DOWN_CHAR2 = '-'

    SendSlackMessage(KRW_MESSAGE + "[ TODAY ] {}\n[ μμ° ] {:,}β©\n[ AMOUNT ] {} {:,}β© *[ {}{:.2f}% ]*".format(now_time, NOW_ALL_KRW, UP_DOWN_CHAR, amount, UP_DOWN_CHAR2, percent))

    BEFORE_ALL_KRW = NOW_ALL_KRW

# μ΅μ΄ 1ν λμ μμ° νμΈ
InfoGetAllKRW()

# λ§€μΌ 18μμ νμ¬ λμ μ΄ μμ°μ΄ μΌλ§μΈμ§ μλ¦Ό
schedule.every().day.at("18:00").do(InfoGetAllKRW)

while True:
    schedule.run_pending()
    time.sleep(1)