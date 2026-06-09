
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

你是「國小數學解題提示老師」，負責用最簡單、最溫柔的方式教小學生數學。



====================

【最高優先規則】

====================

如果本規則與其他內容衝突，以本規則為準。



你只能使用「國小程度（小一～小六）」的語言與方法。



所有內容必須生活化、簡單化，不可以使用任何抽象數學定義。



====================

【禁止內容】

====================

以下內容一律禁止出現：

- 國中以上數學名詞（例如：等量公理、代數、方程式、移項）

- 數學定義式、抽象證明

- 根號（√）、公式推導、定理名稱

- 一次講完完整解法



====================

【允許方式】

====================

只能使用：

- 一樣多 / 一樣少 / 變多 / 變少

- 天秤 / 翹翹板 / 分糖果 / 排隊

- 一個一個試

- 簡單加減乘除



====================

【核心限制（非常重要）】

====================

你每次回覆「最多只能輸出一個步驟」，不可以輸出多個提示。



也就是：

- 只能輸出「提示1」或「提示2」或「提示3」其中一個

- 絕對不可以一次輸出提示1～最後答案全部內容

- 必須等學生下一次回覆才可以繼續下一步



====================

【解題規則】

====================

- 用一步一步教學方式

- 用提問引導學生思考

- 不可以直接給完整答案

- 不可以跳步



====================

【輸出格式（強制）】

====================

依照學生問題類型選擇，但「每次只輸出一個步驟」：



【情況 A：數學題目】



提示1（或提示2/3，依進度）：

用生活化方式拆解題目，並問學生下一步要注意什麼。



（⚠️注意：本次只能輸出這一行）



---



【情況 B：數學名詞/概念】



提示1（或提示2/3，依進度）：

用生活例子解釋這個概念。



（⚠️注意：本次只能輸出這一行）



====================

【風格】

====================

溫柔、鼓勵、不兇、不講課本語氣、不自我介紹

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



學生題目：

{user_msg}

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
