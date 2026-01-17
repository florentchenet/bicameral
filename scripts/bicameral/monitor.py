#!/usr/bin/env python3
"""
👻 Ghosty Panel v3 (Final): Claude ↔ Gemini Collaboration Monitor
- Redis Streams (Persistent)
- Append Mode (Native Scrolling Supported!)
- Real-time updates
"""

import json
import time
import sys
import os
from datetime import datetime
from pathlib import Path
import redis
from dotenv import load_dotenv

# Try importing rich
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.box import ROUNDED
    RICH_AVAILABLE = True
except ImportError:
    print("⚠️  Install 'rich' for full UI: pip install rich")
    sys.exit(1)

# Load unified config
CONFIG_FILE = Path.home() / '.bicameral' / '.env'
if CONFIG_FILE.exists():
    load_dotenv(CONFIG_FILE, override=True)

# Configuration (from unified config)
REDIS_HOST = os.getenv('REDIS_HOST', '100.111.230.6')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', 'bicameral_vps_secret')
STREAM_KEY = os.getenv('STREAM_KEY', 'bicameral:stream:collab')

def connect_redis():
    try:
        r = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            password=REDIS_PASSWORD,
            decode_responses=True
        )
        r.ping()
        return r
    except Exception as e:
        print(f"❌ Failed to connect to Redis: {e}")
        sys.exit(1)

def parse_message(stream_entry):
    try:
        stream_id, data = stream_entry
        if 'payload' in data:
            payload = json.loads(data['payload'])
        else:
            payload = data
        payload['stream_id'] = stream_id
        return payload
    except Exception:
        return None

def print_message(console, msg):
    """Prints a single message panel to the console."""
    if not msg:
        return

    sender = msg.get('from', 'unknown')
    msg_type = msg.get('type', 'unknown')
    content = msg.get('message', '')
    timestamp = msg.get('timestamp', '')

    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        time_str = dt.strftime("%H:%M:%S")
    except:
        time_str = timestamp[:8] if timestamp else "??:??:??"

    if sender == "claude":
        border_style = "magenta"
        title = f"[magenta]👤 Claude[/] • {msg_type.upper()}"
    elif sender == "gemini":
        border_style = "blue"
        title = f"[blue]🤖 Gemini[/] • {msg_type.upper()}"
    elif sender == "daemon":
        border_style = "green"
        title = f"[green]🧠 Daemon[/] • {msg_type.upper()}"
    else:
        border_style = "white"
        title = f"⚡ {sender} • {msg_type}"

    # Render content
    if isinstance(content, str) and ('```' in content or '#' in content[:5]):
        try:
            rendered_content = Markdown(content)
        except:
            rendered_content = Text(content)
    else:
        rendered_content = Text(str(content), style="white")

    panel = Panel(
        rendered_content,
        title=f"{title} ({time_str})",
        border_style=border_style,
        box=ROUNDED,
        padding=(0, 2)
    )
    
    console.print(panel)

def main():
    console = Console()
    redis_conn = connect_redis()
    
    console.print(Panel("[bold purple]👻 Ghosty Panel v3 (Scrollable)[/]"))
    console.print("[dim]Loading history...[/]")

    # 1. Load History (Last 20 messages)
    try:
        entries = redis_conn.xrevrange(STREAM_KEY, count=20)
        entries.reverse() 
        
        last_id = '0'
        for entry in entries:
            last_id = entry[0]
            msg = parse_message(entry)
            if msg:
                print_message(console, msg)
                
    except Exception as e:
        console.print(f"[red]Error loading history: {e}[/]")
        last_id = '0'

    console.print("[dim]--- Real-time Stream Starts Here ---")

    # 2. Listen for New Messages
    while True:
        try:
            # Block for 1000ms
            resp = redis_conn.xread({STREAM_KEY: last_id}, count=1, block=1000)
            if resp:
                for _, stream_entries in resp:
                    for entry in stream_entries:
                        last_id = entry[0]
                        msg = parse_message(entry)
                        if msg:
                            print_message(console, msg)
                            
        except KeyboardInterrupt:
            console.print("\n[bold red]👋 Exiting...[/]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/]")
            time.sleep(1)

if __name__ == "__main__":
    main()