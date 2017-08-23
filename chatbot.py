# -*- coding: utf-8 -*-
import os

from flask import Flask, request, Response
from slackclient import SlackClient
import requests
import konlpy
import nltk
from flask.ext.restful import Api, Resource, reqparse, fields, marshal

app = Flask(__name__)

SLACK_WEBHOOK_SECRET = os.environ.get('SLACK_WEBHOOK_SECRET')
SLACK_TOKEN = os.environ.get('SLACK_TOKEN', None)
slack_client = SlackClient(SLACK_TOKEN)
FORECAST_TOKEN = os.environ.get('FORECAST_TOKEN')
tour_fields = {
    'title': fields.String,
    'title_link': fields.String,
    'text': fields.String,
    'thumb_url': fields.String,
}


class TourApi():
    def __init__(self, response):
        self.res = reqparse.RequestParser()

        self.reqparse.add_argument('title', type=str, required=True,
                                   help='정보를 찾지 못했습니다',
                                   location='json')
        self.reqparse.add_argument('title_link', type=str, default="http://naver.com",
                                   location='json')
        self.reqparse.add_argument('text', type=str, default="관리자한테 알려주세요.",
                                   location='json')
        self.reqparse.add_argument('thumb_url', type=str, default="",
                                   location='json')
        super(TourApi, self).__init__()

    def get(self):
        return {'documents': [marshal(tour_fields)]}

def send_message(channel_id, message):
    slack_client.api_call(
        "chat.postMessage",
        channel=channel_id,
        attachments=message,
        username='RomiRomi',
        icon_emoji=':monkey_face:'
    )


@app.route('/webhook', methods=['POST'])
def inbound():
    text = request.form.get('text')
    channel_id = request.form.get('channel_id')

    keywords = extra_keyword(text)
    # tour_info = tour_api(keywords)
    message = tour_api(keywords)
    # message = inbound_message(request, tour_info)

    try:
        send_message(channel_id, message)
    except BaseException as ex:
        print("send_message (error) : ", ex)

    return Response(), 200


# 메세지 전달
def inbound_message(request, tour_info):
    message = tour_info

    return message


# 키워드 추출(검색어 추출)
def extra_keyword(text):

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


# 키워드 정보 받아서 api 정보 전달
def extra_api(keywords):
    api_info = []

    # 첫번째 키워드가 지명 두번째가 콘텐츠 타입이라고 가정
    addr = keywords[0]
    type = keywords[1]


    code_dict = addr_info(addr)
    # code_dict['type'] = type_info(type)
    type = type_info(type)
    code_dict.update(type)

    return code_dict


# 위치 정보 가져오기
def addr_info(addr):

    url = 'http://www.juso.go.kr/addrlink/addrLinkApi.do'
    params = {
        'confmKey' : 'U01TX0FVVEgyMDE3MDgwOTE5MDgxNjIzNzY5',
        'currentPage' : 1,
        'countPerPage' : 1,
        'keyword' : addr,
        'resultType' : 'json',
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
        addr_response = requests.get('http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaCode?ServiceKey=0tGMz%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D&MobileOS=ETC&MobileApp=romiBot&numOfRows=40&_type=json')
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

    return area_code


# 타입 정보 가져오기
def type_info(type_str):
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

    return type


# 정보 가져오기
def tour_api(keywords):
    api_info = extra_api(keywords)
    send_info = send_api(api_info)

    return send_api


# api 호출
def send_api(code_dict):
    url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaBasedList?ServiceKey=0tGMz" \
          "%2FY9NJAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D& "

    # print("\n api info : ", code_dict, "\n")

    params = {
        'numOfRows': 1,
        'arrange': 'A',
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        'contentTypeId' : code_dict['type'],
        'cat1' : code_dict['cat1'],
        'cat2' : code_dict['cat2'],
        'cat3' : code_dict['cat3'],
        'areaCode': code_dict['area_code'],
        'sigunguCode' : code_dict['sigungu_code'] if 'sigungu_code' in code_dict else '',
        '_type': 'json'
    }

    try:
        response = requests.get(url, params=params)
    except BaseException as ex:
        print("send api error : ", ex)


    result = response.json()
    parsing_result = parsing_api(result)

    return parsing_result


# api 결과 파싱
def parsing_api(api_info):
    result_code = api_info['response']['header']['resultCode']
    print("\n api result : " , api_info, "\n")

    attachments = {}

    items = api_info['response']['body']['items']

    # print("\n api result items : ",  items, "\n")

    if items and result_code == "0000":
        item = items['item']

        mapx = str(item['mapx']) if 'mapx' in item.keys() else ''
        mapy = str(item['mapy']) if 'mapy' in item.keys() else ''

        attachments['title'] = " ' " + item['title'] + "' 여기는 어떠신가요??"
        attachments['title_link'] = "https://www.google.co.kr/search/"+ item['title'] +"/@" + mapy + "," + mapx + ",18z?hl=ko"
        attachments['text'] = item['title'] if 'title' in item.keys() else '여기요!'
        attachments['thumb_url'] = item['firstimage'] if 'firstimage' in item.keys() else ''
    else:
        attachments['title'] = "정보를 찾지못했어요ㅠㅠ"
        attachments['title_link'] = "http://www.naver.com"
        attachments['text'] = "관리자한테 문의해주세요."

    print("\n send message : ", {'documents' : attachments} , "\n")
    return {'documents' : attachments}


@app.route('/', methods=['GET'])
def test():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)
