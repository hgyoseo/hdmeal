from flask import Flask, make_response
import os
import datetime
from pytz import timezone
import urllib.request
from bs4 import BeautifulSoup
import json
from collections import OrderedDict
from flask_restful import request, Api, Resource
import re

# 디버그용
isDebugging = False
# today에서 사용됨
today_year = 2019
today_month = 7
today_date = 14
# 시간표에서 사용됨

# Flask 인스턴스 생성
app = Flask(__name__)
api = Api(app)


# 파서
def parse(year, month, date, isDebugging):
    year = str(year).zfill(2)
    month = str(month).zfill(2)
    date = str(date).zfill(2)

    try:
        url = urllib.request.urlopen("http://stu.goe.go.kr/sts_sci_md01_001.do?"
                                     "schulCode=J100005775"
                                     "&schulCrseScCode=3"
                                     "&schulKndScCode=03"
                                     "&schMmealScCode=2"
                                     "&schYmd=%s.%s.%s" % (year, month, date))
    except Exception as error:
        if isDebugging:
            print(error)
        return error
    data = BeautifulSoup(url, 'html.parser')
    data = data.find_all("tr")

    # 날싸 파싱
    loc = int()
    raw_date = data[0].find_all("th")
    try:
        for i in range(8):
            if year.zfill(4) + "." + month.zfill(2) + "." + date.zfill(2) in str(raw_date[i]):
                loc = i - 1
                date = raw_date[i].get_text().strip().replace(".", "-")
                if isDebugging:
                    print(loc)
                    print(date)
    except IndexError:
        return "IndexError"
    if not loc:
        return ""

    # 알레르기정보 선언
    allergy_filter = ["1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.",
                      "9.", "10.", "11.", "12.", "13.", "14.", "15.", "16.",
                      "17.", "18."]
    allergy_string = ["[난류]", "[우유]", "[메밀]", "[땅콩]", "[대두]", "[밀]", "[고등어]", "[게]",
                      "[새우]", "[돼지고기]", "[복숭아]", "[토마토]", "[아황산류]", "[호두]", "[닭고기]", "[쇠고기]",
                      "[오징어]", "[조개류]"]
    allergy_filter.reverse()
    allergy_string.reverse() # 역순으로 정렬 - 오류방지

    # 메뉴 파싱
    menu = data[2].find_all("td")
    try:
        menu = str(menu[loc]).replace('<br/>', '.\n') # 줄바꿈 처리
    except IndexError:
        return "IndexError"
    menu = re.sub('<.+?>', '', menu).strip()  # 태그 처리
    if menu == "":
        return "NoData"
    for i in range(18):
        menu = menu.replace(allergy_filter[i], allergy_string[i])
    if isDebugging:
        print(menu)

    # 칼로리 파싱
    kcal = data[45].find_all("td")
    kcal = kcal[loc].get_text().strip()
    if isDebugging:
        print(kcal)

    # 반환값 생성
    return_data = OrderedDict()
    return_data["date"] = date
    return_data["menu"] = menu
    return_data["kcal"] = kcal
    if isDebugging:
        print(return_data)

    with open(
            'data/' + date[:10] + '.json', 'w',
            encoding="utf-8") as make_file:
        json.dump(return_data, make_file, ensure_ascii=False, indent="\t")
        print("File Created")

    return 0


# 데이터 가져오기
def meal_data(year, month, date):
    # 자료형 변환
    year = str(year)
    month = str(month)
    date = str(date)

    if not os.path.isfile('data/' + year.zfill(4) + '-' + month.zfill(2) + '-' + date.zfill(2) +'.json'):
        parse(year, month, date, isDebugging)

    json_data = OrderedDict()
    try:
        with open('data/' + year.zfill(4) + '-' + month.zfill(2) + '-' + date.zfill(2) +'.json', encoding="utf-8") as data_file:
            data = json.load(data_file, object_pairs_hook=OrderedDict)
            json_data = data
    except FileNotFoundError:  # 파일 없을때
        if isDebugging:
            print("FileNotFound")
        json_data["message"] = "등록된 데이터가 없습니다."
    return json_data


