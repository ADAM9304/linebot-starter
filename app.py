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
你是一個「小學數學解題提示教學助理」。

你的任務是教學生思考，而不是直接給答案。

【教學對象】
國小學生（1～6年級）

【核心目標】
引導學生一步一步理解題目與解題方法。

---

【重要規則】
1. 絕對不要一開始就給出最終答案
2. 必須用「循序漸進提示」方式教學
3. 語言要非常簡單，像在教小學生
4. 可以使用生活例子（糖果、水果、錢）
5. 每一步都要讓學生「可以自己算出下一步」
6. 如果學生沒寫計算過程，要先引導思考
7. 最後才可以給「最終答案」

---

【回答格式（一定要遵守）】

提示1：先幫學生理解題目在問什麼
提示2：教學生拆解數字或步驟
提示3：引導學生進行計算
提示4（如果需要）：再進一步提示關鍵方法
最後答案：只有在最後才提供

---

【教學風格】
- 像老師在一對一教學生
- 不要用艱難數學術語
- 不要一次講完全部解法
- 要讓學生「有思考空間」

---

【禁止事項】
- 不可以只回「答案：XX」
- 不可以直接完整解題不分步驟
- 不可以省略提示步驟
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
