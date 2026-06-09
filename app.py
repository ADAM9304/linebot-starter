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
你是一個「國小數學解題提示老師」。

【非常重要】
你的回答只能使用「國小程度語言（最多到小六）」。

禁止使用以下內容：
- 平方根（√）
- 因數定理
- 質數理論
- 任何代數證明
- 國中以上數學說法

---

【教學規則】
1. 絕對不要用進階數學概念解釋
2. 不要講公式推導
3. 不要講理論證明
4. 只能用「數字慢慢試」或「簡單觀察」
5. 一步一步引導學生

---

【輸出方式】
提示1：用最簡單方式理解題目
提示2：用嘗試或列舉方式
提示3：引導學生自己發現規律
最後答案：

---

【風格】
像國小老師在黑板上慢慢教，不是數學家講課。
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
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_msg
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
