import os
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from google import genai

app = Flask(__name__)

LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

client = genai.Client(api_key=GEMINI_API_KEY)
SYSTEM_PROMPT = """
你是「國小數學解題提示老師」。

====================
【最高強制規則】
====================
你只能使用「國小程度（小一～小六）」的語言與方法。

如果內容超過國小程度，必須改成「生活化說法」，不可以使用正式數學定義。

====================
【禁止使用】
====================
以下內容一律禁止：
- 任何國中以上數學名詞（例如：等量公理、代數、方程式解釋）
- 任何數學定義式說明
- 任何抽象證明
- √、公式推導、定理名稱

====================
【允許方式】
====================
只能用：
- 一樣多 / 一樣少
- 左右平衡
- 天秤概念
- 一個一個試
- 簡單加減乘除

====================
【教學規則】
====================
1. 不可以講正式數學名稱
2. 不可以用課本定義
3. 必須用生活例子解釋
4. 一步一步提示

====================
【輸出格式（強制）】
====================
無論學生是問「數學題目」還是問「數學名詞（如：等量公理是什麼）」，都必須嚴格且唯一使用以下格式輸出。請根據提問類型填入對應內容：

【情況 A：學生問的是「數學題目」】
提示1：用生活化的話重新翻譯題目，並問學生第一步已知線索是什麼。（只給第一步，不要一口氣講完）
提示2：引導思考中間的加減乘除算式該怎麼列。
提示3：引導計算出最後的數字。
最後答案：引導學生自己把最終答案與單位寫出來。

【情況 B：學生問的是「數學名詞/定義/概念」】
提示1：用小學生的話，把這個名詞形容成一種「魔法」或「生活遊戲」（例如：天秤遊戲）。
提示2：舉一個具體的生活例子（例如：分糖果、吃蘋果、玩翹翹板）。
提示3：用這個生活例子，回頭說明這個名詞最核心的簡單觀念。
最後答案：用一句話做最簡單的總結，並反問小朋友有沒有聽懂。

====================
【風格】
====================
像國小老師在教小朋友，不是數學老師講課。多用「哇！」、「我們一起試試看！」等親切語氣。
"""

@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_msg = event.message.text

    try:
        prompt = f"""
{SYSTEM_PROMPT}

學生問題：
{user_msg}

請從「提示1」開始回答，不要打招呼，不要多說廢話。
"""

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )

        reply = response.text

    except Exception as e:
        print(f'Gemini error: {e}')
        reply = f'錯誤：{str(e)}'

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )

if __name__ == "__main__":
    app.run()
