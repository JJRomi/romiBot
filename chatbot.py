# -*- coding: utf-8 -*-
import os

from flask import Flask, request, Response, make_response, json
from slackclient import SlackClient
import requests
import konlpy
import nltk
from konlpy.tag import Mecab
from flask.ext.restful import Api, Resource, reqparse, fields, marshal

app = Flask(__name__)
# SLACK BOT TOKEN
SLACK_BOT_UESR_TOKEN = os.environ.get('SLACK_BOT_USER_TOKEN')
SLACK_AUTH_TOKEN = os.environ.get('SLACK_AUTH_TOKEN')
# SLACK OAUTH
SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET =  os.environ.get('SLACK_CLIENT_SECRET')
SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')


class slackBot:
    def __init__(self):
        self.text = "안녕하세요!"
        self.channel_id = ""
        self.message = {}
        self.user_name = "Romi"
        self.user_emoji = ":monkey_face:"
        self.verification = SLACK_VERIFICATION_TOKEN
        self.slack_client = SlackClient(SLACK_BOT_UESR_TOKEN)
        self.code = ""
        self.type = ""
        self.location = ""
        self.type_code = ""

    def send_message(self):
        try:
            self.slack_client.api_call(
                "chat.postMessage",
                channel=self.channel_id,
                attachments=self.message,
                username=self.user_name,
                icon_emoji=self.user_emoji
            )
        except BaseException as ex:
            print("send_message (error) : ", ex)
            return 500

        return 200

    def oauth(self):
        self.slack_client.api_call(
            "oauth.access",
            client_id=SLACK_CLIENT_ID,
            client_secret=SLACK_CLIENT_SECRET,
            code=self.code
        )


class callAPI:
    def __init__(self):
        self.url = ""
        self.params = {}

    def get_send_api(self):
        try:
            response = requests.get(self.url, params=self.params)
            result = response.json()
        except BaseException as ex:
            print("\n send api error : ", ex, "\n")

        return result


# local test url
@app.route('/test', methods=['POST'])
def test():
    slackBot.text = request.form.get('text')
    slackBot.channel_id = request.form.get('channel_id')
    slackBot.type = request.form.get('type_code')

    extra_keyword(slackBot.text)
    keyword_addr()

    # response = slackBot.send_message()

    return Response()#, response


# button select message (type select)
@app.route('/webhook', methods=['POST'])
def btn_select():
    slackBot.text = request.form.get('text')
    slackBot.channel_id = request.form.get('channel_id')

    # text로 keyword 추출
    extra_keyword(slackBot.text)

    # 장소, 타입 정보 있는 지 확인 후 답변
    if slackBot.location == "":
        slackBot.message = [
            {
                'title': '장소를 알려주세요.',
                'text': '장소정보를 찾지 못했어요. 다시 상세하게 알려주세요.'
            }
        ]
    elif slackBot.type_code == "":
        slackBot.message = [
            {
                'title': '어떤 정보를 알려드릴까요?',
                'text': '원하시는 정보가 무엇인지 모르겠어요. 다시 상세하게 알려주세요.'
            }
        ]
    else:
        slackBot.message = [
            {
                "text": slackBot.location + "에서의 " + slackBot.type_code + " 찾고 계신가요??",
                "fallback": "",
                "callback_id": "select tour",
                "color": "#3AA3E3",
                "attachment_type": "default",
                'actions': [
                    {
                        "name": "location",
                        "text": "위치 중심 검색",
                        "type": "button",
                        "value": ""
                    },
                    {
                        "name": "type",
                        "text": "타입 중심 검색",
                        "type": "button",
                        "value": ""
                    },
                ]
            }
        ]
    response = slackBot.send_message()

    return Response(), response


@app.route('/slack/events', methods=['POST'])
def events():
    payload = request.get_data()
    data = json.loads(payload)

    return Response(data["challenge"], mimetype='application/x-www-form-urlencoded')


@app.route('/slack/oauth', methods=['POST'])
def oauth():
    slackBot.code = request.args.get('code')
    slackBot.oauth()

    return Response(), 200


# button click actions
@app.route('/slack/actions', methods=['POST'])
def interactive_callback():
    payload = json.loads(request.form['payload'])
    slackBot.channel_id = payload['channel']['id']

    if slackBot.channel_id == 'select tour':
        slackBot.type = payload['actions'][0]['name']
        keyword_addr()
    else:
        extra_api(payload['actions'][0]['value'])


