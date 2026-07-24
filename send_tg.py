import os
import requests
from datetime import datetime

def send_tg_msg():
    bot_token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("未找到 Telegram 密钥，请检查 GitHub Secrets。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    text = f"🌞 早上好！今日 ({today}) 的校招雷达已运行完毕。\n\n✅ 新岗位数据已抓取并更新至 GitHub 仓库。\n\n💻 赶紧打开电脑查看最新匹配的岗位吧！"
    
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    response = requests.post(url, json=payload)
    if response.status_code == 200:
        print("Telegram 消息发送成功！")
    else:
        print(f"发送失败，状态码：{response.status_code}，返回内容：{response.text}")

if __name__ == "__main__":
    send_tg_msg()
