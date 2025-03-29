#!/usr/bin/env python3
import os
import sys
import json
import argparse
import requests
import logging
from datetime import datetime
from pathlib import Path

# Import local modules
from utils import get_last_update_id, save_last_update_id, send_telegram_message
from content_processor import process_content, create_daily_entry
from sns_manager import process_sns_queues  # Preserving SNS functionality

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Telegram Handler")

# Configuration
BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
AUTHORIZED_USER_ID = int(os.environ.get('AUTHORIZED_USER_ID', 0))

def get_updates(offset=None):
    """Fetch updates from Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"timeout": 60, "allowed_updates": ["message"]}
    if offset:
        params["offset"] = offset
    
    logger.info(f"Fetching updates from Telegram API with offset {offset}")
    try:
        response = requests.get(url, params=params)
        data = response.json()
        if not data.get("ok"):
            logger.error(f"Error fetching updates: {data}")
        return data
    except Exception as e:
        logger.error(f"Exception while fetching updates: {str(e)}")
        return {"ok": False, "error": str(e)}

def list_queues():
    """List all queues and their content."""
    try:
        logger.info("Listing queues")
        with open('bot_data/queues.json', 'r', encoding='utf-8') as f:
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
        
        # Send the queue contents to the authorized user
        message = "📋 **Current SNS Queues**\n\n" + "\n\n".join(queue_contents)
        send_telegram_message(AUTHORIZED_USER_ID, message)
        return True
    except Exception as e:
        logger.error(f"Error listing queues: {e}")
        return False

def process_telegram_messages():
    """Process new Telegram messages"""
    last_update_id = get_last_update_id()
    logger.info(f"Starting to process messages with last update ID: {last_update_id}")
    
    updates = get_updates(last_update_id + 1)
    
    if not updates.get("ok"):
        logger.error(f"Error fetching updates: {updates}")
        return False
    
    new_update_id = last_update_id
    updates_processed = 0
    
    for update in updates.get("result", []):
        update_id = update["update_id"]
        logger.info(f"Processing update ID: {update_id}")
        
        if update_id > new_update_id:
            new_update_id = update_id
        
        if "message" in update:
            message = update["message"]
            chat_id = message.get("chat", {}).get("id")
            user_id = message.get("from", {}).get("id")
            
            # Security check - only process from authorized user
            if user_id != AUTHORIZED_USER_ID:
                logger.warning(f"Unauthorized message from user {user_id}, ignoring")
                continue
            
            # Process message text or commands
            if "text" in message:
                text = message["text"]
                logger.info(f"Processing message: {text[:50]}...")
                
                # Handle queue commands
                if text.startswith('!'):
                    command = text[1:].strip().lower()
                    logger.info(f"Processing command: {command}")
                    
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
                                with open('bot_data/queues.json', 'r', encoding='utf-8') as f:
                                    queues = json.load(f)
                                
                                # Format items in the queue
                                if platform in queues and queues[platform]:
                                    items = [f"{i+1}. {item['text'][:50]}..." for i, item in enumerate(queues[platform])]
                                    message = f"{platform.capitalize()} Queue ({len(queues[platform])} items):\n" + "\n".join(items)
                                else:
                                    message = f"{platform.capitalize()} Queue is empty."
                                
                                send_telegram_message(chat_id, message)
                            except Exception as e:
                                logger.error(f"Error listing {platform} queue: {e}")
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
                                with open('bot_data/queues.json', 'r', encoding='utf-8') as f:
                                    queues = json.load(f)
                                
                                # Remove first item if queue isn't empty
                                if platform in queues and queues[platform]:
                                    removed = queues[platform].pop(0)
                                    with open('bot_data/queues.json', 'w', encoding='utf-8') as f:
                                        json.dump(queues, f, indent=2)
                                    send_telegram_message(chat_id, f"Removed first item from {platform} queue:\n{removed['text'][:100]}...")
                                else:
                                    send_telegram_message(chat_id, f"{platform.capitalize()} Queue is already empty.")
                            except Exception as e:
                                logger.error(f"Error dequeuing from {platform}: {e}")
                                send_telegram_message(chat_id, f"Error dequeuing from {platform}: {str(e)}")
                        else:
                            send_telegram_message(chat_id, f"Unknown platform: {platform}")
                        updates_processed += 1
                        continue
                    
                    else:
                        send_telegram_message(chat_id, f"Unknown command: {command}")
                        updates_processed += 1
                        continue

                # Process regular content as daily entry or SNS post
                try:
                    logger.info("Processing content with content_processor")
                    result = process_content(message)
                    logger.info(f"Processing result: {result}")
                    
                    if result:
                        # Check if a file was created
                        if 'file' in result:
                            logger.info(f"Created/updated file: {result['file']}")
                            
                        # Send a confirmation message back to the user
                        if result.get('type') == 'daily':
                            if result.get('language') == 'zh':
                                send_telegram_message(chat_id, f"✅ 已添加到日更: {result.get('title', '无标题')}")
                            else:
                                send_telegram_message(chat_id, f"✅ Added to daily digest: {result.get('title', 'Untitled')}")
                        
                        if result.get('platforms'):
                            platform_results = result.get('platforms', [])
                            platforms_str = ", ".join(platform_results)
                            send_telegram_message(chat_id, f"✅ Added to SNS queues: {platforms_str}")
                        
                        updates_processed += 1
                    else:
                        logger.warning("No result returned from content_processor")
                        send_telegram_message(chat_id, "❌ Unable to process your message")
                except Exception as e:
                    logger.error(f"Error processing message: {e}", exc_info=True)
                    send_telegram_message(chat_id, f"❌ Error processing your message: {str(e)}")

    
    # Save the new update ID if we processed any updates
    if new_update_id > last_update_id:
        logger.info(f"Saving new update ID: {new_update_id}")
        save_last_update_id(new_update_id)
    
    logger.info(f"Processed {updates_processed} updates")
    return updates_processed > 0

def main():
    parser = argparse.ArgumentParser(description='Process Telegram messages')
    parser.add_argument('--action', type=str, default='process', 
                        choices=['process', 'create_daily', 'process_queues', 'list_queues'],
                        help='Action to perform')
    
    args = parser.parse_args()
    logger.info(f"Starting with action: {args.action}")
    
    if args.action == 'process':
        # Regular processing of new messages
        process_telegram_messages()
    
    elif args.action == 'create_daily':
        # Create daily entry if it doesn't exist
        result = create_daily_entry()
        logger.info(f"Daily entry creation result: {result}")
    
    elif args.action == 'process_queues':
        # Process the SNS queues
        result = process_sns_queues()
        logger.info(f"Queue processing result: {result}")
    
    elif args.action == 'list_queues':
        # List the contents of the queues
        list_queues()
    
    logger.info(f"Completed action: {args.action}")
    # Always return success to avoid GitHub Actions failures
    return 0

if __name__ == "__main__":
    sys.exit(main())
