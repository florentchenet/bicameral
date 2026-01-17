"""
Bicameral Init - Interactive setup wizard for new machines
Supports multiple Redis providers: Docker, System, Upstash (cloud)
"""
import os
import subprocess
import secrets
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table

console = Console()

# Paths
BICAMERAL_DIR = Path.home() / '.bicameral'
CONFIG_FILE = BICAMERAL_DIR / '.env'
LOG_DIR = BICAMERAL_DIR / 'logs'


class RedisProvider:
    """Base class for Redis providers"""
    name = "base"

    def check_prerequisites(self) -> tuple[bool, str]:
        """Check if prerequisites are met. Returns (success, message)"""
        raise NotImplementedError

    def setup(self, config: dict) -> tuple[bool, str]:
        """Set up Redis. Returns (success, message)"""
        raise NotImplementedError

    def get_config_values(self, config: dict) -> dict:
        """Return config values for .env file"""
        raise NotImplementedError

    def test_connection(self, config: dict) -> tuple[bool, str]:
        """Test Redis connection. Returns (success, message)"""
        import redis
        try:
            r = redis.Redis(
                host=config.get('host', 'localhost'),
                port=int(config.get('port', 6379)),
                password=config.get('password', ''),
                socket_connect_timeout=5,
                decode_responses=True
            )
            r.ping()
            return True, "Connection successful"
        except Exception as e:
            return False, str(e)


