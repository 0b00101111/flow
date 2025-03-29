# scripts/sns_manager.py
import json
import requests
import os
import logging
from datetime import datetime
import pytz

# Set up logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SNS Manager")

def post_to_mastodon(text, instance_url=None, access_token=None):
    """Post content to Mastodon."""
    if not instance_url:
        instance_url = os.environ.get('MASTODON_INSTANCE')
    if not access_token:
        access_token = os.environ.get('MASTODON_TOKEN')

    if not instance_url or not access_token:
        logger.error("Missing Mastodon credentials")
        return False, "Missing Mastodon credentials"

    # Make sure instance URL doesn't end with a slash
    if instance_url.endswith('/'):
        instance_url = instance_url[:-1]

    headers = {
        'Authorization': f'Bearer {access_token}'
    }

    data = {
        'status': text
    }

    try:
        logger.info(f"Attempting to post to Mastodon instance: {instance_url}")
        response = requests.post(
            f'{instance_url}/api/v1/statuses',
            headers=headers,
            data=data
        )

        if response.status_code == 200:
            logger.info("Successfully posted to Mastodon")
            return True, response.json()
        else:
            logger.error(f"Failed to post to Mastodon: {response.status_code} - {response.text}")
            return False, f"Status code: {response.status_code}, Response: {response.text}"
    except Exception as e:
        logger.error(f"Exception while posting to Mastodon: {str(e)}")
        return False, str(e)

def post_to_threads(text, username=None, password=None):
    """
    Post to Threads using API methods.
    Note: Threads does not have an official API yet, so this is a placeholder.
    """
    if not username:
        username = os.environ.get('THREADS_USERNAME')
    if not password:
        password = os.environ.get('THREADS_PASSWORD')

    if not username or not password:
        logger.error("Missing Threads credentials")
        return False, "Missing Threads credentials"

    # Since Threads doesn't have an official API, this is a placeholder
    # In practice, you'd need to use a third-party library or browser automation
    logger.info(f"Would post to Threads as {username}: {text[:30]}...")

    # For now, we'll simulate success
    # In a real implementation, you'd replace this with actual API calls
    return True, "Posted successfully (simulated)"

def process_sns_queues(config_path='bot_data/config.json', queues_path='bot_data/queues.json'):
    """Process social media queues based on current time windows."""
    # Load queues
    try:
        with open(queues_path, 'r') as f:
            queues = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading queues: {str(e)}")
        return False

    # Load config
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Error loading config: {str(e)}")
        return False

    # Get current time in Vancouver
    vancouver_tz = pytz.timezone('America/Vancouver')
    now = datetime.now(pytz.utc).astimezone(vancouver_tz)
    current_time = now.strftime('%H:%M')

    logger.info(f"Processing SNS queues at {current_time} (Vancouver time)")

    changes_made = False

    # Process Threads queue
    if queues.get("threads") and config.get("sns_channels", {}).get("threads", {}).get("enabled", False):
        post_windows = config["sns_channels"]["threads"]["post_windows"]
        logger.info(f"Threads post windows: {post_windows}")

        # Check if current time matches any post window (with 5-minute margin)
        should_post = False
        for window in post_windows:
            window_time = datetime.strptime(window, '%H:%M').time()
            current_time_obj = now.time()

            # Within 5 minutes of the window
            time_diff_minutes = abs((current_time_obj.hour * 60 + current_time_obj.minute) -
                                   (window_time.hour * 60 + window_time.minute))
            if time_diff_minutes <= 5:
                should_post = True
                break

        if should_post and queues["threads"]:
            logger.info("Time window matched for Threads posting")
            # Post the first item in the queue
            post = queues["threads"].pop(0)
            username = config["sns_channels"]["threads"].get("credentials", {}).get("username")
            password = config["sns_channels"]["threads"].get("credentials", {}).get("password")

            success, result = post_to_threads(post["text"], username, password)

            if success:
                logger.info(f"Posted to Threads: {post['text'][:30]}...")
                changes_made = True
            else:
                # Put it back in the queue if failed
                queues["threads"].insert(0, post)
                logger.error(f"Failed to post to Threads: {result}")

    # Process Mastodon queue
    if queues.get("mastodon") and config.get("sns_channels", {}).get("mastodon", {}).get("enabled", False):
        post_windows = config["sns_channels"]["mastodon"]["post_windows"]
        logger.info(f"Mastodon post windows: {post_windows}")

        # Check if current time matches any post window (with 5-minute margin)
        should_post = False
        for window in post_windows:
            window_time = datetime.strptime(window, '%H:%M').time()
            current_time_obj = now.time()

            # Within 5 minutes of the window
            time_diff_minutes = abs((current_time_obj.hour * 60 + current_time_obj.minute) -
                                   (window_time.hour * 60 + window_time.minute))
            if time_diff_minutes <= 5:
                should_post = True
                break

        if should_post and queues["mastodon"]:
            logger.info("Time window matched for Mastodon posting")
            # Post the first item in the queue
            post = queues["mastodon"].pop(0)
            instance = config["sns_channels"]["mastodon"].get("credentials", {}).get("instance")
            token = config["sns_channels"]["mastodon"].get("credentials", {}).get("token")

            success, result = post_to_mastodon(post["text"], instance, token)

            if success:
                logger.info(f"Posted to Mastodon: {post['text'][:30]}...")
                changes_made = True
            else:
                # Put it back in the queue if failed
                queues["mastodon"].insert(0, post)
                logger.error(f"Failed to post to Mastodon: {result}")

    # Save updated queues if changes were made
    if changes_made:
        logger.info("Saving updated queues")
        with open(queues_path, 'w') as f:
            json.dump(queues, f, indent=2)
    else:
        logger.info("No changes were made to queues")

    return changes_made

if __name__ == "__main__":
    # Test the module directly when run as script
    process_sns_queues()
