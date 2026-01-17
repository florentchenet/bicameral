#!/usr/bin/env python3
"""
Redis Sync Daemon - Local First with VPS Sync
Keeps local Redis and VPS Redis in sync bidirectionally
Ensures resilience: work locally even if VPS is down
"""
import redis
import json
import time
import os
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load config
CONFIG_FILE = Path.home() / '.bicameral' / '.env'
load_dotenv(CONFIG_FILE, override=True)

# Configuration
LOCAL_HOST = 'localhost'
LOCAL_PORT = 6379
LOCAL_PASSWORD = os.getenv('LOCAL_REDIS_PASSWORD', 'bicameral_secret_local')

VPS_HOST = os.getenv('REDIS_HOST', '100.111.230.6')
VPS_PORT = int(os.getenv('REDIS_PORT', '6379'))
VPS_PASSWORD = os.getenv('REDIS_PASSWORD', 'bicameral_vps_secret')

STREAM_KEY = 'bicameral:stream:collab'
SYNC_INTERVAL = 2  # seconds
SYNC_STATE_KEY = 'sync:state'

# Logging
LOG_FILE = Path.home() / '.bicameral' / 'sync_daemon.log'
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


class RedisSyncDaemon:
    """Bidirectional sync between local and VPS Redis"""

    def __init__(self):
        self.local = None
        self.vps = None
        self.local_last_id = '$'
        self.vps_last_id = '$'
        self.running = True

    def connect(self):
        """Connect to both Redis instances"""

        # Local Redis (primary)
        try:
            self.local = redis.Redis(
                host=LOCAL_HOST,
                port=LOCAL_PORT,
                password=LOCAL_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=2
            )
            self.local.ping()
            logger.info(f"✅ Connected to LOCAL Redis ({LOCAL_HOST}:{LOCAL_PORT})")
        except Exception as e:
            logger.error(f"❌ Failed to connect to LOCAL Redis: {e}")
            logger.error("   Start local Redis: docker compose up -d redis")
            return False

        # VPS Redis (sync target)
        try:
            self.vps = redis.Redis(
                host=VPS_HOST,
                port=VPS_PORT,
                password=VPS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=3
            )
            self.vps.ping()
            logger.info(f"✅ Connected to VPS Redis ({VPS_HOST}:{VPS_PORT})")
        except Exception as e:
            logger.warning(f"⚠️  VPS Redis unavailable: {e}")
            logger.info("   Operating in LOCAL-ONLY mode")
            self.vps = None

        # Load sync state
        self._load_sync_state()
        return True

    def _load_sync_state(self):
        """Load last sync positions"""
        try:
            if self.local:
                state = self.local.get(SYNC_STATE_KEY)
                if state:
                    data = json.loads(state)
                    self.local_last_id = data.get('local_last_id', '$')
                    self.vps_last_id = data.get('vps_last_id', '$')
                    logger.info(f"📍 Loaded sync state: local={self.local_last_id}, vps={self.vps_last_id}")
        except Exception as e:
            logger.warning(f"Failed to load sync state: {e}")

    def _save_sync_state(self):
        """Save sync positions"""
        try:
            if self.local:
                state = {
                    'local_last_id': self.local_last_id,
                    'vps_last_id': self.vps_last_id,
                    'last_sync': datetime.now().isoformat()
                }
                self.local.set(SYNC_STATE_KEY, json.dumps(state))
        except Exception as e:
            logger.warning(f"Failed to save sync state: {e}")

    def sync_local_to_vps(self):
        """Sync new local messages to VPS"""
        if not self.vps:
            return  # VPS unavailable

        try:
            # Read new messages from local
            entries = self.local.xread({STREAM_KEY: self.local_last_id}, count=100, block=0)

            if entries:
                for stream_name, messages in entries:
                    for msg_id, data in messages:
                        # Add to VPS
                        try:
                            # Try to add with same ID (preserve order)
                            self.vps.xadd(STREAM_KEY, data, id=msg_id)
                            logger.debug(f"→ VPS: {msg_id}")
                        except:
                            # If ID exists, just skip (already synced)
                            pass

                        # Update position
                        self.local_last_id = msg_id

                logger.info(f"↗ Synced {len(messages)} messages LOCAL → VPS")
                self._save_sync_state()

        except Exception as e:
            logger.warning(f"Sync LOCAL → VPS failed: {e}")
            # Try to reconnect VPS
            self._reconnect_vps()

    def sync_vps_to_local(self):
        """Sync new VPS messages to local"""
        if not self.vps:
            return  # VPS unavailable

        try:
            # Read new messages from VPS
            entries = self.vps.xread({STREAM_KEY: self.vps_last_id}, count=100, block=0)

            if entries:
                for stream_name, messages in entries:
                    for msg_id, data in messages:
                        # Add to local
                        try:
                            self.local.xadd(STREAM_KEY, data, id=msg_id)
                            logger.debug(f"← LOCAL: {msg_id}")
                        except:
                            # If ID exists, skip
                            pass

                        # Update position
                        self.vps_last_id = msg_id

                logger.info(f"↙ Synced {len(messages)} messages VPS → LOCAL")
                self._save_sync_state()

        except Exception as e:
            logger.warning(f"Sync VPS → LOCAL failed: {e}")
            self._reconnect_vps()

    def _reconnect_vps(self):
        """Try to reconnect to VPS"""
        if self.vps:
            return  # Already connected

        try:
            self.vps = redis.Redis(
                host=VPS_HOST,
                port=VPS_PORT,
                password=VPS_PASSWORD,
                decode_responses=True,
                socket_connect_timeout=3
            )
            self.vps.ping()
            logger.info(f"✅ Reconnected to VPS Redis")
        except:
            pass  # Still offline

    def run(self):
        """Main sync loop"""
        logger.info("🔄 Redis Sync Daemon started")
        logger.info(f"   LOCAL: {LOCAL_HOST}:{LOCAL_PORT}")
        logger.info(f"   VPS:   {VPS_HOST}:{VPS_PORT}")
        logger.info(f"   Sync interval: {SYNC_INTERVAL}s")
        logger.info("")

        if not self.connect():
            logger.error("Failed to initialize. Exiting.")
            return

        while self.running:
            try:
                # Bidirectional sync
                self.sync_local_to_vps()
                self.sync_vps_to_local()

                # Wait before next sync
                time.sleep(SYNC_INTERVAL)

            except KeyboardInterrupt:
                logger.info("\n🛑 Stopping sync daemon...")
                self.running = False
            except Exception as e:
                logger.error(f"Sync error: {e}")
                time.sleep(5)  # Wait before retry

        logger.info("✅ Sync daemon stopped")


if __name__ == "__main__":
    daemon = RedisSyncDaemon()
    daemon.run()
