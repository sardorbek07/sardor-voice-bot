import os
import json
import urllib.request
from http.server import BaseHTTPRequestHandler


TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]


def telegram_api(method, data):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request) as response:
        return json.loads(response.read().decode("utf-8"))


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Telegram bot is running.")

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            update = json.loads(body.decode("utf-8"))
        except Exception:
            self.send_response(400)
            self.end_headers()
            return

        message = update.get("message")

        if message:
            chat_id = message["chat"]["id"]
            text = message.get("text", "")

            if text:
                telegram_api(
                    "sendMessage",
                    {
                        "chat_id": chat_id,
                        "text": f"Siz yubordingiz:\n\n{text}",
                        "reply_markup": {
                            "inline_keyboard": [
                                [
                                    {
                                        "text": "🎙 Sardor",
                                        "callback_data": "sardor",
                                    },
                                    {
                                        "text": "🎙 Ifora",
                                        "callback_data": "ifora",
                                    },
                                ]
                            ]
                        },
                    },
                )

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"ok":true}')
