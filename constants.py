# constants.py
# 存放不敏感的常量設定

# 支援的貨幣代碼和名稱映射
CURRENCY_MAPPING = {
    # 貨幣名稱對應
    "美金": "USD",
    "美元": "USD",
    "日幣": "JPY",
    "日元": "JPY",
    "韓幣": "KRW",
    "韓元": "KRW",
    "人民幣": "CNY",
    "泰銖": "THB",
    "歐元": "EUR",
    # 貨幣代碼對應
    "USD": "USD",
    "JPY": "JPY",
    "KRW": "KRW",
    "CNY": "CNY",
    "THB": "THB",
    "EUR": "EUR"
}

# 貨幣代碼到顯示名稱的映射
CURRENCY_DISPLAY_NAMES = {
    "USD": "美金",
    "JPY": "日幣",
    "KRW": "韓幣",
    "CNY": "人民幣",
    "THB": "泰銖",
    "EUR": "歐元"
}