import json
from channels.generic.websocket import WebsocketConsumer


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        self.accept()

    def disconnect(self, close_code):
        pass

    def receive(self, thumnail_url):
        text_data_json = json.loads(thumnail_url)
        message = text_data_json['s3_url']

        self.send(text_data=json.dumps({
            's3_url': message
        }))
