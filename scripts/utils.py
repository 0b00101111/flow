# scripts/utils.py
import os
import re
import requests
import json
from datetime import datetime

def slugify(text):
    """Convert text to a URL-friendly slug"""
    # Convert to lowercase
    text = text.lower()
    # Remove non-alphanumeric characters
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    # Remove multiple hyphens
    text = re.sub(r'-+', '-', text)
    # Trim hyphens from beginning and end
    text = text.strip('-')
    return text

def send_telegram_message(chat_id, text):
    """Send a message via Telegram"""
    bot_token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not bot_token:
        print("Error: TELEGRAM_BOT_TOKEN not set")
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
        print(f"Error sending Telegram message: {e}")
        return False

def get_last_update_id():
    """Get the last processed Telegram update ID"""
    try:
        with open('data/last_update_id.txt', 'r') as f:
            return int(f.read().strip() or "0")
    except (FileNotFoundError, ValueError):
        return 0

def save_last_update_id(update_id):
    """Save the last processed Telegram update ID"""
    os.makedirs('data', exist_ok=True)
    with open('data/last_update_id.txt', 'w') as f:
        f.write(str(update_id))

def detect_language(text):
    """
    Detect if text is primarily Chinese or English.
    Returns 'zh' for Chinese, 'en' for English.
    """
    # Simple detection: if more than 20% of characters are Chinese, consider it Chinese
    chinese_char_count = 0
    total_count = 0
    
    for char in text:
        if ord(char) > 127:  # Non-ASCII character
            # Check if it's in common Chinese character range
            if '\u4e00' <= char <= '\u9fff':
                chinese_char_count += 1
        total_count += 1
    
    # Skip empty text
    if total_count == 0:
        return 'zh'  # Default to Chinese
    
    # If more than 20% Chinese characters, consider it Chinese
    if chinese_char_count / total_count > 0.2:
        return 'zh'
    else:
        return 'en'

def ensure_directory_exists(filepath):
    """Ensure the directory for a file path exists"""
    directory = os.path.dirname(filepath)
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    return True

def format_time_difference(timestamp_str):
    """Format time difference between timestamp and now"""
    timestamp = datetime.fromisoformat(timestamp_str)
    now = datetime.now()
    
    delta = now - timestamp
    
    if delta.days > 0:
        if detect_language(str(delta.days)) == 'zh':
            return f"{delta.days} 天前"
        else:
            return f"{delta.days} days ago"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        if detect_language(str(hours)) == 'zh':
            return f"{hours} 小时前"
        else:
            return f"{hours} hours ago"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        if detect_language(str(minutes)) == 'zh':
            return f"{minutes} 分钟前"
        else:
            return f"{minutes} minutes ago"
    else:
        if detect_language("just now") == 'zh':
            return "刚刚"
        else:
            return "just now"

def load_json_file(filepath, default=None):
    """Load a JSON file, returning a default value if the file doesn't exist"""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        return default if default is not None else {}
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return default if default is not None else {}

def save_json_file(filepath, data):
    """Save data to a JSON file"""
    try:
        ensure_directory_exists(filepath)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Error saving JSON file: {e}")
        return False
