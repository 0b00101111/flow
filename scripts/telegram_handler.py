#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

# 导入本地模块
from utils import get_last_update_id, save_last_update_id, send_telegram_message, format_reminder_message

# 配置
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID = int(os.environ.get('AUTHORIZED_USER_ID', 0))

def get_updates(offset=None):
    """从 Telegram 获取更新"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 60, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset

    response = requests.get(url, params=params)
    return response.json()

def process_telegram_messages():
    """处理新的 Telegram 消息"""
    last_update_id = get_last_update_id()
    updates = get_updates(last_update_id + 1)

    if not updates.get("ok"):
        print(f"获取更新时出错：{updates}")
        return False

    new_update_id = last_update_id
    updates_processed = 0

    for update in updates.get("result", []):
        update_id = update["update_id"]

        if update_id > new_update_id:
            new_update_id = update_id

        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")

            # 安全检查 - 只处理来自授权用户的消息
            if user_id != AUTHORIZED_USER_ID:
                continue

            # 处理消息文本或命令
            if "text" in message:
                text = message["text"]

                # 处理队列命令
                if text.startswith('!'):
                    # 稍后添加此功能
                    print(f"队列命令：{text}")
                    updates_processed += 1
                    continue

                # 处理常规内容
                print(f"处理消息：{text[:30]}...")
                # 稍后添加内容处理
                updates_processed += 1

    # 如果处理了任何更新，则保存新的更新 ID
    if new_update_id > last_update_id:
        save_last_update_id(new_update_id)

    return updates_processed > 0

def send_reminders():
    """发送未标记想法的提醒"""
    try:
        with open('data/untagged_thoughts.json', 'r') as f:
            untagged = json.load(f)

        reminder_message = format_reminder_message(untagged)
        if reminder_message:
            send_telegram_message(AUTHORIZED_USER_ID, reminder_message)
            return True
    except Exception as e:
        print(f"发送提醒时出错：{e}")

    return False

def main():
    parser = argparse.ArgumentParser(description='处理 Telegram 消息')
    parser.add_argument('--action', type=str, default='process',
                        choices=['process', 'reminder', 'publish_digest', 'process_queues', 'list_queues'],
                        help='要执行的操作')

    args = parser.parse_args()

    if args.action == 'process':
        # 常规消息处理
        process_telegram_messages()

    elif args.action == 'reminder':
        # 发送未标记想法的提醒
        send_reminders()

    elif args.action == 'publish_digest':
        # 稍后实现
        print("发布摘要...")

    elif args.action == 'process_queues':
        # 稍后实现
        print("处理队列...")

    elif args.action == 'list_queues':
        # 稍后实现
        print("列出队列...")

if __name__ == "__main__":
    main()
