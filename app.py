import os
from flask import Flask, request, abort

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

from google import genai

app = Flask(__name__)

# ======================
# LINE / Gemini 設定
# ======================
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

client = genai.Client(api_key=GEMINI_API_KEY)

# ======================
# 記憶系統（Render 版：暫存記憶）
# ======================
chat_history = {}
MAX_HISTORY = 8

# ======================
# 讀取資料庫
# ======================
with open("math_knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

KNOWLEDGE_BASE = KNOWLEDGE_BASE[:3000]

# ======================
# System Prompt（優化版）
# ======================
SYSTEM_PROMPT = """
你是國小數學老師，只能用引導方式教學。

規則：
1. 不可以直接給答案
2. 每次只能給一個提示
3. 不可以跳步驟
4. 必須用生活例子（糖果、錢、排隊）
5. 回答不超過80字、3行
6. 用鼓勵語氣
7. 如果學生答錯，先鼓勵再給提示

重要：
所有例子必須和問題完全相關，不可跳題或亂舉例。
"""

# ======================
# Webhook
# ======================
@app.route("/webhook", methods=['POST'])
def webhook():
    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'


# ======================
# 主邏輯
# ======================
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    user_id = event.source.user_id
    user_msg = event.message.text

    # 初始化記憶
    if user_id not in chat_history:
        chat_history[user_id] = []

    try:
        # ======================
        # 建立對話內容（含記憶）
        # ======================
        contents = []

        # system prompt
        contents.append({
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT}]
        })

        # history
        for msg in chat_history[user_id]:
            contents.append({
                "role": msg["role"],
                "parts": [{"text": msg["text"]}]
            })

        # current user message
        contents.append({
            "role": "user",
            "parts": [{"text": user_msg}]
        })

        # ======================
        # 呼叫 Gemini
        # ======================
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=contents
        )

        reply = response.text.strip()

    except Exception as e:
        print("Gemini error:", e)
        reply = "系統忙碌，請再試一次"

    # ======================
    # 更新記憶（只存成功對話）
    # ======================
    chat_history[user_id].append({
        "role": "user",
        "text": user_msg
    })

    chat_history[user_id].append({
        "role": "model",
        "text": reply
    })

    # 限制記憶長度（避免爆 token）
    chat_history[user_id] = chat_history[user_id][-MAX_HISTORY:]

    # ======================
    # 回覆 LINE
    # ======================
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply)
    )


if __name__ == "__main__":
    app.run()
