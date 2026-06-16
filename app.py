import os
import time
import traceback
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
# 記憶系統
# ======================
chat_history = {}
MAX_HISTORY = 8

# ======================
# 換題觸發詞（重點新增）
# ======================
RESET_KEYWORDS = ["我懂了", "了解了", "知道了", "下一題", "換一題", "不懂了", "換題"]

# ======================
# 讀取資料庫
# ======================
with open("math_knowledge_base.txt", "r", encoding="utf-8") as f:
    KNOWLEDGE_BASE = f.read()

KNOWLEDGE_BASE = KNOWLEDGE_BASE[:3000]

# ======================
# System Prompt（強化版）
# ======================
SYSTEM_PROMPT = """
你是國小數學老師，只能用引導方式教學。

規則：
1. 不可以直接給答案
2. 每次只能給一個提示
3. 不可以延續上一題，除非使用者明確要求
4. 如果使用者說「我懂了、下一題、換一題」，必須立刻切換新題目
5. 必須用生活例子（糖果、錢、排隊）
6. 回答不超過80字、3行
7. 用鼓勵語氣
8. 禁止跳題或亂舉例

重要：
所有例子必須與當前問題完全相關。

【鼓勵規則（已修正過度誇獎）】
====================
1. 不可以每句都稱讚
2. 不可以使用「你真棒」「好棒喔」這種空泛稱讚
3. 每一題最多只能鼓勵一次
4. 只有在以下情況才能鼓勵：
   - 學生答對
   - 學生明顯接近正確
   - 教學結束時

5. 鼓勵必須簡短，例如：
   - 「很好，我們繼續」
   - 「不錯，再看下一步」
   - 「很接近了」
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

    # ======================
    # 🔥 換題偵測（超重要）
    # ======================
    if any(k in user_msg for k in RESET_KEYWORDS):
        chat_history[user_id] = []

    # 初始化記憶
    if user_id not in chat_history:
        chat_history[user_id] = []

    try:
        # ======================
        # 建立對話內容
        # ======================
        contents = []

        contents.append({
            "role": "user",
            "parts": [{"text": SYSTEM_PROMPT}]
        })

        for msg in chat_history[user_id]:
            contents.append({
                "role": msg["role"],
                "parts": [{"text": msg["text"]}]
            })

        contents.append({
            "role": "user",
            "parts": [{"text": user_msg}]
        })

        # ======================
        # 呼叫 Gemini（已升級：重試 + 備用模型）
        # ======================

        MODELS = [
            "gemini-2.5-flash",
            "gemini-2.0-flash"
        ]

        reply = None
        last_error = None

        for model_name in MODELS:

            for attempt in range(3):

                try:

                    print(
                        f"[Gemini] model={model_name} attempt={attempt + 1}"
                    )

                    response = client.models.generate_content(
                        model=model_name,
                        contents=contents
                    )

                    reply = response.text.strip()

                    print(
                        f"[Gemini] Success model={model_name}"
                    )

                    break

                except Exception as e:

                    last_error = e
                    error_text = str(e)

                    print(
                        f"[Gemini Error] model={model_name} attempt={attempt + 1}"
                    )
                    print(error_text)

                    if "503" in error_text or "UNAVAILABLE" in error_text:

                        wait_time = 2 * (attempt + 1)

                        print(f"[Retry] waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue

                    elif "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:

                        reply = "目前使用人數較多，請稍後再試。"
                        break

                    else:
                        break

            if reply:
                break

        if not reply:

            print("[Gemini Final Error]", last_error)

            reply = "系統目前較忙碌，請稍後再試一次。"

    except Exception as e:

        print("Gemini error:")
        print(e)

        traceback.print_exc()

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
