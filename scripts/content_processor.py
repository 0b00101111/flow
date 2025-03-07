# scripts/content_processor.py

import os
import re
import json
import yaml
from datetime import datetime
from pathlib import Path
from utils import slugify, detect_language

def parse_tags(text):
    """Extract simple hashtags from text content."""
    # Regular expression to match simple tags like #daily, #threads, #mastodon
    tag_pattern = r'#([a-zA-Z0-9_]+)'
    
    tags = set()
    matches = re.finditer(tag_pattern, text)
    
    for match in matches:
        tag = match.group(1).lower()  # Extract tag without # and convert to lowercase
        tags.add(tag)
    
    return tags

def add_to_daily_entry(content, message_id, language="zh"):
    """Add content to the daily entry."""
    # Get today's date for the digest file
    today = datetime.now()
    
    # Convert to Vancouver time (Pacific Time)
    import pytz
    vancouver_tz = pytz.timezone('America/Vancouver')
    today_vancouver = datetime.now(pytz.utc).astimezone(vancouver_tz)
    
    date_str = today_vancouver.strftime('%Y-%m-%d')
    week_num = int(today_vancouver.strftime('%W')) + 1  # Get ISO week number and add 1
    
    # Day name based on language
    if language == "zh":
        day_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        day_name = day_names[today_vancouver.weekday()]
        digest_title = f"{date_str} 第{week_num}周 {day_name}"
    else:
        day_name = today_vancouver.strftime('%A')
        digest_title = f"{date_str} Week {week_num} {day_name} Digest"
    
    # Create the filename for today's digest
    filename = f"content/daily/{date_str}.md"
    
    # Remove tags from the content
    # This pattern will match hashtags and remove them
    clean_content = re.sub(r'#[a-zA-Z0-9_]+', '', content).strip()
    
    # Process content to ensure proper Markdown formatting
    # Make sure paragraphs are properly separated with double line breaks
    formatted_content = clean_content.replace("\n", "\n\n").replace("\n\n\n", "\n\n").strip()
    
    # Check if the file exists
    if os.path.exists(filename):
        # Load existing content
        with open(filename, 'r', encoding='utf-8') as f:
            existing_content = f.read()
        
        # Find the end of the front matter
        front_matter_end = existing_content.find("---\n\n") + 4
        if front_matter_end < 4:  # If the pattern wasn't found
            front_matter_end = existing_content.find("---\n") + 4
        
        # Split into front matter and content
        front_matter = existing_content[:front_matter_end]
        digest_content = existing_content[front_matter_end:]
        
        # Add the new content with timestamp in Vancouver time
        now = today_vancouver.strftime('%H:%M')
        digest_content += f"\n## {now}\n\n{formatted_content}\n\n"
        
        # Write the updated file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(front_matter)
            f.write(digest_content)
    
    else:
        # Create a new digest file
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Prepare front matter
        front_matter = {
            "title": digest_title,
            "date": today.isoformat(),
            "type": "daily",
            "draft": False
        }
        
        # Create the initial content with this entry
        now = today_vancouver.strftime('%H:%M')
        content_with_time = f"## {now}\n\n{formatted_content}\n\n"
        
        # Write the file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("---\n")
            f.write(yaml.dump(front_matter, default_flow_style=False))
            f.write("---\n\n")
            f.write(content_with_time)
    
    return {"type": "daily", "title": digest_title, "file": filename, "language": language}

def add_to_platform_queue(content, platform, message_id):
    """Add content to a specific platform queue."""
    # Load the current queues
    try:
        with open('data/queues.json', 'r', encoding='utf-8') as f:
            queues = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        queues = {"threads": [], "mastodon": [], "telegram": []}
    
    # Ensure the platform queue exists
    if platform not in queues:
        queues[platform] = []
    
    # Remove tags from content
    clean_content = re.sub(r'#[a-zA-Z0-9_]+', '', content).strip()
    
    # Prepare the post data
    post_data = {
        "text": clean_content,
        "message_id": str(message_id),
        "timestamp": datetime.now().isoformat()
    }
    
    # Add to queue
    queues[platform].append(post_data)
    
    # Save the updated queues
    with open('data/queues.json', 'w', encoding='utf-8') as f:
        json.dump(queues, f, indent=2)
    
    return f"{platform}:queued"

def process_content(message):
    """Process message content based on tags."""
    if "text" not in message:
        return None
    
    content = message["text"]
    message_id = message["message_id"]
    language = detect_language(content)
    
    try:
        # Parse the tags in the message
        tags = parse_tags(content)
        
        # Track processing results
        results = {"platforms": []}
        
        # Process based on tags
        # If #daily tag is present or no recognized tags, add to daily entry
        if 'daily' in tags or not any(tag in tags for tag in ['threads', 'mastodon']):
            daily_result = add_to_daily_entry(content, message_id, language)
            results.update(daily_result)
        
        # Process platform-specific tags
        if 'threads' in tags:
            result = add_to_platform_queue(content, "threads", message_id)
            results["platforms"].append(result)
            results["type"] = results.get("type", "sns")
        
        if 'mastodon' in tags:
            result = add_to_platform_queue(content, "mastodon", message_id)
            results["platforms"].append(result)
            results["type"] = results.get("type", "sns")
        
        return results
    except Exception as e:
        print(f"Error processing content: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_daily_entry(language="zh"):
    """Create today's digest if it doesn't exist already."""
    # Get today's date info
    today = datetime.now()
    
    # Convert to Vancouver time
    import pytz
    vancouver_tz = pytz.timezone('America/Vancouver')
    today_vancouver = datetime.now(pytz.utc).astimezone(vancouver_tz)
    
    date_str = today_vancouver.strftime('%Y-%m-%d')
    week_num = int(today_vancouver.strftime('%W')) + 1
    
    # Set language-specific parameters
    if language == "zh":
        day_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        day_name = day_names[today_vancouver.weekday()]
        digest_title = f"{date_str} 第{week_num}周 {day_name}"
        initial_content = "## 日记\n\n今天还没有记录。\n"
    else:
        day_name = today_vancouver.strftime('%A')
        digest_title = f"{date_str} Week {week_num} {day_name} Digest"
        initial_content = "## Daily Digest\n\nNo entries yet.\n"
    
    # Create the filename for today's digest
    filename = f"content/daily/{date_str}.md"
    
    # Only create if it doesn't exist
    if not os.path.exists(filename):
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        
        # Prepare front matter
        front_matter = {
            "title": digest_title,
            "date": datetime.now().isoformat(),
            "type": "daily",
            "draft": False
        }
        
        # Write the file
        with open(filename, 'w', encoding='utf-8') as f:
            f.write("---\n")
            f.write(yaml.dump(front_matter, default_flow_style=False))
            f.write("---\n\n")
            f.write(initial_content)
        
        return {"created": True, "file": filename, "language": language}
    
    return {"created": False, "language": language}
