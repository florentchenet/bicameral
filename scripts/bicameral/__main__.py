"""
Bicameral CLI - AI Collaboration Infrastructure
"""
import click
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


@click.group()
@click.version_option(version='2.1.0', prog_name='bicameral')
def cli():
    """Bicameral - AI Collaboration System

    Get started:

        bicameral init          Set up Bicameral on this machine

        bicameral status        Check system health

        bicameral send          Send messages between agents

        bicameral monitor       Visual collaboration monitor
    """
    pass


# =============================================================================
# INIT COMMAND
# =============================================================================

@cli.command()
@click.option('--provider', '-p',
              type=click.Choice(['docker', 'system', 'upstash', 'existing']),
              help='Redis provider to use')
@click.option('--local-only', is_flag=True, help='Skip VPS sync configuration')
@click.option('--force', '-f', is_flag=True, help='Overwrite existing configuration')
def init(provider, local_only, force):
    """Initialize Bicameral on this machine

    Sets up Redis, configuration, and directory structure.

    Examples:

        bicameral init                    # Interactive setup

        bicameral init -p docker          # Use Docker for Redis

        bicameral init -p system          # Use Homebrew Redis

        bicameral init -p upstash         # Use Upstash cloud Redis

        bicameral init --local-only       # No VPS sync
    """
    from bicameral.init import run_init
    success = run_init(provider_name=provider, local_only=local_only, force=force)
    sys.exit(0 if success else 1)


# =============================================================================
# MESSAGING COMMANDS
# =============================================================================

