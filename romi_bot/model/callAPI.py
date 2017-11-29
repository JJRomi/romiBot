# -*- coding: utf-8 -*-
import requests, json, xmltodict


class callAPI:
    def __init__(self):
        self.url = ""
        self.params = ""

    def get_send_api(self):
        try:
            response = requests.get(self.url, params=self.params)
            print("*****")
            print(response.text)
            result = response.json()
        except Exception as ex:
            print("\n send api error : ", ex, "\n")

        return result


    def get_xml_api(self):
        try:
            response = requests.get(self.url, params=self.params)
            result = json.dumps(xmltodict.parse(response.text), indent=4)
        except Exception as ex:
            print("\n xml api error : ", ex, "\n")

        return result