# 시간표 가져오기
def timetable(Grade, Class, Weekday):
    try:
        url = urllib.request.urlopen("https://comci.azurewebsites.net/"
                                     "?schoolName=%ED%9D%A5%EB%8D%95%EC%A4%91%ED%95%99%EA%B5%90"
                                     "&gradeNumber=" + Grade + "&classNumber=" + Class + "&resultType=week")
    except Exception as error:
        if isDebugging:
            print("오류")
        return ""

    data = url.read().decode('utf-8')

    json_data = json.loads(data)

    if Weekday >= 5:
        return "등록된 데이터가 없습니다."
    data = json_data["data"]["result"][Weekday]
    header = ("%s(%s):\n\n" % (data["date"].replace(".", "-"), data["day"].replace("요일", "")))
    if isDebugging:
        print(header)
    if Weekday == 1 or Weekday == 3:
        body = ("1교시: %s\n2교시: %s\n3교시: %s\n4교시: %s\n5교시: %s\n6교시: %s\n7교시: %s"
                % (data["class01"][:2], data["class02"][:2], data["class03"][:2], data["class04"][:2],
                   data["class05"][:2], data["class06"][:2], data["class07"][:2]))
    else:
        body = ("1교시: %s\n2교시: %s\n3교시: %s\n4교시: %s\n5교시: %s\n6교시: %s"
                % (data["class01"][:2], data["class02"][:2], data["class03"][:2],
                   data["class04"][:2], data["class05"][:2], data["class06"][:2]))
    return header + body


# 특정 날짜
class Date(Resource):
    def get(self, year, month, date):
        return meal_data(year, month, date)

# Skill (Kakao i Open Builder) - 챗봇용
class Skill(Resource):
    def post(self):
        return_simpleText = OrderedDict()
        return_outputs = OrderedDict()
        return_list = list()
        return_template = OrderedDict()
        return_data = OrderedDict()
        def return_error():
            return_simpleText["text"] = "오류가 발생했습니다."
            return_outputs["simpleText"] = return_simpleText
            if not return_outputs in return_list:
                return_list.append(return_outputs)
            return_template["outputs"] = return_list
            return_data["version"] = "2.0"
            return_data["template"] = return_template
            return return_data
        sys_date = str()
        year = int()
        month = int()
        date = int()
        try:
            sys_date = json.loads(json.loads(request.data)["action"]["params"]["sys_date"])["date"]
        except Exception:
            return_error()
        try:
            year = datetime.datetime.strptime(sys_date, "%Y-%m-%d").timetuple()[0]
            month = datetime.datetime.strptime(sys_date, "%Y-%m-%d").timetuple()[1]
            date = datetime.datetime.strptime(sys_date, "%Y-%m-%d").timetuple()[2]
        except ValueError:
            return_error()
        meal = meal_data(year, month, date)
        if not "message" in meal:
            meal["message"] = "%s:\n\n%s\n\n열량: %s kcal" % (meal["date"], meal["menu"], meal["kcal"])
        return_simpleText["text"] = meal["message"]
        return_outputs["simpleText"] = return_simpleText
        if not return_outputs in return_list:
            return_list.append(return_outputs)
        return_template["outputs"] = return_list
        return_data["version"] = "2.0"
        return_data["template"] = return_template
        return return_data

