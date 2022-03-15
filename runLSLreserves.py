import requests as req
from bs4 import BeautifulSoup
import pyrebase
import json
import os

from datetime import datetime
import pytz

KST = pytz.timezone('Asia/Seoul')
SIGNIN_URL = "http://academic.petapop.com/sign/actionLogin.do"
APPLY_URL = "http://academic.petapop.com/self/requestSelfLrn.do"


def cleanUp(str):
    strList = str.split()
    result = " ".join(strList)
    return result


dayOfWeekToday = datetime.utcnow().astimezone(KST).weekday()

firebaseConfig = json.loads(os.environ['FIREBASE_CONFIG'])

# with open("C:\\React\\cbshportal\\src\\auth\\firebase-config.json") as f:
#     firebaseConfig = json.load(f)

firebase = pyrebase.initialize_app(firebaseConfig)
db = firebase.database()

totalReserveList = db.child('reservedLSL').get().val()
userData = db.child('users/students').get().val()
homeroomTeacherCodes = db.child('config/homeroomTeacher').get().val()

for userUuid, reserves in totalReserveList.items():

    print(f"For user [{userData[userUuid]['name']}]:")

    userCredential = userData[userUuid]["legacySelfLearnCredentials"]
    userHomeroomClass = str(
        userData[userUuid]["grade"]) + str(userData[userUuid]["classNumber"])

    userHomeroomTeacherCode = homeroomTeacherCodes[userHomeroomClass]

    applyDatas = []

    for reserveIndex, eachReserve in enumerate(reserves):
        if eachReserve['dayOfWeek'][dayOfWeekToday]:
            print(f"RUN) Reserve #{reserveIndex} is for today.")
            periods = eachReserve['periods']

            applyData = {
                'roomTcherId': userHomeroomTeacherCode,
                'cchTcherId': eachReserve['conductingTeacherCode'],
                'clssrmId': eachReserve['classroomCode'],
                'actCode': eachReserve['actCode'],
                'actCn': eachReserve['actContent'],
                'sgnId': datetime.utcnow().astimezone(KST).strftime(r"%Y%m%d")
            }

            for period in periods:
                applyData['lrnPd'] = period

                applyDatas.append(applyData.copy())
        
        else:
            print(f"RUN) Reserve #{reserveIndex} is not for today.")
            continue

    with req.session() as sess:
        res = sess.post(SIGNIN_URL, data=userCredential)
        rawPage = BeautifulSoup(res.content.decode('utf-8'), "html.parser")

        if cleanUp(rawPage.li.get_text()) == "선생님은 가입해주세요.":
            print(f"FAIL) Failed to login for {userData[userUuid]['name']}.")
            # 로그인 실패
            continue

        for applyData in applyDatas:
            res = sess.post(APPLY_URL, data=applyData)
            response = json.loads(res.content.decode('utf-8'))

            if response['result']['success'] == True:
                print(f"SUCCESS) {response['slrnNo']}")
                # 성공
            else:
                print('Fail')
                # 실패