# 키워드 추출(검색어 추출)
def extra_keyword(text):
    words = konlpy.tag.Mecab().pos(text)

    grammar = """
    NP: {<N.*>*<Suffix>?}   # Noun phrase
    VP: {<V.*>*}            # Verb phrase
    AP: {<A.*>*}            # Adjective phrase
    """
    parser = nltk.RegexpParser(grammar)
    chunks = parser.parse(words)

    str_location = []
    str_type = []
    for subtree in chunks.subtrees():
        if subtree.label() == 'NP':
            for index, e in enumerate(list(subtree)):
                if str(e[1]) == 'NNP':
                    str_location.append(e[0])
                elif str(e[1]) == 'NNG':
                    str_type.append((e[0]))

    slackBot.location = ''.join(str_location)
    slackBot.type_code = ''.join(str_type)


# 주소 정보 타입별로 출력
def extra_api(location):
    code_dict = type_info(slackBot.type_code)
    if slackBot.type == 'location':
        code_dict['lng'] = location['frontLon']
        code_dict['lat'] = location['frontLat']
        location_base_api(code_dict)
    else:
        area_dict = area_info(location)
        code_dict.update(area_dict)
        type_base_api(code_dict)


# 키워드로 주소 정보 확인
def keyword_addr():
    call_api = callAPI()
    call_api.url = 'http://apis.skplanetx.com/tmap/pois'
    call_api.params = {
        'appKey': '6c8d5711-b0e5-30b1-8aa3-1cdfd328db49',
        'version': '1',
        'format': 'json',
        'searchKeyword': slackBot.location,
        'page': '1',
        'count': '5',
    }

    result = call_api.get_send_api()
    error_code = result['error']['id'] if 'error' in result else ''

    if error_code == '':
        total_count = int(result['searchPoiInfo']['totalCount'])
        # 주소 정보가 많을 경우 선택
        if total_count > 1:
            btn_message = [
                {
                    "text": "검색하신 장소를 선택해주세요.",
                    "fallback": "",
                    "callback_id": "select addr info",
                    "color": "#3AA3E3",
                    "attachment_type": "default",
                    'actions': []
                }
            ]

            str_addr = ""
            for addr in result['searchPoiInfo']['pois']['poi']:
                if str_addr != addr['upperAddrName'] + " " + addr['middleAddrName'] + " " + addr['lowerAddrName']:
                    coordinate = {
                                    "name": addr['id'],
                                    "text": addr['upperAddrName'] + " " + addr['middleAddrName'] + " " + addr['lowerAddrName'],
                                    "type": "button",
                                    "value": addr
                                }
                    str_addr = addr['upperAddrName'] + " " + addr['middleAddrName'] + " " + addr['lowerAddrName']
                    btn_message.append(coordinate)
            slackBot.message = btn_message
        elif total_count == 1:
            extra_api(result['searchPoiInfo']['pois']['poi'][0])
        else:
            slackBot.message = [
                {
                    'title': '찾으시는 장소가 ' + slackBot.location + '이 맞나요?',
                    'text': '상세 장소 정보를 찾지 못했어요. 다시 자세하게 알려주시겠어요? '
                }
            ]
    else:
        slackBot.message = [
            {
                'title': slackBot.location + ' 어디 ' + slackBot.type_code + '를 원하시나요?',
                'text': slackBot.location + '의 자세한 장소를 알려주세요.'
            }
        ]
    response = slackBot.send_message()

    return Response(), response


# 주소 정보 가져오기
def area_info(addr):
    call_api = callAPI()
    call_api.url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaCode?ServiceKey=0tGMz" \
                   "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "
    call_api.params = {
        'numOfRows': 40,
        'arrange': 'A',
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        '_type': 'json'
    }

    addr_result = call_api.get_send_api()
    code_arr = addr_result['response']['body']['items']['item']

    area_code = {}
    for code in code_arr:
        if code['name'] in addr['upperAddrName']:
            area_code['area_code'] = code['code']

    if slackBot.location not in addr['upperAddrName']:
        call_api.url = 'http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaCode?ServiceKey=0tGMz%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D'
        call_api.params = {
            'MobileOS': 'ETC',
            'MobileApp': 'romiBot',
            'numOfRows': 100,
            '_type': 'json',
            'areaCode': area_code['area_code']
        }
        addr2_result = call_api.get_send_api()
        code2_arr = addr2_result['response']['body']['items']['item']

        for code in code2_arr:
            if code['name'] in addr['middleAddrName']:
                area_code['sigungu_code'] = code['code']

    print(" \n 3. type base addr info :", area_code)

    return area_code