@cli.command()
@click.argument('agent')
@click.argument('message_type')
@click.argument('message')
@click.option('--to', default='all', help='Target agent (default: all)')
def send(agent, message_type, message, to):
    """Send a message to another agent

    Examples:

        bicameral send claude message "Hello Gemini!"

        bicameral send gemini status "Online" --to claude
    """
    try:
        from bicameral.config import load_config
        from bicameral.client import BicameralClient

        load_config()
        client = BicameralClient(agent_name=agent)
        client.send(to_agent=to, message_type=message_type, content=message)
        click.echo("Message sent!")
    except FileNotFoundError:
        click.echo("Error: Bicameral not configured. Run: bicameral init", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def listen():
    """Start instant listener (Pub/Sub)

    Listens for real-time messages via Redis Pub/Sub.
    """
    try:
        from bicameral.config import load_config
        load_config()
        from bicameral.listener import main as listener_main
        listener_main()
    except FileNotFoundError:
        click.echo("Error: Bicameral not configured. Run: bicameral init", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
def monitor():
    """Start visual collaboration monitor

    Real-time display of all messages with Rich terminal UI.
    """
    try:
        from bicameral.config import load_config
        load_config()
        from bicameral.monitor import main as monitor_main
        monitor_main()
    except FileNotFoundError:
        click.echo("Error: Bicameral not configured. Run: bicameral init", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


# =============================================================================
# SYNC COMMANDS
# =============================================================================

@cli.group()
def sync():
    """Manage sync daemon for VPS synchronization"""
    pass


@sync.command('start')
@click.option('--foreground', '-f', is_flag=True, help='Run in foreground')
def sync_start(foreground):
    """Start the sync daemon"""
    import subprocess

    if foreground:
        from bicameral.config import load_config
        load_config()
        from bicameral.sync import main as sync_main
        sync_main()
    else:
        subprocess.Popen(
            [sys.executable, '-m', 'bicameral.sync'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )
        click.echo("Sync daemon started in background")


@sync.command('stop')
def sync_stop():
    """Stop the sync daemon"""
    import subprocess
    result = subprocess.run(['pkill', '-f', 'bicameral.sync'], capture_output=True)
    if result.returncode == 0:
        click.echo("Sync daemon stopped")
    else:
        click.echo("Sync daemon was not running")


@sync.command('status')
def sync_status():
    """Check sync daemon status"""
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'bicameral.sync'], capture_output=True, text=True)
    if result.returncode == 0:
        pids = result.stdout.strip().split('\n')
        click.echo(f"Sync daemon running (PID: {', '.join(pids)})")
    else:
        click.echo("Sync daemon not running")


# =============================================================================
# SERVICE COMMANDS (macOS launchd)
# =============================================================================

@cli.group()
def service():
    """Manage auto-start services (macOS launchd)

    Install services to automatically start Bicameral components at login.
    """
    pass


@service.command('install')
@click.argument('service_name', required=False, default=None)
@click.option('--all', 'all_services', is_flag=True, help='Install all services')
def service_install(service_name, all_services):
    """Install launchd service

    Examples:

        bicameral service install sync       # Install sync daemon service

        bicameral service install --all      # Install all services
    """
    from bicameral.service import install_service, SERVICES

    if not service_name and not all_services:
        click.echo("Available services:")
        for name, svc in SERVICES.items():
            click.echo(f"  {name}: {svc['description']}")
        click.echo("\nUsage: bicameral service install <service_name>")
        click.echo("       bicameral service install --all")
        return

    install_service(service_name, all_services)


@service.command('uninstall')
@click.argument('service_name', required=False, default=None)
@click.option('--all', 'all_services', is_flag=True, help='Uninstall all services')
def service_uninstall(service_name, all_services):
    """Uninstall launchd service"""
    from bicameral.service import uninstall_service

    if not service_name and not all_services:
        click.echo("Usage: bicameral service uninstall <service_name>")
        click.echo("       bicameral service uninstall --all")
        return

    uninstall_service(service_name, all_services)


@service.command('start')
@click.argument('service_name', required=False, default=None)
@click.option('--all', 'all_services', is_flag=True, help='Start all services')
def service_start(service_name, all_services):
    """Start launchd service"""
    from bicameral.service import start_service

    if not service_name and not all_services:
        click.echo("Usage: bicameral service start <service_name>")
        click.echo("       bicameral service start --all")
        return

    start_service(service_name, all_services)


@service.command('stop')
@click.argument('service_name', required=False, default=None)
@click.option('--all', 'all_services', is_flag=True, help='Stop all services')
def service_stop(service_name, all_services):
    """Stop launchd service"""
    from bicameral.service import stop_service

    if not service_name and not all_services:
        click.echo("Usage: bicameral service stop <service_name>")
        click.echo("       bicameral service stop --all")
        return

    stop_service(service_name, all_services)


@service.command('restart')
@click.argument('service_name', required=False, default=None)
@click.option('--all', 'all_services', is_flag=True, help='Restart all services')
def service_restart(service_name, all_services):
    """Restart launchd service"""
    from bicameral.service import restart_service

    if not service_name and not all_services:
        click.echo("Usage: bicameral service restart <service_name>")
        click.echo("       bicameral service restart --all")
        return

    restart_service(service_name, all_services)


@service.command('status')
def service_status():
    """Show status of all services"""
    from bicameral.service import show_status
    show_status()


@service.command('logs')
@click.argument('service_name')
@click.option('--follow', '-f', is_flag=True, help='Follow log output')
@click.option('--lines', '-n', default=50, help='Number of lines to show')
def service_logs(service_name, follow, lines):
    """Show logs for a service

    Examples:

        bicameral service logs sync          # Show last 50 lines

        bicameral service logs sync -f       # Follow log output

        bicameral service logs sync -n 100   # Show last 100 lines
    """
    from bicameral.service import show_logs
    show_logs(service_name, follow, lines)


# =============================================================================
# STATUS COMMAND
# =============================================================================

@cli.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed status')
def status(verbose):
    """Check system health

    Shows status of Redis connections and services.
    """
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    import redis

    console = Console()

    console.print(Panel.fit(
        "[bold]Bicameral System Status[/bold]",
        border_style="blue"
    ))

    # Load config
    config_file = Path.home() / '.bicameral' / '.env'
    if not config_file.exists():
        console.print("[yellow]Not configured. Run: bicameral init[/yellow]")
        sys.exit(1)

    from bicameral.config import load_config, get_config
    load_config()

    table = Table()
    table.add_column("Component", style="cyan")
    table.add_column("Status")
    table.add_column("Details")

    # Configuration
    provider = get_config('REDIS_PROVIDER', 'unknown')
    table.add_row("Configuration", "[green]OK[/green]", f"Provider: {provider}")

    # Local Redis
    try:
        r = redis.Redis(
            host=get_config('LOCAL_REDIS_HOST', 'localhost'),
            port=int(get_config('LOCAL_REDIS_PORT', 6379)),
            password=get_config('LOCAL_REDIS_PASSWORD', ''),
            socket_connect_timeout=3,
            decode_responses=True
        )
        r.ping()
        msg_count = r.xlen(get_config('STREAM_KEY', 'bicameral:stream:collab'))
        table.add_row("Local Redis", "[green]ONLINE[/green]", f"{msg_count} messages")
    except Exception as e:
        table.add_row("Local Redis", "[red]OFFLINE[/red]", str(e)[:50])

    # VPS Redis (if configured)
    vps_host = get_config('REDIS_HOST', '')
    if vps_host:
        try:
            r = redis.Redis(
                host=vps_host,
                port=int(get_config('REDIS_PORT', 6379)),
                password=get_config('REDIS_PASSWORD', ''),
                socket_connect_timeout=3,
                decode_responses=True
            )
            r.ping()
            table.add_row("VPS Redis", "[green]ONLINE[/green]", vps_host)
        except Exception as e:
            table.add_row("VPS Redis", "[yellow]OFFLINE[/yellow]", "Local-only mode")
    else:
        table.add_row("VPS Redis", "[dim]Not configured[/dim]", "")

    # Sync daemon
    import subprocess
    result = subprocess.run(['pgrep', '-f', 'bicameral.sync'], capture_output=True, text=True)
    if result.returncode == 0:
        table.add_row("Sync Daemon", "[green]Running[/green]", f"PID: {result.stdout.strip()}")
    else:
        table.add_row("Sync Daemon", "[dim]Not running[/dim]", "")

    console.print(table)

    if verbose:
        console.print("\n[bold]Configuration:[/bold]")
        console.print(f"  Config file: {config_file}")
        console.print(f"  Log directory: {Path.home() / '.bicameral' / 'logs'}")


# =============================================================================
# DOCTOR COMMAND
# =============================================================================

@cli.command()
def doctor():
    """Diagnose and fix common issues

    Checks for common problems and suggests fixes.
    """
    from rich.console import Console
    console = Console()

    console.print("[bold]Running diagnostics...[/bold]\n")

    issues = []

    # Check config file
    config_file = Path.home() / '.bicameral' / '.env'
    if not config_file.exists():
        issues.append(("Configuration missing", "Run: bicameral init"))
    else:
        console.print("[green]Configuration file exists[/green]")

    # Check Docker (if using docker provider)
    import subprocess
    try:
        result = subprocess.run(['docker', 'info'], capture_output=True, timeout=5)
        if result.returncode != 0:
            issues.append(("Docker not running", "Start Docker Desktop"))
        else:
            console.print("[green]Docker is running[/green]")

            # Check Redis container
            result = subprocess.run(
                ['docker', 'ps', '--filter', 'name=bicameral-redis', '--format', '{{.Names}}'],
                capture_output=True, text=True
            )
            if 'bicameral-redis' not in result.stdout:
                issues.append(("Redis container not running", "Run: docker start bicameral-redis"))
            else:
                console.print("[green]Redis container is running[/green]")
    except FileNotFoundError:
        console.print("[yellow]Docker not installed (optional)[/yellow]")
    except subprocess.TimeoutExpired:
        issues.append(("Docker not responding", "Check Docker Desktop"))

    # Check Redis connection
    if config_file.exists():
        try:
            from bicameral.config import load_config, get_config
            import redis

            load_config()
            r = redis.Redis(
                host=get_config('LOCAL_REDIS_HOST', 'localhost'),
                port=int(get_config('LOCAL_REDIS_PORT', 6379)),
                password=get_config('LOCAL_REDIS_PASSWORD', ''),
                socket_connect_timeout=3,
                decode_responses=True
            )
            r.ping()
            console.print("[green]Redis connection successful[/green]")
        except Exception as e:
            issues.append(("Cannot connect to Redis", str(e)))

    # Show issues
    if issues:
        console.print("\n[bold red]Issues found:[/bold red]")
        for issue, fix in issues:
            console.print(f"  [red]- {issue}[/red]")
            console.print(f"    [yellow]Fix: {fix}[/yellow]")
    else:
        console.print("\n[bold green]All checks passed![/bold green]")


if __name__ == '__main__':
    cli()
