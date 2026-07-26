import os
import json
import requests
from datetime import datetime

def send_tg_msg():
    bot_token = os.getenv("TG_BOT_TOKEN")
    chat_id = os.getenv("TG_CHAT_ID")
    
    if not bot_token or not chat_id:
        print("未找到 Telegram 密钥，请检查 GitHub Secrets。")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    
    # ---------------- 第一步：发送文字概览 ----------------
    job_messages = []
    try:
        with open('all_companies_jobs.json', 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            
        # 文字消息里只放前 5 个最匹配的，作为引子
        for job in jobs[:5]: 
            title = job.get('job_name', job.get('title', job.get('name', '未知岗位')))
            company = job.get('company', job.get('company_name', '未知公司'))
            url = job.get('url', job.get('link', job.get('job_url', '无链接')))
            score = job.get('score', job.get('match_score', '未评分'))
            job_messages.append(f"🏢 <b>{company}</b> | {title}\n⭐ 匹配度：{score}\n🔗 {url}\n")
    except Exception as e:
        job_messages.append("⚠️ 读取部分岗位速览时出错。")

    jobs_text = "\n".join(job_messages)
    text = f"🌞 早上好！今日 ({today}) 的校招雷达已运行完毕。\n\n🎯 <b>今日 Top 5 高薪/高匹配岗位速览：</b>\n\n{jobs_text}\n📥 <b>完整岗位数据表已附在下方，请点击查收！</b>"
    
    url_message = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    requests.post(url_message, json={
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    })
    
    # ---------------- 第二步：发送完整的数据文件 ----------------
    url_document = f"https://api.telegram.org/bot{bot_token}/sendDocument"
    
    # 我们把 CSV 和 JSON 文件都尝试发给你
    files_to_send = ['jobs_enriched.csv', 'all_companies_jobs.json']
    
    for file_name in files_to_send:
        if os.path.exists(file_name):
            with open(file_name, 'rb') as document_file:
                print(f"正在发送完整文件: {file_name}...")
                response = requests.post(
                    url_document, 
                    data={"chat_id": chat_id}, 
                    files={"document": document_file}
                )
                if response.status_code == 200:
                    print(f"✅ {file_name} 文件发送成功！")
                else:
                    print(f"❌ 发送 {file_name} 失败: {response.text}")
        else:
            print(f"⚠️ 未找到文件: {file_name}，可能今日无新增数据。")

if __name__ == "__main__":
    send_tg_msg()