# Skill 특정날짜(고정값) 조회
class SkillSpecificDate(Resource):
    def post(self):
        return_simpleText = OrderedDict()
        return_outputs = OrderedDict()
        return_list = list()
        return_template = OrderedDict()
        return_data = OrderedDict()
        def return_error():
            return_simpleText["text"] = "오류가 발생했습니다."
            return_outputs["simpleText"] = return_simpleText
            if not return_outputs in return_list:
                return_list.append(return_outputs)
            return_template["outputs"] = return_list
            return_data["version"] = "2.0"
            return_data["template"] = return_template
            return return_data
        specific_date = str()
        year = int()
        month = int()
        date = int()
        try:
            specific_date = json.loads(request.data)["action"]["params"]["date"]
        except Exception:
            return_error()
        try:
            year = datetime.datetime.strptime(specific_date, "%Y-%m-%d").timetuple()[0]
            month = datetime.datetime.strptime(specific_date, "%Y-%m-%d").timetuple()[1]
            date = datetime.datetime.strptime(specific_date, "%Y-%m-%d").timetuple()[2]
        except ValueError:
            return_error()
        if isDebugging:
            print(specific_date)
            print(year)
            print(month)
            print(date)
        meal = meal_data(year, month, date)
        if not "message" in meal:
            meal["message"] = "%s:\n\n%s\n\n열량: %s kcal" % (meal["date"], meal["menu"], meal["kcal"])
        return_simpleText["text"] = meal["message"]
        return_outputs["simpleText"] = return_simpleText
        if not return_outputs in return_list:
            return_list.append(return_outputs)
        return_template["outputs"] = return_list
        return_data["version"] = "2.0"
        return_data["template"] = return_template
        return return_data

# Skill 시간표 조회
class Timetable(Resource):
    def post(self):
        return_simpleText = OrderedDict()
        return_outputs = OrderedDict()
        return_list = list()
        return_template = OrderedDict()
        return_data = OrderedDict()
        def return_error():
            return_simpleText["text"] = "오류가 발생했습니다."
            return_outputs["simpleText"] = return_simpleText
            if not return_outputs in return_list:
                return_list.append(return_outputs)
            return_template["outputs"] = return_list
            return_data["version"] = "2.0"
            return_data["template"] = return_template
            return return_data
        Grade = str()
        Class = str()
        sys_date = str()
        Weekday = int()
        try:
            Grade = json.loads(request.data)["action"]["params"]["Grade"]
        except Exception:
            return_error()
        try:
            Class = json.loads(request.data)["action"]["params"]["Class"]
        except Exception:
            return_error()
        try:
            sys_date = json.loads(json.loads(request.data)["action"]["params"]["sys_date"])["date"]
        except Exception:
            return_error()
        try:
            Weekday = datetime.datetime.strptime(sys_date, "%Y-%m-%d").weekday()
        except ValueError:
            return_error()
        if isDebugging:
            print(Grade)
            print(Class)
            print(Weekday)
        tt = timetable(Grade, Class, Weekday)
        return_simpleText["text"] = tt
        return_outputs["simpleText"] = return_simpleText
        if not return_outputs in return_list:
            return_list.append(return_outputs)
        return_template["outputs"] = return_list
        return_data["version"] = "2.0"
        return_data["template"] = return_template
        return return_data

# 캐시 비우기
class PurgeCache(Resource):
    def get(self):
        dict_data = OrderedDict()
        try:
            file_list = [file for file in os.listdir("data") if file.endswith(".json")]
            for file in file_list:
                os.remove("data/" + file)
        except Exception as error:
            if isDebugging:
                dict_data["status"] = error
            else:
                dict_data["status"] = "Error"
        dict_data["status"] = "OK"
        return dict_data

# URL Router에 맵핑한다.(Rest URL정의)
api.add_resource(Date, '/date/<int:year>-<int:month>-<int:date>')
api.add_resource(Skill, '/skill-gateway/')
api.add_resource(SkillSpecificDate, '/skill-gateway/specificdate')
api.add_resource(Timetable, '/skill-gateway/tt')
api.add_resource(PurgeCache, '/purge/')

# 서버 실행
if __name__ == '__main__':
    app.run(debug=isDebugging)
