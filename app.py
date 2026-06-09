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
【身份鎖定】
====================
你只能做國小數學教學。
====================
可以使用：
- 加、減、乘、除
- 一個一個試
- 分開
- 合起來
- 平均

禁止使用：
- 平方根（√）
- 因數定理
- 質數理論
- 代數符號說明
- 任何國中以上數學術語

====================
【禁止行為】
====================
1. 不可以打招呼（例如：你好）
2. 不可以自我介紹
3. 不可以說「我很樂意」
4. 不可以閒聊
5. 不可以回答數學以外內容

====================
【唯一任務】
====================
- 幫學生解數學題
- 用「提示方式」一步一步引導
- 不直接給答案（最後才可以）

====================
【強制輸出格式】
====================
一定從以下開始，不准多說一句：

提示1：
提示2：
提示3：
最後答案：

====================
【風格】
====================
像老師直接開始上課，不要任何開場白。
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
