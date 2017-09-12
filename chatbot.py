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
        self.type = "location"

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

    def send_api(self):
        try:
            response = requests.get(self.url, params=self.params)
        except BaseException as ex:
            print("\n send api error : ", ex, "\n")

        return response


# local test url
@app.route('/test', methods=['POST'])
def test():
    slack_bot = slackBot()
    slack_bot.text = request.form.get('text')
    slack_bot.channel_id = request.form.get('channel_id')
    slack_bot.type = request.form.get('type')

    keywords = extra_keyword(slack_bot.text)
    slack_bot.message = tour_api(keywords)

    response = slack_bot.send_message()

    return Response(), response


# button select message (type select)
@app.route('/webhook', methods=['POST'])
def btn_select():
    slack_bot = slackBot()
    slack_bot.text = request.form.get('text')
    slack_bot.channel_id = request.form.get('channel_id')

    # text로 keyword 추출
    keywords = extra_keyword(slack_bot.text)
    slack_bot.message = [
        {
            "text": keywords[0] + keywords[1] + " 찾고 계신가요??",
            "fallback": "",
            "callback_id": "select tour",
            "color": "#3AA3E3",
            "attachment_type": "default",
            'actions': [
                {
                    "name": "location",
                    "text": "위치 중심 검색",
                    "type": "button",
                    "value": keywords[0] + "," + keywords[1]
                },
                {
                    "name": "type",
                    "text": "타입 중심 검색",
                    "type": "button",
                    "value": keywords[0] + "," + keywords[1]
                },
            ]

        }
    ]

    response = slack_bot.send_message()

    return Response(), response


@app.route('/slack/events', methods=['POST'])
def events():
    payload = request.get_data()
    data = json.loads(payload)

    return Response(data["challenge"], mimetype='application/x-www-form-urlencoded')


@app.route('/slack/oauth', methods=['POST'])
def oauth():
    slack_bot = slackBot
    slack_bot.code = request.args.get('code')
    slack_bot.oauth()

    return Response(), 200


# button actions
@app.route('/slack/actions', methods=['POST'])
def interactive_callback():
    slack_bot = slackBot()

    payload = json.loads(request.form['payload'])

    slack_bot.channel_id = payload['channel']['id']
    value = payload['actions'][0]['value']
    slack_bot.type = payload['actions'][0]['name']

    keywords = value.split(',')
    slack_bot.message = tour_api(keywords)

    response = slack_bot.send_message()

    return Response(), response


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

    keywords = {}
    for subtree in chunks.subtrees():
        if subtree.label() == 'NP':
            # keywords.append(str(e[0]) for e in list(subtree))
            for index,e in enumerate(list(subtree)):
                if str(e[1]) == 'NNP':
                    keywords['location'] = e[0]
                elif str(e[1]) == 'NNG':
                    keywords['type'] = e[0]
                else:
                    keywords[index] = e[0]

    return keywords


# 정보 가져오기
def tour_api(keywords):
    slack_bot = slackBot()
    api_info = extra_api(keywords)

    if slack_bot.type == "location":
        send_info = location_base_api(api_info)
    else:
        send_info = type_base_api(api_info)

    return send_info


# 키워드 정보 받아서 api 정보 전달
def extra_api(keywords):
    slack_bot = slackBot()

    # TODO : 키워드에서 장소정보와 타입정보가 없을 경우 다시 묻는 거 필요함
    # TODO -> 기존에 말했던 장소와 타입을 기억하기 위해서 global variale에 저장

    addr = keywords['location'] if 'location' in keywords else '상암동'
    type = keywords['type'] if 'type' in keywords else '카페'

    if slack_bot.type == "location":
        code_dict = location_info(addr)
    else:
        code_dict = addr_info(addr)

    type = type_info(type)
    code_dict.update(type)

    return code_dict


# 위치 정보 가져오기
def location_info(addr):
    call_api = callAPI()
    call_api.url = "https://maps.googleapis.com/maps/api/geocode/json"
    call_api.params = {
        'key': 'AIzaSyA_CnvlGifC88wJJBdriNetzsuZY_0CIfI',
        'address': addr,
    }

    response = call_api.send_api()

    location = {}
    if response:
        result = response.json()
        status = result['status']
        if status == 'OK':
            location = result['results'][0]['geometry']['location']

    return location


# 주소 정보 가져오기
def addr_info(addr):
    url = 'http://www.juso.go.kr/addrlink/addrLinkApi.do'
    params = {
        'confmKey': 'U01TX0FVVEgyMDE3MDgwOTE5MDgxNjIzNzY5',
        'currentPage': 1,
        'countPerPage': 1,
        'keyword': addr,
        'resultType': 'json',
    }

    try:
        response = requests.get(url, params=params)
    except BaseException as ex:
        print("\n send api error : ", ex, "\n")

    result = response.json()

    area_code = {}
    error_code = result['results']['common']['errorCode']

    if error_code == 'E0006':
        area_name = addr
        area_name2 = ''
    elif error_code == '0':
        area_arr = result['results']['juso'][0]
        area_name = area_arr['siNm']
        area_name2 = area_arr['sggNm']

    try:
        addr_response = requests.get(
            'http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaCode?ServiceKey=0tGMz%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D&MobileOS=ETC&MobileApp=romiBot&numOfRows=40&_type=json')
    except BaseException as ex:
        print("\n addr code api error : ", ex, "\n")

    addr_result = addr_response.json()
    code_arr = addr_result['response']['body']['items']['item']

    for code in code_arr:
        if code['name'] in area_name:
            area_code['area_code'] = code['code']

    if area_name2:
        url = 'http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaCode?ServiceKey=0tGMz%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D'
        params = {
            'MobileOS': 'ETC',
            'MobileApp': 'romiBot',
            'numOfRows': 100,
            '_type': 'json',
            'areaCode': area_code['area_code']
        }

        try:
            addr2_response = requests.get(url, params=params)
        except BaseException as ex:
            print("\n addr code2 api error : ", ex, "\n")

        addr2_result = addr2_response.json()
        code2_arr = addr2_result['response']['body']['items']['item']

        for code in code2_arr:
            if code['name'] in area_name2:
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

    response = call_api.send_api()

    type = {}
    if response:
        result = response.json()
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

    response = call_api.send_api()

    if response:
        result = response.json()
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

    response = call_api.send_api()

    if response:
        result = response.json()
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
                # if item['cat1'] == api_info
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