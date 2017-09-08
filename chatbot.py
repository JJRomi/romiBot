# -*- coding: utf-8 -*-
import os

from flask import Flask, request, Response, make_response, json
from slackclient import SlackClient
import requests
import konlpy
import nltk
from flask.ext.restful import Api, Resource, reqparse, fields, marshal

app = Flask(__name__)

SLACK_BOT_UESR_TOKEN = os.environ.get('SLACK_BOT_USER_TOKEN')
SLACK_AUTH_TOKEN = os.environ.get('SLACK_AUTH_TOKEN')

SLACK_CLIENT_ID = os.environ.get('SLACK_CLIENT_ID')
SLACK_CLIENT_SECRET =  os.environ.get('SLACK_CLIENT_SECRET')
SLACK_VERIFICATION_TOKEN = os.environ.get('SLACK_VERIFICATION_TOKEN')

slack_client = SlackClient(SLACK_BOT_UESR_TOKEN)

# SLACK_WEBHOOK_SECRET = os.environ.get('SLACK_WEBHOOK_SECRET')
# SLACK_TOKEN = os.environ.get('SLACK_TOKEN', None)
# FORECAST_TOKEN = os.environ.get('FORECAST_TOKEN')


# test url
@app.route('/test', methods=['POST'])
def test():
    text = request.form.get('text')
    channel_id = request.form.get('channel_id')
    type_code = request.form.get('type_code')

    keywords = extra_keyword(text)
    message = tour_api(keywords, type_code)

    try:
        send_message(channel_id, message)
    except BaseException as ex:
        print("send_message (error) : ", ex)

    return Response(), 200



# button select message (type select)
@app.route('/webhook', methods=['POST'])
def btn_select():
    text = request.form.get('text')
    channel_id = request.form.get('channel_id')

    # text로 keyword 추출
    keywords = extra_keyword(text)

    attachments = [
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

    try:
        send_message(channel_id, attachments)
    except BaseException as ex:
        print("send_message (error) : ", ex)

    return Response(), 200


@app.route('/slack/events', methods=['POST'])
def events():
    payload = request.get_data()
    data = json.loads(payload)

    print("\n event data : ", data)

    return Response(data["challenge"], mimetype='application/x-www-form-urlencoded')


@app.route('/slack/oauth', methods=['POST'])
def oauth():
    code = request.args.get('code')
    slack_client.api_call(
        "oauth.access",
        client_id=SLACK_CLIENT_ID,
        client_secret=SLACK_CLIENT_SECRET,
        code=code
    )

    return Response(), 200


def send_message(channel_id, message):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        attachments=message,
        username='RomiRomi',
        icon_emoji=':monkey_face:'
    )


# button actions
@app.route('/slack/actions', methods=['POST'])
def interactive_callback():
    # print("interaction callback")
    payload = json.loads(request.form['payload'])

    channel_id = payload['channel']['id']
    value = payload['actions'][0]['value']
    type = payload['actions'][0]['name']

    keywords = value.split(',')

    message = tour_api(keywords, type)

    try:
        send_message(channel_id, message)
    except BaseException as ex:
        print("send_message (error) : ", ex)

    return Response(), 200


# 키워드 추출(검색어 추출)
def extra_keyword(text):
    print(" \n 1. 키워드 추출 ")
    sentence = text
    words = konlpy.tag.Twitter().pos(sentence)

    grammar = """
    NP: {<N.*>*<Suffix>?}   # Noun phrase
    VP: {<V.*>*}            # Verb phrase
    AP: {<A.*>*}            # Adjective phrase
    """
    parser = nltk.RegexpParser(grammar)
    chunks = parser.parse(words)

    keywords = []
    for subtree in chunks.subtrees():
        if subtree.label() == 'NP':
            # keywords.append(str(e[0]) for e in list(subtree))
            for e in list(subtree):
                keywords.append(e[0])

    return keywords


# 정보 가져오기
def tour_api(keywords, type_code):

    api_info = extra_api(keywords, type_code)

    if type_code == "location":
        send_info = location_base_api(api_info)
    else:
        send_info = type_base_api(api_info)

    return send_info


# 키워드 정보 받아서 api 정보 전달
def extra_api(keywords, type_code):
    print("\n 2. extra api ")
    # print("\n keywords : ", keywords)

    # 첫번째 키워드가 지명 두번째가 콘텐츠 타입이라고 가정
    addr = keywords[0]
    type = keywords[1]

    print(" \n========= type code====", type_code)

    if type_code == "location":
        code_dict = location_info(addr)
    else:
        code_dict = addr_info(addr)

    type = type_info(type)
    code_dict.update(type)

    print("\n 2. extra api result :", code_dict)

    return code_dict


# 위치 정보 가져오기
def location_info(addr):
    print(" \n 3. loaction base info")

    url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {
        'key': 'AIzaSyA_CnvlGifC88wJJBdriNetzsuZY_0CIfI',
        'address': addr,
    }

    try:
        response = requests.get(url, params=params)
    except BaseException as ex:
        print("\n send api error : ", ex, "\n")

    result = response.json()
    status = result['status']

    location = {}
    if status == 'OK':
        location = result['results'][0]['geometry']['location']

    print(" \n 3. loaction base info result :", location)

    return location


# 주소 정보 가져오기
def addr_info(addr):
    print(" \n 3. type base addr info")

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
    print("\n 4. type info ")
    url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/searchKeyword?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "

    params = {
        'numOfRows' : 1,
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        'keyword': type_str,
        'arrange' : 'B',
        '_type': 'json'
    }

    try:
        response = requests.get(url, params=params)
    except BaseException as ex:
        print("send api error : ", ex)


    result = response.json()
    type_result = result['response']['body']['items']['item']
    print("\n type_code result : ", result , "\n")

    type = {}
    type['type'] = type_result['contenttypeid'] if 'contenttypeid' in type_result else ''
    type['cat1'] = type_result['cat1'] if 'cat1' in type_result else ''
    type['cat2'] = type_result['cat2'] if 'cat2' in type_result else ''
    type['cat3'] = type_result['cat3'] if 'cat3' in type_result else ''

    print("\n 4. type info result : ", type)

    return type


# location base api 호출
def location_base_api(code_dict):

    print(" \n 5. loaction base api")

    url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/locationBasedList?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "

    # print("\n api info : ", code_dict, "\n")

    params = {
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

    try:
        response = requests.get(url, params=params)
    except BaseException as ex:
        print("send api error : ", ex)


    result = response.json()
    result.update(code_dict)

    print("\n 5. location base api result : ", result)
    parsing_result = parsing_api(result, "location")


    return parsing_result


# type base api 호출
def type_base_api(code_dict):
    print("\n 5. type base api ")

    url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaBasedList?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "

    # print("\n api info : ", code_dict, "\n")

    params = {
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

    try:
        response = requests.get(url, params=params)
    except BaseException as ex:
        print("send api error : ", ex)

    result = response.json()
    result.update(code_dict)

    print("\n 5. type base api result : ", result)

    parsing_result = parsing_api(result, "type")

    return parsing_result


# api 결과 파싱
def parsing_api(api_info, type):
    print(" \n 6. api 결과 파싱")
    result_code = api_info['response']['header']['resultCode']

    print("\n last api info : " , api_info, "\n")

    attachments = {}
    items = api_info['response']['body']['items']

    print("\n last api result items : ",  items, "\n")

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

    # print("\n send message : ", {'documents' : attachments} , "\n")

    return {'documents' : attachments}


@app.route('/', methods=['GET'])
def main():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)