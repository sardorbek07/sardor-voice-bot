import os
import json
import base64
import wave
import io
import urllib.request
import urllib.parse
import urllib.error
from http.server import BaseHTTPRequestHandler


TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

GEMINI_MODEL = "gemini-3.1-flash-tts-preview"


SARDOR_VOICE = "Achird"
IFORA_VOICE = "Aoede"


SARDOR_PROMPT = """
You are a 21-year-old Uzbek male.
Sound clearly young, around 20–22 years old.
Use only a young male voice throughout the entire recording.
Never switch to a female voice.

Speak naturally, confidently and conversationally,
like a young professional talking directly to his audience.

Warm, clear and masculine.
Relaxed pacing with natural pauses.

Do not sound like a narrator, announcer, or middle-aged man.
Do not sound artificial or robotic.

Read the provided Uzbek text naturally.
Preserve the meaning and wording of the text.
Do not add, remove, translate, or explain anything.
"""


IFORA_PROMPT = """
You are a 21-year-old Uzbek woman.
Sound clearly young, around 20–22 years old.
Use only a young female voice throughout the entire recording.
Never switch to a male voice.

Speak naturally, confidently and conversationally,
like a young professional talking directly to her audience.

Warm, clear and pleasant.
Fresh and youthful, without sounding childish.
Relaxed pacing with natural pauses.

Do not sound like a narrator, announcer, or mature woman.
Do not sound artificial or robotic.

Read the provided Uzbek text naturally.
Preserve the meaning and wording of the text.
Do not add, remove, translate, or explain anything.
"""


def telegram_api(method, data):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"

    request = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def telegram_answer_callback(callback_id):
    telegram_api(
        "answerCallbackQuery",
        {
            "callback_query_id": callback_id
        }
    )


def telegram_remove_buttons(chat_id, message_id):
    telegram_api(
        "editMessageReplyMarkup",
        {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {
                "inline_keyboard": []
            }
        }
    )


def pcm_to_wav(pcm_data):
    output = io.BytesIO()

    with wave.open(output, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(24000)
        wav_file.writeframes(pcm_data)

    return output.getvalue()


def generate_tts(text, voice, character_prompt):
    full_prompt = f"""
{character_prompt}

TEXT TO READ:
---BEGIN TEXT---
{text}
---END TEXT---
"""

    payload = {
        "model": GEMINI_MODEL,
        "input": full_prompt,
        "response_format": {
            "type": "audio"
        },
        "generation_config": {
            "speech_config": [
                {
                    "voice": voice
                }
            ]
        }
    }

    request = urllib.request.Request(
        "https://generativelanguage.googleapis.com/v1beta/interactions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": GEMINI_API_KEY,
            "Api-Revision": "2026-05-20",
        },
        method="POST",
    )

try:
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))

except urllib.error.HTTPError as error:
    error_body = error.read().decode("utf-8", errors="replace")
    print("GEMINI HTTP ERROR:", error.code)
    print("GEMINI RESPONSE:", error_body)
    raise RuntimeError(
        f"Gemini HTTP {error.code}: {error_body}"
    )

    audio_data = result.get("output_audio", {}).get("data")

    if not audio_data:
        raise RuntimeError(
            f"Gemini did not return audio: {json.dumps(result)[:1000]}"
        )

    pcm_data = base64.b64decode(audio_data)

    return pcm_to_wav(pcm_data)


def send_audio(chat_id, audio_bytes, filename="voice.wav"):
    boundary = "----TelegramBoundary7MA4YWxkTrZu0gW"

    body = bytearray()

    def add_field(name, value):
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        )
        body.extend(str(value).encode())
        body.extend(b"\r\n")

    add_field("chat_id", chat_id)

    body.extend(f"--{boundary}\r\n".encode())
    body.extend(
        f'Content-Disposition: form-data; name="audio"; filename="{filename}"\r\n'.encode()
    )
    body.extend(b"Content-Type: audio/wav\r\n\r\n")
    body.extend(audio_bytes)
    body.extend(b"\r\n")

    body.extend(f"--{boundary}--\r\n".encode())

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendAudio"

    request = urllib.request.Request(
        url,
        data=bytes(body),
        headers={
            "Content-Type": f"multipart/form-data; boundary={boundary}"
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def send_text_with_buttons(chat_id, text):
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
                            "callback_data": "sardor"
                        },
                        {
                            "text": "🎙 Ifora",
                            "callback_data": "ifora"
                        }
                    ]
                ]
            }
        }
    )


class handler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Telegram bot is running.")

    def do_POST(self):
        try:
            content_length = int(
                self.headers.get("Content-Length", 0)
            )

            body = self.rfile.read(content_length)
            update = json.loads(body.decode("utf-8"))

            # -------------------------------------------------
            # USER SENT A TEXT MESSAGE
            # -------------------------------------------------

            message = update.get("message")

            if message:
                chat_id = message["chat"]["id"]
                text = message.get("text", "").strip()

                if text:
                    send_text_with_buttons(chat_id, text)

            # -------------------------------------------------
            # USER PRESSED SARDOR / IFORA
            # -------------------------------------------------

            callback_query = update.get("callback_query")

            if callback_query:
                callback_id = callback_query["id"]

                telegram_answer_callback(callback_id)

                callback_data = callback_query.get("data")
                callback_message = callback_query.get("message", {})

                chat_id = callback_message.get("chat", {}).get("id")
                message_id = callback_message.get("message_id")
                message_text = callback_message.get("text", "")

                if not chat_id or not message_text:
                    raise RuntimeError("Callback message data is missing.")

                # Our bot message format:
                #
                # Siz yubordingiz:
                #
                # original text

                prefix = "Siz yubordingiz:\n\n"

                if message_text.startswith(prefix):
                    original_text = message_text[len(prefix):]
                else:
                    original_text = message_text

                if not original_text.strip():
                    raise RuntimeError("Original text is empty.")

                if callback_data == "sardor":
                    voice = SARDOR_VOICE
                    character_prompt = SARDOR_PROMPT
                    filename = "sardor.wav"

                elif callback_data == "ifora":
                    voice = IFORA_VOICE
                    character_prompt = IFORA_PROMPT
                    filename = "ifora.wav"

                else:
                    raise RuntimeError("Unknown voice selection.")

                # Remove buttons after selection.
                if message_id:
                    try:
                        telegram_remove_buttons(
                            chat_id,
                            message_id
                        )
                    except Exception:
                        pass

                audio = generate_tts(
                    original_text,
                    voice,
                    character_prompt
                )

                send_audio(
                    chat_id,
                    audio,
                    filename
                )

            self.send_response(200)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.end_headers()

            self.wfile.write(
                b'{"ok":true}'
            )

        except Exception as error:
            print("ERROR:", repr(error))

            self.send_response(500)
            self.send_header(
                "Content-Type",
                "application/json"
            )
            self.end_headers()

            self.wfile.write(
                json.dumps(
                    {
                        "ok": False,
                        "error": str(error)
                    }
                ).encode("utf-8")
            )
