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
from content_processor import process_content, create_daily_digest
from sns_manager import process_sns_queues  # Import the SNS queue processing function

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

def list_queues():
    """List all queues and their content."""
    try:
        with open('data/queues.json', 'r') as f:
            queues = json.load(f)
        
        queue_contents = []
        
        # Format Threads queue
        if queues.get("threads"):
            threads_items = [f"  {i+1}. {item['text'][:50]}..." for i, item in enumerate(queues["threads"])]
            queue_contents.append(f"Threads Queue ({len(queues['threads'])} items):\n" + "\n".join(threads_items))
        else:
            queue_contents.append("Threads Queue: Empty")
        
        # Format Mastodon queue
        if queues.get("mastodon"):
            mastodon_items = [f"  {i+1}. {item['text'][:50]}..." for i, item in enumerate(queues["mastodon"])]
            queue_contents.append(f"Mastodon Queue ({len(queues['mastodon'])} items):\n" + "\n".join(mastodon_items))
        else:
            queue_contents.append("Mastodon Queue: Empty")
        
        # Format Telegram queue
        if queues.get("telegram"):
            telegram_items = [f"  {i+1}. {item['text'][:50]}..." for i, item in enumerate(queues["telegram"])]
            queue_contents.append(f"Telegram Queue ({len(queues['telegram'])} items):\n" + "\n".join(telegram_items))
        else:
            queue_contents.append("Telegram Queue: Empty")
        
        # Send the queue contents to the authorized user
        message = "📋 **Current SNS Queues**\n\n" + "\n\n".join(queue_contents)
        send_telegram_message(AUTHORIZED_USER_ID, message)
        return True
    except Exception as e:
        print(f"Error listing queues: {e}")
        return False

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
                    command = text[1:].strip().lower()
                    
                    if command == "queues":
                        list_queues()
                        send_telegram_message(chat_id, "Queues listed above.")
                        updates_processed += 1
                        continue
                    
                    elif command.startswith("queue_"):
                        platform = command[6:]  # Extract platform name
                        if platform in ["threads", "mastodon", "telegram"]:
                            # Load queues
                            try:
                                with open('data/queues.json', 'r') as f:
                                    queues = json.load(f)
                                
                                # Format items in the queue
                                if platform in queues and queues[platform]:
                                    items = [f"{i+1}. {item['text'][:50]}..." for i, item in enumerate(queues[platform])]
                                    message = f"{platform.capitalize()} Queue ({len(queues[platform])} items):\n" + "\n".join(items)
                                else:
                                    message = f"{platform.capitalize()} Queue is empty."
                                
                                send_telegram_message(chat_id, message)
                            except Exception as e:
                                send_telegram_message(chat_id, f"Error listing {platform} queue: {str(e)}")
                        else:
                            send_telegram_message(chat_id, f"Unknown platform: {platform}")
                        updates_processed += 1
                        continue
                    
                    elif command.startswith("dequeue_"):
                        platform = command[8:]  # Extract platform name
                        if platform in ["threads", "mastodon", "telegram"]:
                            # Load queues
                            try:
                                with open('data/queues.json', 'r') as f:
                                    queues = json.load(f)
                                
                                # Remove first item if queue isn't empty
                                if platform in queues and queues[platform]:
                                    removed = queues[platform].pop(0)
                                    with open('data/queues.json', 'w') as f:
                                        json.dump(queues, f, indent=2)
                                    send_telegram_message(chat_id, f"Removed first item from {platform} queue:\n{removed['text'][:100]}...")
                                else:
                                    send_telegram_message(chat_id, f"{platform.capitalize()} Queue is already empty.")
                            except Exception as e:
                                send_telegram_message(chat_id, f"Error dequeuing from {platform}: {str(e)}")
                        else:
                            send_telegram_message(chat_id, f"Unknown platform: {platform}")
                        updates_processed += 1
                        continue
                    
                    else:
                        send_telegram_message(chat_id, f"Unknown command: {command}")
                        updates_processed += 1
                        continue

                # Process regular content - use process_content here
                try:
                    result = process_content(message)
                    if result:
                        print(f"Processed message with result: {result}")
                        # Check if a file was created
                        if 'file' in result:
                            print(f"Created file: {result['file']}")
                            # Print the contents of the file to check it
                            try:
                                with open(result['file'], 'r') as f:
                                    print(f"File contents:\n{f.read()}")
                            except Exception as e:
                                print(f"Error reading file: {e}")
                                
                        # Send a confirmation message back to the user
                        if result.get('type') == 'blog':
                            if result.get('language') == 'zh':
                                send_telegram_message(chat_id, f"✅ 已处理您的内容: {result.get('title', '无标题')}")
                            else:
                                send_telegram_message(chat_id, f"✅ Processed your content: {result.get('title', 'Untitled')}")
                        elif result.get('type') == 'sns':
                            platform_results = result.get('platforms', [])
                            platforms_str = ", ".join(platform_results)
                            send_telegram_message(chat_id, f"✅ Added to SNS queues: {platforms_str}")
                        
                        updates_processed += 1
                except Exception as e:
                    print(f"Error processing message: {e}")
                    send_telegram_message(chat_id, f"❌ Error processing your message: {str(e)}")

    
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
        # Process the SNS queues
        process_sns_queues()
    
    elif args.action == 'list_queues':
        # List the contents of the queues
        list_queues()
    
    # Always return success to avoid GitHub Actions failures
    return 0

if __name__ == "__main__":
    sys.exit(main())
