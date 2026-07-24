import os
import requests
import urllib.parse
from datetime import datetime

def send_whatsapp_msg():
    phone = os.getenv("WA_PHONE_NUMBER")
    api_key = os.getenv("WA_API_KEY")

    if not phone or not api_key:
        print("未找到 WhatsApp 密钥，请检查 GitHub Secrets。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    text = f"🌞 早上好！今日 ({today}) 的校招雷达已运行完毕。\n\n✅ 新岗位数据已抓取并经过 Gemini 分析，已更新至 GitHub 仓库。\n\n💻 赶紧打开电脑查看最新匹配的岗位吧！"

    encoded_text = urllib.parse.quote(text)
    url = f"https://api.callmebot.com/whatsapp.php?phone={phone}&text={encoded_text}&apikey={api_key}"

    response = requests.get(url)
    if response.status_code == 200:
        print("WhatsApp 消息发送成功！")
    else:
        print(f"发送失败，状态码：{response.status_code}")

if __name__ == "__main__":
    send_whatsapp_msg()
