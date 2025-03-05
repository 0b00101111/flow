#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Import local modules - add the import for content_processor
from utils import get_last_update_id, save_last_update_id, send_telegram_message
from content_processor import process_content, create_daily_digest  # Add this import

# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID = int(os.environ.get('AUTHORIZED_USER_ID', 0))

def get_updates(offset=None):
    """Fetch updates from Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 60, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    
    response = requests.get(url, params=params)
    return response.json()

def process_telegram_messages():
    """Process new Telegram messages"""
    last_update_id = get_last_update_id()
    updates = get_updates(last_update_id + 1)
    
    if not updates.get("ok"):
        print(f"Error fetching updates: {updates}")
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
            
            # Security check - only process from authorized user
            if user_id != AUTHORIZED_USER_ID:
                continue
            
            # Process message text or commands
            if "text" in message:
                text = message["text"]
                
                # Handle queue commands
                if text.startswith('!'):
                    # Will add this functionality later
                    print(f"Queue command: {text}")
                    updates_processed += 1
                    continue
                
                # Process regular content - use process_content here
                result = process_content(message)
                if result:
                    print(f"Processed message: {result}")
                    # Send a confirmation message back to the user
                    if result.get('type') == 'blog':
                        if result.get('language') == 'zh':
                            send_telegram_message(chat_id, f"✅ 已处理您的内容: {result.get('title', '无标题')}")
                        else:
                            send_telegram_message(chat_id, f"✅ Processed your content: {result.get('title', 'Untitled')}")
                    
                    updates_processed += 1
    
    # Save the new update ID if we processed any updates
    if new_update_id > last_update_id:
        save_last_update_id(new_update_id)
    
    return updates_processed > 0

def send_reminders():
    """Send reminders for untagged thoughts"""
    try:
        with open('data/untagged_thoughts.json', 'r') as f:
            untagged = json.load(f)
        
        from utils import format_reminder_message
        reminder_message = format_reminder_message(untagged)
        if reminder_message:
            send_telegram_message(AUTHORIZED_USER_ID, reminder_message)
            return True
    except Exception as e:
        print(f"Error sending reminders: {e}")
    
    return False

def main():
    parser = argparse.ArgumentParser(description='Process Telegram messages')
    parser.add_argument('--action', type=str, default='process', 
                        choices=['process', 'reminder', 'publish_digest', 'process_queues', 'list_queues'],
                        help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'process':
        # Regular processing of new messages
        process_telegram_messages()
    
    elif args.action == 'reminder':
        # Send reminders for untagged thoughts
        send_reminders()
    
    elif args.action == 'publish_digest':
        # Create and publish daily digest
        create_daily_digest()
    
    elif args.action == 'process_queues':
        # Will implement this later
        print("Processing queues...")
    
    elif args.action == 'list_queues':
        # Will implement this later
        print("Listing queues...")

if __name__ == "__main__":
    main()
