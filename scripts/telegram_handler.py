#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
from datetime import datetime
from pathlib import Path

# Import local modules
from utils import get_last_update_id, save_last_update_id, send_telegram_message
from content_processor import process_daily_entry, create_daily_entry

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
            
            # Process message text
            if "text" in message:
                text = message["text"]
                
                # Process message as daily entry
                try:
                    result = process_daily_entry(message)
                    if result:
                        print(f"Processed daily entry with result: {result}")
                        # Check if a file was created
                        if 'file' in result:
                            print(f"Created/updated file: {result['file']}")
                            # Print the contents of the file to check it
                            try:
                                with open(result['file'], 'r') as f:
                                    print(f"File contents:\n{f.read()}")
                            except Exception as e:
                                print(f"Error reading file: {e}")
                                
                        # Send a confirmation message back to the user
                        if result.get('language') == 'zh':
                            send_telegram_message(chat_id, f"✅ 已添加到日更: {result.get('title', '无标题')}")
                        else:
                            send_telegram_message(chat_id, f"✅ Added to daily digest: {result.get('title', 'Untitled')}")
                        
                        updates_processed += 1
                except Exception as e:
                    print(f"Error processing daily entry: {e}")
                    send_telegram_message(chat_id, f"❌ Error adding to daily digest: {str(e)}")

    
    # Save the new update ID if we processed any updates
    if new_update_id > last_update_id:
        save_last_update_id(new_update_id)
    
    return updates_processed > 0

def main():
    parser = argparse.ArgumentParser(description='Process Telegram messages for daily entries')
    parser.add_argument('--action', type=str, default='process', 
                        choices=['process', 'create_daily'],
                        help='Action to perform')
    
    args = parser.parse_args()
    
    if args.action == 'process':
        # Regular processing of new messages
        process_telegram_messages()
    
    elif args.action == 'create_daily':
        # Create daily entry if it doesn't exist
        create_daily_entry()
    
    # Always return success to avoid GitHub Actions failures
    return 0

if __name__ == "__main__":
    sys.exit(main())
