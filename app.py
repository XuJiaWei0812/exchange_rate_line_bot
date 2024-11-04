from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    RichMenuSize,
    RichMenuRequest,
    RichMenuArea,
    RichMenuBounds,
    MessageAction,
    ReplyMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
import requests
import json
import os
import re
from constants import CURRENCY_MAPPING, CURRENCY_DISPLAY_NAMES

app = Flask(__name__)

configuration = Configuration(access_token=os.getenv("CHANNEL_ACCESS_TOKEN"))
line_handler = WebhookHandler(os.getenv("CHANNEL_SECRET"))


@app.route("/callback", methods=["POST"])
def callback():
    # get X-Line-Signature header value
    signature = request.headers["X-Line-Signature"]

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        line_handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info(
            "Invalid signature. Please check your channel access token/channel secret."
        )
        abort(400)

    return "OK"


def create_rich_menu():
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_blob_api = MessagingApiBlob(api_client)

        headers = {
            "Authorization": "Bearer " + CHANNEL_ACCESS_TOKEN,
            "Content-Type": "application/json",
        }

        # 刪除所有現有的 rich menus
        rich_menu_list = requests.get("https://api.line.me/v2/bot/richmenu/list", headers=headers).json()
        for rich_menu in rich_menu_list.get("richmenus", []):
            delete_response = requests.delete(
                f"https://api.line.me/v2/bot/richmenu/{rich_menu['richMenuId']}",
                headers=headers
            )

        # 新的 rich menu 資料
        body = {
            "size": {"width": 2500, "height": 1686},
            "selected": True,
            "name": "匯率查詢選單",
            "chatBarText": "點擊查詢匯率",
            "areas": [
                {"bounds": {"x": 0, "y": 0, "width": 833, "height": 843}, "action": {"type": "message", "text": "人民幣匯率"}},
                {"bounds": {"x": 834, "y": 0, "width": 833, "height": 843}, "action": {"type": "message", "text": "美金匯率"}},
                {"bounds": {"x": 1663, "y": 0, "width": 834, "height": 843}, "action": {"type": "message", "text": "日幣匯率"}},
                {"bounds": {"x": 0, "y": 843, "width": 833, "height": 843}, "action": {"type": "message", "text": "韓幣匯率"}},
                {"bounds": {"x": 834, "y": 843, "width": 833, "height": 843}, "action": {"type": "message", "text": "泰銖匯率"}},
                {"bounds": {"x": 1662, "y": 843, "width": 838, "height": 843}, "action": {"type": "message", "text": "歐元匯率"}},
            ],
        }

        # 創建新的 rich menu
        response = requests.post("https://api.line.me/v2/bot/richmenu", headers=headers, data=json.dumps(body))
        if response.status_code == 200:
            rich_menu_id = response.json().get("richMenuId")
            
            # 上傳 rich menu 圖片
            with open("static/richmenu.jpg", "rb") as image:
                image_response = requests.post(
                    f"https://api.line.me/v2/bot/richmenu/{rich_menu_id}/content",
                    headers={"Authorization": "Bearer " + CHANNEL_ACCESS_TOKEN, "Content-Type": "image/jpeg"},
                    data=image
                )

            # 設置為預設選單
            default_response = requests.post(
                f"https://api.line.me/v2/bot/user/all/richmenu/{rich_menu_id}",
                headers={"Authorization": "Bearer " + CHANNEL_ACCESS_TOKEN}
            )



def get_exchange_rate(currency_code, currency_name):
    """
    查詢 TWD 與指定貨幣的雙向匯率
    """
    try:
        # 發送 GET 請求獲取匯率資料
        response = requests.get(os.getenv("EXCHANGE_RATE_API_URL"))
        data = response.json()
        rate = data["rates"].get(currency_code)

        if rate:
            # 計算雙向匯率
            twd_to_foreign = round(float(rate), 2)
            foreign_to_twd = round(1 / float(rate), 2)

            # 獲取貨幣顯示名稱
            display_name = CURRENCY_DISPLAY_NAMES.get(currency_code, currency_code)

            # 組織回覆訊息
            reply = (
                f"📌 匯率換算結果：\n"
                f"1 台幣 = {twd_to_foreign} {display_name}\n"
                f"1 {display_name} = {foreign_to_twd} 台幣\n\n"
                f"！！此匯率僅供參考使用！！！\n"
                f"！！實際匯率請以銀行為準！！\n\n"
                f"💡 小提示：您可以直接輸入想要換算的金額，例如：\n"
                f"「100{display_name}」或「{currency_code} 100」"
            )
            return reply
    except Exception as e:
        print(f"匯率查詢錯誤: {e}")
    return f"無法取得 {currency_name} 的匯率資訊"


