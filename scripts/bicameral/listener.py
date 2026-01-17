#!/usr/bin/env python3
"""
Gemini Instant Listener - Real-Time Notifications via Redis Pub/Sub
Combines with Streams for instant alerts + persistence

INSTANT: Redis Pub/Sub (push-based, <1ms notification)
PERSISTENT: Redis Streams (pull-based, never lose messages)

This is MUCH faster than polling Streams every few seconds!
"""
import redis
import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load config
CONFIG_FILE = Path.home() / '.bicameral' / '.env'
load_dotenv(CONFIG_FILE, override=True)

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', '100.111.230.6')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'bicameral_vps_secret')
LOCAL_HOST = os.getenv('LOCAL_REDIS_HOST', 'localhost')
LOCAL_PORT = int(os.getenv('LOCAL_REDIS_PORT', '6379'))
LOCAL_PASSWORD = os.getenv('LOCAL_REDIS_PASSWORD', 'bicameral_vps_secret')

# Pub/Sub channels
PUBSUB_CHANNEL = 'bicameral:realtime'

# Logging
LOG_FILE = Path.home() / '.bicameral' / 'gemini_listener.log'
LOG_FILE.parent.mkdir(exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def notify_user(title, message):
    """Send macOS notification"""
    try:
        safe_title = title.replace('"', '\\"').replace("'", "\\'")
        safe_message = message.replace('"', '\\"').replace("'", "\\'")[:200]  # Limit length
        cmd = f'osascript -e \'display notification "{safe_message}" with title "{safe_title}"\''
        os.system(cmd)
    except Exception as e:
        logger.warning(f"Failed to send notification: {e}")


def connect_redis():
    """Connect to Redis (try local first, then VPS)"""
    hosts_to_try = [
        (LOCAL_HOST, LOCAL_PORT, LOCAL_PASSWORD, 'Local Redis'),
        (REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, 'VPS Redis'),
    ]

    for host, port, password, description in hosts_to_try:
        try:
            r = redis.Redis(
                host=host,
                port=port,
                password=password,
                decode_responses=True,
                socket_connect_timeout=3
            )
            r.ping()
            logger.info(f"✅ Connected to {description} ({host}:{port})")
            print(f"✅ Connected to {description}")
            return r
        except Exception as e:
            logger.warning(f"Failed to connect to {description}: {e}")
            continue

    logger.error("❌ Could not connect to any Redis")
    return None


def main():
    print("👂 Gemini Instant Listener - Real-Time via Pub/Sub")
    print("=" * 60)

    r = connect_redis()
    if not r:
        print("❌ No Redis available. Exiting.")
        sys.exit(1)

    pubsub = r.pubsub()
    pubsub.subscribe(PUBSUB_CHANNEL)

    print(f"📡 Listening on channel: {PUBSUB_CHANNEL}")
    print("   Waiting for messages from Claude...")
    print("   Press Ctrl+C to stop")
    print("")

    try:
        for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    payload = json.loads(message['data'])
                    from_agent = payload.get('from', 'unknown')
                    to_agent = payload.get('to', 'all')
                    msg_type = payload.get('type', 'message')
                    content = payload.get('message', '')
                    timestamp = payload.get('timestamp', '')

                    # Only notify if message is for Gemini (or all)
                    if to_agent == 'gemini' or to_agent == 'all':
                        # Don't notify about Gemini's own messages
                        if from_agent != 'gemini':
                            # Parse timestamp
                            try:
                                dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                                time_str = dt.strftime('%H:%M:%S')
                            except:
                                time_str = timestamp[:8] if timestamp else '??:??:??'

                            # Print to console
                            print(f"\n[{time_str}] 📨 {from_agent.upper()} → {msg_type.upper()}")
                            print(f"   {content}")

                            # Send macOS notification
                            notify_user(
                                f"Message from {from_agent.upper()}",
                                f"[{msg_type}] {content[:100]}"
                            )

                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse message: {message['data']}")
                except Exception as e:
                    logger.error(f"Error processing message: {e}")

    except KeyboardInterrupt:
        print("\n\n🛑 Listener stopped")
        pubsub.unsubscribe()


if __name__ == "__main__":
    main()
