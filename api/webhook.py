import os
import json
import urllib.request


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


def handler(request):
    if request.method != "POST":
        return {
            "statusCode": 200,
            "body": "OK",
        }

    update = request.json

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

    return {
        "statusCode": 200,
        "body": "OK",
    }