def parse_amount_and_currency(text):
    """
    解析使用者輸入的金額和幣種
    """
    # 檢查是否輸入台幣
    if "台幣" in text or "臺幣" in text:
        return "TWD", None, None

    # 匹配數字和貨幣名稱/代碼的模式
    # 支援格式：
    # - 數字+貨幣名稱/代碼 (例如：100美金, 100USD)
    # - 貨幣名稱/代碼+數字 (例如：美金100, USD100)
    pattern = r"(\d+\.?\d*)\s*([a-zA-Z一-龥]+)|([a-zA-Z一-龥]+)\s*(\d+\.?\d*)"
    match = re.search(pattern, text)

    if match:
        if match.group(1) and match.group(2):
            amount = float(match.group(1))
            currency_input = match.group(2)
        else:
            amount = float(match.group(4))
            currency_input = match.group(3)

        # 嘗試從映射中獲取貨幣代碼
        currency_code = CURRENCY_MAPPING.get(currency_input)
        if currency_code:
            currency_name = CURRENCY_DISPLAY_NAMES.get(currency_code, currency_input)
            return amount, currency_code, currency_name

    return None, None, None


@line_handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        text = event.message.text

        # 處理圖文選單的固定選項
        if text.endswith("匯率"):
            currency_code = {
                "人民幣匯率": "CNY",
                "美金匯率": "USD",
                "日幣匯率": "JPY",
                "韓幣匯率": "KRW",
                "泰銖匯率": "THB",
                "歐元匯率": "EUR",
            }.get(text)

            if currency_code:
                reply_text = get_exchange_rate(currency_code, text)
            else:
                reply_text = "無法識別的貨幣類型"
        else:
            # 處理使用者輸入的金額換算
            amount, currency_code, currency_name = parse_amount_and_currency(text)

            if amount == "TWD":
                # 提示使用者不支援台幣換算
                reply_text = (
                    "😅 不好意思，本服務僅提供外幣換算台幣\n"
                    "請直接輸入外幣金額，例如：\n"
                    "✅ 100美金\n"
                    "✅ JPY 5000\n"
                    "✅ EUR 50"
                )
            elif amount and currency_code:
                # 進行匯率換算
                try:
                    response = requests.get(os.getenv("EXCHANGE_RATE_API_URL"))
                    data = response.json()
                    rate = data["rates"].get(currency_code)
                    if rate:
                        twd_amount = round(amount / float(rate), 2)
                        reply_text = (
                            f"💱 匯率換算結果：\n"
                            f"{amount} {currency_name} = {twd_amount} 台幣\n\n"
                            f"！！此匯率僅供參考使用！！\n"
                            f"！！實際匯率請以銀行為準！！"
                        )
                    else:
                        reply_text = f"無法取得 {currency_name} 的匯率資訊"
                except Exception as e:
                    print(f"匯率換算錯誤: {e}")
                    reply_text = "匯率換算發生錯誤，請稍後再試"
            else:
                # 格式錯誤提示
                reply_text = (
                    "🤔 看不懂這個格式呢！\n"
                    "💡 請這樣輸入：\n"
                    "✅ 100美金\n"
                    "✅ USD 100\n"
                    "✅ JPY 5000\n"
                    "❌ 不要輸入台幣喔！"
                )

        # 發送回覆
        line_bot_api.reply_message(
            ReplyMessageRequest(
                reply_token=event.reply_token, 
                messages=[TextMessage(text=reply_text)]
            )
        )


if __name__ == "__main__":
    create_rich_menu()  # 創建圖文選單
    app.run()
