# -*- coding: utf-8 -*-
from romi_bot.model.callAPI import callAPI
from flask import render_template, json
from romi_bot.controller.bot_webhook import slack_bot



def web_detail(type_id, content_id):
    call_api = callAPI()
    call_api.url = "http://api.visitkorea.or.kr/openapi/service/rest/KorService/detailCommon?ServiceKey=0tGMz%2FY9N" \
                   "JAmuX2b5XBvz2jtdGMVxjmqpEk6dB%2FoX65tTQruqoO6A3Mpk5en%2BbqSaQCIBLWqiXU8vMVDNTdhiA%3D%3D"

    call_api.params = {
        'numOfRows': 10,
        'pageNo': 1,
        'MobileApp': 'romiBot',
        'MobileOS': 'ETC',
        'contentId': content_id,
        'contentTypeId': type_id,
        '_type': 'json',
        'defaultYN': 'Y',
        'firstImageYN': 'Y',
        'areacodeYN': 'Y',
        'catcodeYN': 'Y',
        'addrinfoYN': 'Y',
        'mapinfoYN': 'Y',
        'overviewYN': 'Y',
    }

    result = call_api.get_send_api()
    result = result['response']['body']['items']['item']

    return render_template('detail.html', result=result, name=slack_bot.user_name)