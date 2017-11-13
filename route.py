# -*- coding: utf-8 -*-
import chatbot
from flask import Flask, Response


app = Flask(__name__)


# local test url
@app.route('/test', methods=['POST'])
def test():
    chatbot.slack_test()


@app.route('/slack/events', methods=['POST'])
def events():
    chatbot.slack_events()


@app.route('/slack/oauth', methods=['POST'])
def oauth():
    chatbot.slack_oauth()


# button select message (search type select)
@app.route('/webhook', methods=['POST'])
def btn_select():
    chatbot.slack_btn_select()


# user button click actions
@app.route('/slack/actions', methods=['POST'])
def interactive_callback():
    chatbot.slack_actions()


@app.route('/tour/<tour_id>/detail')
def web_tour_detail():
    return Response('Detail Page!')


@app.route('/', methods=['GET'])
def main():
    return Response('It works!')


if __name__ == "__main__":
    app.run(debug=True)