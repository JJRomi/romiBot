# -*- coding: utf-8 -*-
from slackclient import SlackClient
import settings

class slackBot:
    def __init__(self):
        self.text = ""
        self.channel_id = ""
        self.message = {}
        self.user_name = "Romi"
        self.user_emoji = ":monkey_face:"
        self.verification = settings.SLACK_VERIFICATION_TOKEN
        self.slack_client = SlackClient(settings.SLACK_BOT_UESR_TOKEN)
        self.code = "" # Auth Code
        self.type = "" # SearchType
        self.location = "" # location info
        self.type_code = "" # type info

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
            client_id=settings.SLACK_CLIENT_ID,
            client_secret=settings.SLACK_CLIENT_SECRET,
            code=self.code
        )