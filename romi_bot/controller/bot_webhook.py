# -*- coding: utf-8 -*-
import konlpy
import nltk
from flask import request, Response, json
from romi_bot.model.chatbot import slackBot
from romi_bot.model.callAPI import callAPI


# slackBot 생성
slack_bot = slackBot()


# local test url
def slack_test():
    slack_bot.text = request.form.get('text')
    slack_bot.channel_id = request.form.get('channel_id')
    slack_bot.type = request.form.get('type_code')
    extra_keyword(slack_bot.text)
    keyword_addr()

    response = slack_bot.send_message()
    print(response)

    return Response(), response


def slack_events():
    payload = request.get_data()
    data = json.loads(payload)
    result = data['challenge'] if 'challenge' in data else ''

    return Response(result, mimetype='application/x-www-form-urlencoded')


def slack_oauth():
    slack_bot.code = request.args.get('code')
    slack_bot.oauth()

    return Response(), 200


# button select message (search type select)
def slack_btn_select():
    slack_bot.text = request.form.get('text')
    slack_bot.channel_id = request.form.get('channel_id')

    # 장소, 타입 정보 있는 지 확인 후 답변
    if slack_bot.text != "":
        # 사용자 키워드 추출하여 location, type_code에 저장
        extra_keyword(slack_bot.text)

        if slack_bot.location == "":
            slack_bot.message = [
                {
                    'title': '장소를 알려주세요.',
                    'text': '장소정보를 찾지 못했어요. 다시 상세하게 알려주세요.'
                }
            ]
        elif slack_bot.type_code == "":
            slack_bot.message = [
                {
                    'title': '어떤 정보를 알려드릴까요?',
                    'text': '원하시는 정보가 무엇인지 모르겠어요. 다시 상세하게 알려주세요.'
                }
            ]
        else:
            slack_bot.message = [
                {
                    "text": slack_bot.location + "에서의 " + slack_bot.type_code + " 찾고 계신가요??",
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

        slack_bot.send_message()

    return Response()


# user button click actions
def slack_actions():
    payload = json.loads(request.form['payload'])
    callback_id = payload['callback_id']

    # callback_id select tour : search type click actions
    if callback_id == 'select tour':
        slack_bot.type = payload['actions'][0]['name']
        keyword_addr()
    else:
        # location info click actions
        location = (payload['actions'][0]['value']).split("/")
        if slack_bot.type == "location":
            values = { 'frontLon' : location[0],
                       'frontLat' : location[1],
                     }
        else:
            values = { 'upperAddrName' : location[0],
                       'middleAddrName' : location[1],
                     }
        # search type result request
        extra_api(values)

    return Response()


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

    slack_bot.location = ''.join(str_location)
    slack_bot.type_code = ''.join(str_type)


# 주소 정보 타입별로 출력
def extra_api(location):
    code_dict = type_info(slack_bot.type_code)
    if slack_bot.type == 'location':
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
        'searchKeyword': slack_bot.location,
        'page': '1',
        'count': '5',
        'resCoordType':'WGS84GEO',
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
                    # search type - location info save
                    if slack_bot.type == "location":
                        value = addr['frontLon'] + "/" + addr['frontLat']
                    else:
                        value = addr['upperAddrName'] + "/" + addr['middleAddrName']

                    coordinate = {
                                    "name": addr['id'],
                                    "text": addr['upperAddrName'] + " " + addr['middleAddrName'] + " " + addr['lowerAddrName'],
                                    "type": "button",
                                    "value": value
                                }
                    str_addr = addr['upperAddrName'] + " " + addr['middleAddrName'] + " " + addr['lowerAddrName']
                    btn_message[0]['actions'].append(coordinate)
            slack_bot.message = btn_message

        elif total_count == 1:
            extra_api(result['searchPoiInfo']['pois']['poi'][0])
        else:
            slack_bot.message = [
                {
                    'title': '찾으시는 장소가 ' + slack_bot.location + '이 맞나요?',
                    'text': '상세 장소 정보를 찾지 못했어요. 다시 자세하게 알려주시겠어요? '
                }
            ]
    else:
        slack_bot.message = [
            {
                'title': slack_bot.location + ' 어디 ' + slack_bot.type_code + '를 원하시나요?',
                'text': slack_bot.location + '의 자세한 장소를 알려주세요.'
            }
        ]
    response = slack_bot.send_message()

    print("\n keyword arr send message : ")
    print(slack_bot.message)

    return Response(), response


# 주소 정보 가져오기
def area_info(addr):
    call_api = callAPI()
    call_api.url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/areaCode?ServiceKey=0tGMz%2FY9N" \
                   "JAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D"

    call_api.params = {
        'numOfRows': 40,
        'arrange': 'A',
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        '_type': 'json'
    }
    print("area info : " , addr)
    addr_result = call_api.get_send_api()
    code_arr = addr_result['response']['body']['items']['item']

    area_code = {}
    for code in code_arr:
        if code['name'] in addr['upperAddrName']:
            area_code['area_code'] = code['code']

    if slack_bot.location not in addr['upperAddrName']:
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

    result = call_api.get_send_api()

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
        slack_bot.message = parsing_api(result, "location")
    else:
        slack_bot.message = [
            {
                'title': slack_bot.location + ' 어디 ' + slack_bot.type_code + '를 원하시나요?',
                'text': slack_bot.location + '의 자세한 장소를 알려주세요.'
            }
        ]

    response = slack_bot.send_message()

    print("\n location base send message : ")
    print(slack_bot.message)
    return Response(), response


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
        slack_bot.message = parsing_api(result, "type")
    else:
        slack_bot.message = [
            {
                'title': slack_bot.location + ' 어디 ' + slack_bot.type_code + '를 원하시나요?',
                'text': slack_bot.location + '의 자세한 장소를 알려주세요.'
            }
        ]
    response = slack_bot.send_message()

    print("\n type base send message : ")
    print(slack_bot.message)
    return Response(), response


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

                    message = [
                        {
                            "title": "'" + item['title'] + "' 여기는 어떠신가요?",
                            "title_link": "http://ec2-13-125-14-134.ap-northeast-2.compute.amazonaws.com:8000/tour/"+ str(item['contenttypeid']) + "/detail/" + str(item['contentid']),
                            "text": item['title'] + "은 " + item['addr1'] + " " + item['addr2'] + " 위치에 있습니다.",
                            "attachment_type": "default",
                            "thumb_url" : item['firstimage'] if 'firstimage' in item.keys() else ''
                        }
                    ]
        else:
            message = [
                {
                    "title": "'" + item_arr['title'] + "' 여기는 어떠신가요?",
                    "title_link": "http://ec2-13-125-14-134.ap-northeast-2.compute.amazonaws.com:8000/tour/"+ str(item_arr['contenttypeid']) + "/detail/" + str(item_arr['contentid']),
                    "text": item_arr['title'] + "은 " + item_arr['addr1'] + " " + item_arr['addr2'] + " 위치에 있습니다.",
                    "attachment_type": "default",
                    "thumb_url": item_arr['firstimage'] if 'firstimage' in item_arr.keys() else ''
                }
            ]
    else:
        message = [
            {
                "title": "정보를 찾지 못하였습니다. ",
                "title_link": "http://ec2-13-125-14-134.ap-northeast-2.compute.amazonaws.com:8000/"
                              "slack/error?location="+ slack_bot.location +"&type=" + slack_bot.type,
                "text": " 제목을 클릭하여 관리자에게 못찾은 정보를 보내주세요.",
            }
        ]

    return message