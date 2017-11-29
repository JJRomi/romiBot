# -*- coding: utf-8 -*-
from flask import Flask,render_template, Response
from romi_bot.controller.bot_webhook import *
from romi_bot.controller.bot_webdetail import *
from romi_bot.controller import bot_webhook

app = Flask(__name__)


def not_found(error):
    return render_template('404.html'), 404


def server_error(error):
    err_msg = str(error)
    return render_template('500.html', err_msg=err_msg), 500


# local test url
@app.route('/test', methods=['POST'])
def test():
    return slack_test()


@app.route('/slack/events', methods=['POST'])
def events():
    return bot_webhook.slack_events()


@app.route('/slack/oauth', methods=['POST'])
def oauth():
    return slack_oauth()


# button select message (search type select)
@app.route('/webhook', methods=['POST'])
def btn_select():
    return slack_btn_select()


# user button click actions
@app.route('/slack/actions', methods=['POST'])
def interactive_callback():
    return slack_actions()


@app.route('/tour/<type_id>/detail/<content_id>', methods=['GET'])
def tour_detail(type_id, content_id):
    return web_detail(type_id, content_id)


@app.route('/', methods=['GET'])
def main():
    return Response('It works!')