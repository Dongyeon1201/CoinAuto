from base import *

# 슬랙으로 메세지 전송
def SendSlackMessage(msg):
    requests.post(
        "https://slack.com/api/chat.postMessage",
        headers={"Authorization": "Bearer " + SLACK_TOKEN},
        data={"channel": SLACK_CHANNEL,"text": msg}
    )