"""
Bicameral CLI
"""
import click
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from bicameral.client import BicameralClient
from bicameral.config import load_config

@click.group()
@click.version_option(version='2.0.0')
def cli():
    """🦏 Bicameral - AI Collaboration System"""
    pass

@cli.command()
@click.argument('agent')
@click.argument('message_type')
@click.argument('message')
@click.option('--to', default='all', help='Target agent')
def send(agent, message_type, message, to):
    """Send a message to another agent"""
    try:
        load_config()
        client = BicameralClient(agent_name=agent)
        client.send(to_agent=to, message_type=message_type, content=message)
        click.echo("✅ Message sent!")
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@cli.command()
def listen():
    """Start instant listener (Pub/Sub)"""
    try:
        load_config()
        from bicameral.listener import main as listener_main
        listener_main()
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@cli.command()
def monitor():
    """Start visual collaboration monitor"""
    try:
        load_config()
        from bicameral.monitor import main as monitor_main
        monitor_main()
    except Exception as e:
        click.echo(f"❌ Error: {e}", err=True)
        sys.exit(1)

@cli.command()
@click.argument('action', type=click.Choice(['start', 'stop', 'status']))
def sync(action):
    """Manage sync daemon"""
    import subprocess

    if action == 'start':
        subprocess.run(['python3', '-m', 'bicameral.sync'], check=True)
    elif action == 'stop':
        subprocess.run(['pkill', '-f', 'bicameral.sync'], check=False)
        click.echo("🛑 Sync daemon stopped")
    elif action == 'status':
        result = subprocess.run(['pgrep', '-f', 'bicameral.sync'], capture_output=True)
        if result.returncode == 0:
            click.echo(f"✅ Sync daemon running (PID: {result.stdout.decode().strip()})")
        else:
            click.echo("⚠️  Sync daemon not running")

@cli.command()
def status():
    """Check system status"""
    from bicameral.config import get_config
    import redis

    load_config()

    click.echo("🏥 Bicameral System Status")
    click.echo("")

    # Local Redis
    try:
        r = redis.Redis(
            host='localhost',
            port=6379,
            password=get_config('LOCAL_REDIS_PASSWORD'),
            decode_responses=True
        )
        r.ping()
        msg_count = r.xlen(get_config('STREAM_KEY', 'bicameral:stream:collab'))
        click.echo(f"✅ Local Redis: ONLINE ({msg_count} messages)")
    except:
        click.echo("❌ Local Redis: OFFLINE")

    # VPS Redis
    try:
        r = redis.Redis(
            host=get_config('REDIS_HOST'),
            port=int(get_config('REDIS_PORT', 6379)),
            password=get_config('REDIS_PASSWORD'),
            decode_responses=True
        )
        r.ping()
        click.echo(f"✅ VPS Redis: ONLINE")
    except:
        click.echo("⚠️  VPS Redis: OFFLINE (local-only mode)")

if __name__ == '__main__':
    cli()