# 타입 정보 가져오기
def type_info(type_str):
    call_api = callAPI()
    call_api.url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/searchKeyword?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "
    call_api.params = {
        'numOfRows' : 1,
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        'keyword': type_str,
        'arrange' : 'B',
        '_type': 'json'
    }

    result= call_api.get_send_api()

    type = {}
    if result:
        type_result = result['response']['body']['items']['item']

        type['type'] = type_result['contenttypeid'] if 'contenttypeid' in type_result else ''
        type['cat1'] = type_result['cat1'] if 'cat1' in type_result else ''
        type['cat2'] = type_result['cat2'] if 'cat2' in type_result else ''
        type['cat3'] = type_result['cat3'] if 'cat3' in type_result else ''

    return type


# location base api 호출
def location_base_api(code_dict):
    call_api = callAPI()
    call_api.url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/locationBasedList?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "
    call_api.params = {
        'numOfRows': 10,
        'pageNo' : 1,
        'arrange': 'B',
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        'contentTypeId' : code_dict['type'],
        'mapX' : code_dict['lng'] if 'lng' in code_dict else '',
        'mapY' : code_dict['lat'] if 'lat' in code_dict else '',
        'radius': 2000,
        '_type': 'json'
    }

    result = call_api.get_send_api()

    if result:
        result.update(code_dict)

        return parsing_api(result, "location")

    return {}


# type base api 호출
def type_base_api(code_dict):
    call_api = callAPI()
    call_api.url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaBasedList?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "
    call_api.params = {
        'numOfRows': 1,
        'arrange': 'A',
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        'contentTypeId': code_dict['type'],
        'cat1': code_dict['cat1'],
        'cat2': code_dict['cat2'],
        'cat3': code_dict['cat3'],
        'areaCode': code_dict['area_code'],
        'sigunguCode': code_dict['sigungu_code'] if 'sigungu_code' in code_dict else '',
        '_type': 'json'
    }

    result = call_api.get_send_api()

    if result:
        result.update(code_dict)

        return parsing_api(result, "type")

    return {}


# api 결과 파싱
def parsing_api(api_info, type):
    result_code = api_info['response']['header']['resultCode']

    attachments = {}
    items = api_info['response']['body']['items']
    if items and result_code == "0000":
        item_arr = items['item']
        if type == "location":
            for item in item_arr:
                if item['cat1'] == api_info['cat1']:#and item['cat2'] == api_info['cat2'] and item['cat3'] == api_info['cat3']:

                    mapx = str(item['mapx']) if 'mapx' in item.keys() else ''
                    mapy = str(item['mapy']) if 'mapy' in item.keys() else ''

                    attachments['title'] = " ' " + item['title'] + "' 여기는 어떠신가요??"
                    attachments['title_link'] = "https://www.google.co.kr/maps/search/"+ item['title'] +"/@" + mapy + "," + mapx + ",18z?hl=ko"
                    attachments['text'] = item['title'] if 'title' in item.keys() else '여기요!'
                    attachments['thumb_url'] = item['firstimage'] if 'firstimage' in item.keys() else ''
        else:
            attachments['title'] = " ' " + item_arr['title'] + "' 여기는 어떠신가요??"
            attachments['title_link'] = "https://www.google.co.kr/maps/search/" + item_arr['title'] + ",18z?hl=ko"
            attachments['text'] = item_arr['title'] if 'title' in item_arr.keys() else '여기요!'
            attachments['thumb_url'] = item_arr['firstimage'] if 'firstimage' in item_arr.keys() else ''
    else:
        attachments['title'] = "정보를 찾지못했어요ㅠㅠ"
        attachments['title_link'] = "http://www.naver.com"
        attachments['text'] = "관리자한테 문의해주세요."

    return {'documents' : attachments}


@app.route('/', methods=['GET'])
def main():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)