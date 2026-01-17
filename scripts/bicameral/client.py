#!/usr/bin/env python3
"""
Bicameral Unified Client
Works everywhere - local, remote, VPS, doesn't matter.
One API, automatic failover, bulletproof.
"""
import redis
import json
import os
import sys
import uuid
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load unified config (override=True ensures our config takes precedence)
CONFIG_FILE = Path.home() / '.bicameral' / '.env'
if CONFIG_FILE.exists():
    load_dotenv(CONFIG_FILE, override=True)
else:
    print(f"⚠️  Config file not found: {CONFIG_FILE}")
    print("Run setup first or create ~/.bicameral/.env")

# Configuration
REDIS_HOST = os.getenv('REDIS_HOST', '100.111.230.6')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'bicameral_vps_secret')
STREAM_KEY = os.getenv('STREAM_KEY', 'bicameral:stream:collab')

# Logging
LOG_FILE = Path.home() / '.bicameral' / 'client.log'
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


class BicameralClient:
    """Unified client for all Bicameral communication"""

    def __init__(self, agent_name='unknown'):
        self.agent_name = agent_name
        self.redis = self._connect_redis()

    def _connect_redis(self):
        """Connect to Redis with automatic fallback"""

        # LOCAL FIRST strategy: Try local Redis first, fallback to VPS
        # This ensures work continues even if VPS is down
        LOCAL_HOST = os.getenv('LOCAL_REDIS_HOST', 'localhost')
        LOCAL_PORT = int(os.getenv('LOCAL_REDIS_PORT', '6379'))
        LOCAL_PASSWORD = os.getenv('LOCAL_REDIS_PASSWORD', 'bicameral_secret_local')

        hosts_to_try = [
            (LOCAL_HOST, LOCAL_PORT, LOCAL_PASSWORD, 'Local Redis (PRIMARY)'),
            (REDIS_HOST, REDIS_PORT, REDIS_PASSWORD, 'VPS via Tailscale (FALLBACK)'),
        ]

        for host, port, password, description in hosts_to_try:
            try:
                r = redis.Redis(
                    host=host,
                    port=port,
                    password=password,
                    socket_connect_timeout=3,
                    socket_keepalive=True,
                    decode_responses=True
                )
                r.ping()
                logger.info(f"✅ Connected to Redis: {description} ({host}:{port})")
                print(f"✅ Connected: {description}")
                return r
            except Exception as e:
                logger.warning(f"Failed to connect to {description}: {e}")
                continue

        logger.error("❌ Could not connect to any Redis instance")
        raise ConnectionError("No Redis available. Check VPS/Tailscale connection.")

    def send(self, to_agent='all', message_type='message', content=''):
        """Send a message via Redis Streams"""

        payload = {
            'id': str(uuid.uuid4()),
            'timestamp': datetime.now().isoformat(),
            'from': self.agent_name,
            'to': to_agent,
            'type': message_type,
            'message': content
        }

        try:
            # Store in persistent stream (PERSISTENCE)
            msg_id = self.redis.xadd(STREAM_KEY, {'payload': json.dumps(payload)})

            # Publish to multiple channels for INSTANT notifications
            # 1. Global broadcast channel (for monitors, instant listeners)
            self.redis.publish('bicameral:realtime', json.dumps(payload))

            # 2. Agent-specific channel (for targeted listeners)
            channel = f'{self.agent_name}:to_{to_agent}'
            self.redis.publish(channel, json.dumps(payload))

            logger.info(f"✅ Sent [{message_type}] to {to_agent}: {content[:50]}...")
            logger.debug(f"   Stream ID: {msg_id}")
            logger.debug(f"   Published to: bicameral:realtime, {channel}")
            return msg_id

        except Exception as e:
            logger.error(f"❌ Failed to send message: {e}")
            self._save_to_fallback(payload)
            return None

    def listen(self, callback, last_id='$'):
        """Listen for new messages in real-time"""

        logger.info(f"👂 Listening for messages to {self.agent_name}...")
        current_id = last_id

        try:
            while True:
                try:
                    # Block for 1 second waiting for new messages
                    resp = self.redis.xread({STREAM_KEY: current_id}, count=10, block=1000)

                    if resp:
                        for stream_name, entries in resp:
                            for entry in entries:
                                current_id = entry[0]
                                data = entry[1]

                                # Parse payload
                                try:
                                    payload = json.loads(data.get('payload', '{}'))

                                    # Filter messages not for this agent
                                    to_agent = payload.get('to', 'all')
                                    from_agent = payload.get('from', 'unknown')

                                    if to_agent == 'all' or to_agent == self.agent_name:
                                        # Don't process own messages
                                        if from_agent != self.agent_name:
                                            callback(payload)

                                except json.JSONDecodeError:
                                    logger.warning(f"Failed to parse message: {data}")

                except redis.ConnectionError:
                    logger.error("❌ Connection lost, reconnecting...")
                    self.redis = self._connect_redis()

        except KeyboardInterrupt:
            logger.info("🛑 Listener stopped")

    def get_history(self, count=50):
        """Get recent message history"""
        try:
            entries = self.redis.xrevrange(STREAM_KEY, count=count)
            messages = []

            for entry in entries:
                stream_id, data = entry
                try:
                    payload = json.loads(data.get('payload', '{}'))
                    payload['stream_id'] = stream_id
                    messages.append(payload)
                except:
                    continue

            return messages

        except Exception as e:
            logger.error(f"Failed to get history: {e}")
            return []

    def _save_to_fallback(self, payload):
        """Save failed message to disk"""
        fallback_file = Path.home() / '.bicameral' / 'failed_messages.jsonl'
        try:
            with open(fallback_file, 'a') as f:
                f.write(json.dumps(payload) + '\n')
            logger.warning(f"💾 Message saved to fallback: {fallback_file}")
        except Exception as e:
            logger.error(f"Failed to save fallback: {e}")


# Convenience function for quick sends
def send(from_agent, message_type, content, to_agent='all'):
    """Quick send without creating client instance"""
    client = BicameralClient(agent_name=from_agent)
    return client.send(to_agent=to_agent, message_type=message_type, content=content)


if __name__ == "__main__":
    # Test the client
    if len(sys.argv) < 4:
        print("Usage: python bicameral_client.py <from_agent> <type> <message>")
        print("Example: python bicameral_client.py claude status 'System online'")
        sys.exit(1)

    from_agent = sys.argv[1]
    msg_type = sys.argv[2]
    msg_content = ' '.join(sys.argv[3:])

    send(from_agent, msg_type, msg_content)
    print(f"✅ Message sent!")
