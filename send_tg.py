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
    
    # 提取生成的岗位数据
    job_messages = []
    try:
        # 尝试读取日志里生成的 json 文件
        with open('all_companies_jobs.json', 'r', encoding='utf-8') as f:
            jobs = json.load(f)
            
        # 为了防止 Telegram 消息超长报错，这里只提取前 8 个岗位
        # 假设 JSON 数据已经按推荐度排过序，或者我们直接拿最新的
        for job in jobs[:8]: 
            # 兼容不同字段名，以防爬虫格式变动
            title = job.get('job_name', job.get('title', job.get('name', '未知岗位')))
            company = job.get('company', job.get('company_name', '未知公司'))
            url = job.get('url', job.get('link', job.get('job_url', '无链接')))
            score = job.get('score', job.get('match_score', '未评分'))
            
            # 拼装单条岗位的信息
            job_messages.append(f"🏢 <b>{company}</b> | {title}\n⭐ 匹配度：{score}\n🔗 {url}\n")
            
    except FileNotFoundError:
        job_messages.append("⚠️ 未找到 all_companies_jobs.json 文件，可能是今天没有抓到新岗位。")
    except Exception as e:
        job_messages.append(f"⚠️ 读取岗位数据时出错：{e}")

    # 把所有岗位列表拼接到一起
    jobs_text = "\n".join(job_messages)
    
    # 最终的推送文案，使用 HTML 格式支持加粗
    text = f"🌞 早上好！今日 ({today}) 的校招雷达已运行完毕。\n\n🎯 <b>今日精选高匹配岗位：</b>\n\n{jobs_text}\n💻 更多详情请前往 GitHub 下载完整数据库查看。"
    
    url_api = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML", # 开启 HTML 渲染以支持粗体等格式
        "disable_web_page_preview": True # 【关键】禁用网址的卡片预览，否则屏幕会被占满
    }
    
    response = requests.post(url_api, json=payload)
    if response.status_code == 200:
        print("Telegram 消息发送成功！")
    else:
        print(f"发送失败，状态码：{response.status_code}，返回内容：{response.text}")

if __name__ == "__main__":
    send_tg_msg()
