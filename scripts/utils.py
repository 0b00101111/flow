# scripts/utils.py

import os
import re
import requests
from datetime import datetime

def slugify(text):
    """将文本转换为 URL 友好的 slug"""
    # 转换为小写
    text = text.lower()
    # 移除非字母数字字符
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # 用连字符替换空格
    text = re.sub(r'\s+', '-', text)
    # 移除多个连字符
    text = re.sub(r'-+', '-', text)
    # 去除开头和结尾的连字符
    text = text.strip('-')
    return text

def send_telegram_message(chat_id, text):
    """通过 Telegram 发送消息"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("错误：TELEGRAM_BOT_TOKEN 未设置")
        return False

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }

    try:
        response = requests.post(url, json=payload)
        return response.status_code == 200
    except Exception as e:
        print(f"发送 Telegram 消息错误：{e}")
        return False

def get_last_update_id():
    """获取最后处理的 Telegram 更新 ID"""
    try:
        with open('data/last_update_id.txt', 'r') as f:
            return int(f.read().strip() or "0")
    except (FileNotFoundError, ValueError):
        return 0

def save_last_update_id(update_id):
    """保存最后处理的 Telegram 更新 ID"""
    os.makedirs('data', exist_ok=True)
    with open('data/last_update_id.txt', 'w') as f:
        f.write(str(update_id))

def detect_language(text):
    """
    检测文本是主要是中文还是英文。
    返回 'zh' 表示中文，'en' 表示英文。
    """
    # 简单检测：如果超过 20% 的字符是中文，则认为是中文
    chinese_char_count = 0
    total_count = 0

    for char in text:
        if ord(char) > 127:  # 非 ASCII 字符
            # 检查是否在常见中文字符范围内
            if '\u4e00' <= char <= '\u9fff':
                chinese_char_count += 1
        total_count += 1

    # 跳过空文本
    if total_count == 0:
        return 'zh'  # 默认返回中文

    # 如果超过 20% 是中文字符，认为是中文
    if chinese_char_count / total_count > 0.2:
        return 'zh'
    else:
        return 'en'

def format_reminder_message(untagged_thoughts):
    """根据每个想法的语言格式化提醒消息"""
    if not untagged_thoughts:
        return None

    # 按语言分组想法
    en_thoughts = []
    zh_thoughts = []

    for thought in untagged_thoughts:
        language = thought.get("language", "zh")  # 默认中文
        if language == "zh":
            zh_thoughts.append(thought)
        else:
            en_thoughts.append(thought)

    # 创建消息部分
    message_parts = []

    # 中文提醒（优先）
    if zh_thoughts:
        zh_message = "🔔 *提醒：您有未标记的想法*\n\n"
        for thought in zh_thoughts:
            snippet = thought["content"][:50] + "..." if len(thought["content"]) > 50 else thought["content"]
            zh_message += f"• {snippet}\n"
        zh_message += "\n请为这些想法添加标签以进行处理。"
        message_parts.append(zh_message)

    # 英文提醒
    if en_thoughts:
        en_message = "🔔 *Reminder: You have untagged thoughts*\n\n"
        for thought in en_thoughts:
            snippet = thought["content"][:50] + "..." if len(thought["content"]) > 50 else thought["content"]
            en_message += f"• {snippet}\n"
        en_message += "\nPlease tag these thoughts to process them."
        message_parts.append(en_message)

    # 合并消息
    return "\n\n---\n\n".join(message_parts)
