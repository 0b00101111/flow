# scripts/content_processor.py

import os
import re
import json
import yaml
from datetime import datetime
from pathlib import Path
from utils import slugify, detect_language

def parse_tags(text):
    """Extract tags from text content with support for nested tags."""
    # Regular expression to match tags: #TAG or #TAG::SUBTAG
    tag_pattern = r'#([a-zA-Z0-9_]+(?:::[a-zA-Z0-9_]+)*)'
    
    tags = {}
    matches = re.finditer(tag_pattern, text)
    
    for match in matches:
        tag_full = match.group(1)  # Without the # prefix
        
        # Split into main tag and subtags
        parts = tag_full.split('::')
        main_tag = parts[0].upper()
        
        # Process nested structure
        if main_tag not in tags:
            tags[main_tag] = []
        
        if len(parts) > 1:
            tags[main_tag].extend(parts[1:])
    
    return tags

def add_to_daily_entry(content, message_id, language="zh"):
    """Add content to the daily entry."""
    # Get today's date for the digest file
    today = datetime.now()
    
    # Convert to Vancouver time (Pacific Time)
    import pytz
    vancouver_tz = pytz.timezone('America/Vancouver')
    today_vancouver = datetime.now(pytz.utc).astimezone(vancouver_tz)
    
    date_str = today.strftime('%Y-%m-%d')
    week_num = int(today.strftime('%W')) + 1  # Get ISO week number and add 1
    
    # Day name based on language
    if language == "zh":
        day_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        day_name = day_names[today.weekday()]
        digest_title = f"{date_str} 第{week_num}周 {day_name}"
    else:
        day_name = today.strftime('%A')
        digest_title = f"{date_str} Week {week_num} {day_name} Digest"
    
    # Create the filename for today's digest
    filename = f"content/daily/{date_str}.md"
    
    # Process content to ensure proper Markdown formatting
    # Make sure paragraphs are properly separated with double line breaks
    formatted_content = content.replace("\n", "\n\n").replace("\n\n\n", "\n\n").strip()
    
    # Check if the file exists
    if os.path.exists(filename):
        # Load existing content
        with open(filename, 'r') as f:
            existing_content = f.read()
        
        # Find the end of the front matter
        front_matter_end = existing_content.find("---\n\n") + 4
        
        # Split into front matter and content
        front_matter = existing_content[:front_matter_end]
        digest_content = existing_content[front_matter_end:]
        
        # Add the new content with timestamp in Vancouver time
        now = today_vancouver.strftime('%H:%M')
        digest_content += f"\n## {now}\n\n{formatted_content}\n\n"
        
        # Write the updated file
        with open(filename, 'w') as f:
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
            "draft": false
        }
        
        # Create the initial content with this entry
        now = today_vancouver.strftime('%H:%M')
        content_with_time = f"## {now}\n\n{formatted_content}\n\n"
        
        # Write the file
        with open(filename, 'w') as f:
            f.write("---\n")
            f.write(yaml.dump(front_matter, default_flow_style=False))
            f.write("---\n\n")
            f.write(content_with_time)
    
    return {"type": "daily", "title": digest_title, "file": filename, "language": language}

def process_sns_content(content, tags, message_id):
    """Process content tagged for SNS."""
    # Determine which SNS platform(s) to use
    platforms = []
    scheduling = "queue"  # Default to queue
    
    # Check for SNS tags
    if 'SNS' in tags:
        # Add to all platforms if no specific platform is mentioned
        if not tags.get('SNS'):
            platforms = ["threads", "mastodon", "telegram"]
        else:
            # Check for specific platforms
            for subtag in tags.get('SNS', []):
                if subtag.lower() in ['threads', 'mastodon', 'telegram']:
                    platforms.append(subtag.lower())
                elif subtag.lower() in ['now', 'next']:
                    scheduling = subtag.lower()
    
    if not platforms:
        return None
    
    # Load the current queues
    try:
        with open('data/queues.json', 'r') as f:
            queues = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        queues = {"threads": [], "mastodon": [], "telegram": []}
    
    # Prepare the post data
    post_data = {
        "text": content,
        "message_id": str(message_id),
        "timestamp": datetime.now().isoformat()
    }
    
    results = []
    
    # Add to appropriate queues based on scheduling
    for platform in platforms:
        if platform not in queues:
            queues[platform] = []
        
        if scheduling == "now":
            # For "now", put at the beginning of the queue
            queues[platform].insert(0, post_data)
            results.append(f"{platform}:now")
        elif scheduling == "next":
            # For "next", put it right after the first item
            if len(queues[platform]) > 0:
                queues[platform].insert(1, post_data)
            else:
                queues[platform].append(post_data)
            results.append(f"{platform}:next")
        else:
            # Default is to append to the queue
            queues[platform].append(post_data)
            results.append(f"{platform}:queued")
    
    # Save the updated queues
    with open('data/queues.json', 'w') as f:
        json.dump(queues, f, indent=2)
    
    # Return results
    return {"type": "sns", "platforms": results}

def process_content(message):
    """Process message content based on tags or as a daily entry."""
    if "text" not in message:
        return None
    
    content = message["text"]
    message_id = message["message_id"]
    
    try:
        # Check for SNS tags
        tags = parse_tags(content)
        
        # If it has SNS tags, process for social media
        if 'SNS' in tags:
            return process_sns_content(content, tags, message_id)
        
        # Otherwise, process as a daily entry
        language = detect_language(content)
        return add_to_daily_entry(content, message_id, language)
    except Exception as e:
        print(f"Error processing content: {e}")
        return None

def create_daily_entry(language="zh"):
    """Create today's digest if it doesn't exist already."""
    # Get today's date info
    today = datetime.now()
    date_str = today.strftime('%Y-%m-%d')
    week_num = int(today.strftime('%W')) + 1
    
    # Set language-specific parameters
    if language == "zh":
        day_names = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        day_name = day_names[today.weekday()]
        digest_title = f"{date_str} 第{week_num}周 {day_name}"
        initial_content = "## 日记\n\n今天还没有记录。\n"
    else:
        day_name = today.strftime('%A')
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
        with open(filename, 'w') as f:
            f.write("---\n")
            f.write(yaml.dump(front_matter, default_flow_style=False))
            f.write("---\n\n")
            f.write(initial_content)
        
        return {"created": True, "file": filename, "language": language}
    
    return {"created": False, "language": language}
