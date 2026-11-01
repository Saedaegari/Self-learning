import requests

url = "https://xin1122.zeabur.app/api/usage/token/"
headers = {
    "Authorization": "Bearer sk-kqxyVaNlDYngq2kMvvd7MPLp9Ghk9U0eq2AsvZyhfqhDCTGT" # 記得換回你的真實金鑰
}

response = requests.get(url, headers=headers)
data = response.json()

# 確保請求成功 (code: True)
if data.get('code'):
    token_info = data.get('data', {})
    key_name = token_info.get('name')
    used = token_info.get('total_used', 0)
    available = token_info.get('total_available', 0)
    
    print(f"=== API Key [{key_name}] 用量資訊 ===")
    print(f"已使用額度: {used:,}")
    print(f"剩餘可用額度: {available:,}")
else:
    print(f"查詢失敗，訊息: {data.get('message')}")