class DockerRedisProvider(RedisProvider):
    """Redis via Docker container"""
    name = "docker"

    def check_prerequisites(self) -> tuple[bool, str]:
        try:
            result = subprocess.run(['docker', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                # Check if Docker daemon is running
                result = subprocess.run(['docker', 'info'], capture_output=True, timeout=10)
                if result.returncode == 0:
                    return True, "Docker is installed and running"
                return False, "Docker is installed but daemon is not running. Start Docker Desktop."
            return False, "Docker not found"
        except FileNotFoundError:
            return False, "Docker not installed. Install from https://docs.docker.com/get-docker/"
        except subprocess.TimeoutExpired:
            return False, "Docker command timed out"

    def setup(self, config: dict) -> tuple[bool, str]:
        password = config.get('password', secrets.token_urlsafe(32))
        container_name = 'bicameral-redis'

        # Check if container already exists
        result = subprocess.run(
            ['docker', 'ps', '-a', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
            capture_output=True, text=True
        )

        if container_name in result.stdout:
            # Container exists, check if running
            result = subprocess.run(
                ['docker', 'ps', '--filter', f'name={container_name}', '--format', '{{.Names}}'],
                capture_output=True, text=True
            )
            if container_name in result.stdout:
                return True, "Redis container already running"
            else:
                # Start existing container
                subprocess.run(['docker', 'start', container_name], capture_output=True)
                return True, "Started existing Redis container"

        # Create new container
        try:
            subprocess.run([
                'docker', 'run', '-d',
                '--name', container_name,
                '--restart', 'unless-stopped',
                '-p', '6379:6379',
                'redis:7-alpine',
                'redis-server', '--appendonly', 'yes', '--requirepass', password
            ], check=True, capture_output=True)

            # Wait for Redis to be ready
            import time
            for _ in range(10):
                time.sleep(1)
                success, _ = self.test_connection({'host': 'localhost', 'port': 6379, 'password': password})
                if success:
                    config['password'] = password
                    return True, "Redis container created and running"

            return False, "Container started but Redis not responding"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to create container: {e.stderr.decode() if e.stderr else str(e)}"

    def get_config_values(self, config: dict) -> dict:
        return {
            'LOCAL_REDIS_HOST': 'localhost',
            'LOCAL_REDIS_PORT': '6379',
            'LOCAL_REDIS_PASSWORD': config.get('password', ''),
            'REDIS_PROVIDER': 'docker'
        }


class SystemRedisProvider(RedisProvider):
    """Redis installed via Homebrew or system package manager"""
    name = "system"

    def check_prerequisites(self) -> tuple[bool, str]:
        # Check for redis-server
        try:
            result = subprocess.run(['which', 'redis-server'], capture_output=True)
            if result.returncode == 0:
                return True, "Redis is installed via system package manager"
        except:
            pass

        # Check for Homebrew on macOS
        try:
            result = subprocess.run(['brew', '--version'], capture_output=True, timeout=5)
            if result.returncode == 0:
                return True, "Homebrew available - can install Redis"
        except:
            pass

        return False, "Redis not found. Install with: brew install redis"

    def setup(self, config: dict) -> tuple[bool, str]:
        # Check if Redis is already installed
        result = subprocess.run(['which', 'redis-server'], capture_output=True)

        if result.returncode != 0:
            # Try to install via Homebrew
            console.print("[yellow]Installing Redis via Homebrew...[/yellow]")
            try:
                subprocess.run(['brew', 'install', 'redis'], check=True)
            except subprocess.CalledProcessError:
                return False, "Failed to install Redis via Homebrew"

        # Start Redis service
        try:
            subprocess.run(['brew', 'services', 'start', 'redis'], check=True, capture_output=True)

            # Wait for Redis
            import time
            for _ in range(5):
                time.sleep(1)
                success, _ = self.test_connection({'host': 'localhost', 'port': 6379, 'password': ''})
                if success:
                    return True, "Redis service started"

            return False, "Redis installed but not responding"
        except subprocess.CalledProcessError as e:
            return False, f"Failed to start Redis service: {e}"

    def get_config_values(self, config: dict) -> dict:
        return {
            'LOCAL_REDIS_HOST': 'localhost',
            'LOCAL_REDIS_PORT': '6379',
            'LOCAL_REDIS_PASSWORD': '',  # System Redis typically has no password
            'REDIS_PROVIDER': 'system'
        }


class UpstashRedisProvider(RedisProvider):
    """Redis via Upstash (free cloud tier)"""
    name = "upstash"

    def check_prerequisites(self) -> tuple[bool, str]:
        return True, "Upstash requires no local prerequisites"

    def setup(self, config: dict) -> tuple[bool, str]:
        # Upstash requires manual setup, we just collect credentials
        console.print("\n[bold cyan]Upstash Setup[/bold cyan]")
        console.print("1. Go to [link=https://upstash.com]https://upstash.com[/link]")
        console.print("2. Create a free account")
        console.print("3. Create a new Redis database")
        console.print("4. Copy your connection details\n")

        host = Prompt.ask("Upstash Redis Host", default="")
        if not host:
            return False, "Host is required"

        port = Prompt.ask("Upstash Redis Port", default="6379")
        password = Prompt.ask("Upstash Redis Password", password=True)

        if not password:
            return False, "Password is required for Upstash"

        config['host'] = host
        config['port'] = port
        config['password'] = password

        # Test connection
        success, msg = self.test_connection(config)
        if success:
            return True, "Connected to Upstash Redis"
        return False, f"Failed to connect: {msg}"

    def get_config_values(self, config: dict) -> dict:
        return {
            'LOCAL_REDIS_HOST': config.get('host', ''),
            'LOCAL_REDIS_PORT': config.get('port', '6379'),
            'LOCAL_REDIS_PASSWORD': config.get('password', ''),
            'REDIS_PROVIDER': 'upstash'
        }


class ExistingRedisProvider(RedisProvider):
    """Use existing Redis instance"""
    name = "existing"

    def check_prerequisites(self) -> tuple[bool, str]:
        return True, "No prerequisites needed"

    def setup(self, config: dict) -> tuple[bool, str]:
        console.print("\n[bold cyan]Existing Redis Configuration[/bold cyan]")

        host = Prompt.ask("Redis Host", default="localhost")
        port = Prompt.ask("Redis Port", default="6379")
        password = Prompt.ask("Redis Password (leave empty if none)", password=True, default="")

        config['host'] = host
        config['port'] = port
        config['password'] = password

        # Test connection
        success, msg = self.test_connection(config)
        if success:
            return True, "Connected to existing Redis"
        return False, f"Failed to connect: {msg}"

    def get_config_values(self, config: dict) -> dict:
        return {
            'LOCAL_REDIS_HOST': config.get('host', 'localhost'),
            'LOCAL_REDIS_PORT': config.get('port', '6379'),
            'LOCAL_REDIS_PASSWORD': config.get('password', ''),
            'REDIS_PROVIDER': 'existing'
        }


# Available providers
PROVIDERS = {
    'docker': DockerRedisProvider(),
    'system': SystemRedisProvider(),
    'upstash': UpstashRedisProvider(),
    'existing': ExistingRedisProvider(),
}


def check_python_version() -> bool:
    """Check Python version is 3.10+"""
    return sys.version_info >= (3, 10)


def create_directory_structure():
    """Create ~/.bicameral directory structure"""
    dirs = [
        BICAMERAL_DIR,
        LOG_DIR,
        BICAMERAL_DIR / 'bin',
        BICAMERAL_DIR / 'config',
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)
    return True


def write_config(config: dict):
    """Write configuration to .env file"""
    lines = [
        "# Bicameral Configuration",
        f"# Generated by: bicameral init",
        f"# Provider: {config.get('REDIS_PROVIDER', 'unknown')}",
        "",
        "# Local Redis (PRIMARY)",
        f"LOCAL_REDIS_HOST={config.get('LOCAL_REDIS_HOST', 'localhost')}",
        f"LOCAL_REDIS_PORT={config.get('LOCAL_REDIS_PORT', '6379')}",
        f"LOCAL_REDIS_PASSWORD={config.get('LOCAL_REDIS_PASSWORD', '')}",
        "",
        "# Redis Provider",
        f"REDIS_PROVIDER={config.get('REDIS_PROVIDER', 'docker')}",
        "",
        "# VPS Redis (SYNC TARGET - optional)",
        f"REDIS_HOST={config.get('REDIS_HOST', '')}",
        f"REDIS_PORT={config.get('REDIS_PORT', '6379')}",
        f"REDIS_PASSWORD={config.get('REDIS_PASSWORD', '')}",
        "",
        "# Stream configuration",
        f"STREAM_KEY={config.get('STREAM_KEY', 'bicameral:stream:collab')}",
    ]

    with open(CONFIG_FILE, 'w') as f:
        f.write('\n'.join(lines))

    # Secure the config file
    os.chmod(CONFIG_FILE, 0o600)


def run_init(provider_name: str = None, local_only: bool = False, force: bool = False):
    """Run the interactive init wizard"""

    console.print(Panel.fit(
        "[bold magenta]Bicameral Setup Wizard[/bold magenta]\n"
        "AI Collaboration Infrastructure",
        border_style="magenta"
    ))
    console.print()

    # Check if already configured
    if CONFIG_FILE.exists() and not force:
        console.print("[yellow]Configuration already exists at ~/.bicameral/.env[/yellow]")
        if not Confirm.ask("Overwrite existing configuration?"):
            console.print("[dim]Setup cancelled.[/dim]")
            return False

    # Step 1: Check Python version
    console.print("[bold]Step 1/4:[/bold] Checking prerequisites...")
    if not check_python_version():
        console.print(f"[red]Python 3.10+ required. Current: {sys.version_info.major}.{sys.version_info.minor}[/red]")
        return False
    console.print(f"  [green]Python {sys.version_info.major}.{sys.version_info.minor}[/green]")

    # Step 2: Create directories
    console.print("\n[bold]Step 2/4:[/bold] Creating directories...")
    create_directory_structure()
    console.print(f"  [green]Created ~/.bicameral/[/green]")

    # Step 3: Choose Redis provider
    console.print("\n[bold]Step 3/4:[/bold] Setting up Redis...")

    if provider_name is None:
        # Show provider options
        table = Table(title="Redis Provider Options")
        table.add_column("Option", style="cyan")
        table.add_column("Description")
        table.add_column("Status")

        for name, provider in PROVIDERS.items():
            success, msg = provider.check_prerequisites()
            status = "[green]Ready[/green]" if success else f"[yellow]{msg}[/yellow]"

            descriptions = {
                'docker': "Redis in Docker container (recommended)",
                'system': "Redis via Homebrew (brew install redis)",
                'upstash': "Free cloud Redis (no local install)",
                'existing': "Use your own Redis instance",
            }
            table.add_row(name, descriptions.get(name, ""), status)

        console.print(table)
        console.print()

        provider_name = Prompt.ask(
            "Choose Redis provider",
            choices=list(PROVIDERS.keys()),
            default="docker"
        )

    provider = PROVIDERS.get(provider_name)
    if not provider:
        console.print(f"[red]Unknown provider: {provider_name}[/red]")
        return False

    # Check prerequisites
    success, msg = provider.check_prerequisites()
    if not success:
        console.print(f"[red]Prerequisites not met: {msg}[/red]")
        return False

    # Setup provider
    config = {}
    success, msg = provider.setup(config)
    if not success:
        console.print(f"[red]Setup failed: {msg}[/red]")
        return False
    console.print(f"  [green]{msg}[/green]")

    # Get config values
    env_config = provider.get_config_values(config)

    # Step 4: VPS sync (optional)
    console.print("\n[bold]Step 4/4:[/bold] VPS sync configuration...")

    if local_only:
        console.print("  [dim]Skipped (local-only mode)[/dim]")
    else:
        if Confirm.ask("Configure VPS sync for remote access?", default=False):
            vps_host = Prompt.ask("VPS Redis Host (Tailscale IP)", default="")
            if vps_host:
                vps_port = Prompt.ask("VPS Redis Port", default="6379")
                vps_password = Prompt.ask("VPS Redis Password", password=True, default="")
                env_config['REDIS_HOST'] = vps_host
                env_config['REDIS_PORT'] = vps_port
                env_config['REDIS_PASSWORD'] = vps_password
                console.print("  [green]VPS sync configured[/green]")
        else:
            console.print("  [dim]Skipped[/dim]")

    # Add stream key
    env_config['STREAM_KEY'] = 'bicameral:stream:collab'

    # Write config
    write_config(env_config)
    console.print(f"\n[green]Configuration saved to {CONFIG_FILE}[/green]")

    # Test final connection
    console.print("\n[bold]Testing connection...[/bold]")
    success, msg = provider.test_connection({
        'host': env_config.get('LOCAL_REDIS_HOST', 'localhost'),
        'port': env_config.get('LOCAL_REDIS_PORT', 6379),
        'password': env_config.get('LOCAL_REDIS_PASSWORD', ''),
    })

    if success:
        console.print("[green]Redis connection successful![/green]")
    else:
        console.print(f"[yellow]Warning: Connection test failed: {msg}[/yellow]")

    # Show next steps
    console.print(Panel.fit(
        "[bold green]Setup Complete![/bold green]\n\n"
        "Next steps:\n"
        "  [cyan]bicameral status[/cyan]     - Check system status\n"
        "  [cyan]bicameral send claude message 'Hello!'[/cyan] - Send a test message\n"
        "  [cyan]bicameral monitor[/cyan]    - Start visual monitor\n"
        "  [cyan]bicameral service install[/cyan] - Install auto-start service",
        border_style="green"
    ))

    return True
