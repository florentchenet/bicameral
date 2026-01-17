"""
Bicameral Service Manager - macOS launchd integration
Manages auto-start services for sync daemon and listener
"""
import os
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Paths
LAUNCH_AGENTS_DIR = Path.home() / 'Library' / 'LaunchAgents'
BICAMERAL_DIR = Path.home() / '.bicameral'
LOG_DIR = BICAMERAL_DIR / 'logs'

# Service definitions
SERVICES = {
    'sync': {
        'label': 'com.bicameral.sync',
        'description': 'Bicameral Sync Daemon',
        'program': [sys.executable, '-m', 'bicameral.sync'],
    },
    'listener': {
        'label': 'com.bicameral.listener',
        'description': 'Bicameral Instant Listener',
        'program': [sys.executable, '-m', 'bicameral.listener'],
    },
}


def get_plist_path(service_name: str) -> Path:
    """Get the plist file path for a service"""
    label = SERVICES[service_name]['label']
    return LAUNCH_AGENTS_DIR / f'{label}.plist'


def generate_plist(service_name: str) -> str:
    """Generate launchd plist XML for a service"""
    service = SERVICES[service_name]
    label = service['label']
    program = service['program']

    # Get Python path
    python_path = sys.executable

    # Find bicameral package location
    import bicameral
    bicameral_path = Path(bicameral.__file__).parent.parent

    plist = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>{label}</string>

    <key>ProgramArguments</key>
    <array>
        <string>{python_path}</string>
        <string>-m</string>
        <string>bicameral.{service_name}</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{bicameral_path}</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>PYTHONPATH</key>
        <string>{bicameral_path}</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
    </dict>

    <key>StandardOutPath</key>
    <string>{LOG_DIR}/{service_name}.log</string>

    <key>StandardErrorPath</key>
    <string>{LOG_DIR}/{service_name}.error.log</string>

    <key>ThrottleInterval</key>
    <integer>10</integer>
</dict>
</plist>
'''
    return plist


def is_service_installed(service_name: str) -> bool:
    """Check if a service plist exists"""
    return get_plist_path(service_name).exists()


def is_service_running(service_name: str) -> bool:
    """Check if a service is currently running"""
    label = SERVICES[service_name]['label']
    result = subprocess.run(
        ['launchctl', 'list'],
        capture_output=True,
        text=True
    )
    return label in result.stdout


def get_service_pid(service_name: str) -> int | None:
    """Get the PID of a running service"""
    label = SERVICES[service_name]['label']
    result = subprocess.run(
        ['launchctl', 'list'],
        capture_output=True,
        text=True
    )
    for line in result.stdout.split('\n'):
        if label in line:
            parts = line.split('\t')
            if len(parts) >= 1 and parts[0].isdigit():
                return int(parts[0])
    return None


def install_service(service_name: str = None, all_services: bool = False) -> bool:
    """Install launchd service(s)"""

    # Ensure LaunchAgents directory exists
    LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    services_to_install = list(SERVICES.keys()) if all_services else [service_name]

    success = True
    for svc in services_to_install:
        if svc not in SERVICES:
            console.print(f"[red]Unknown service: {svc}[/red]")
            continue

        plist_path = get_plist_path(svc)
        plist_content = generate_plist(svc)

        try:
            # Write plist file
            with open(plist_path, 'w') as f:
                f.write(plist_content)

            console.print(f"[green]Installed {SERVICES[svc]['description']}[/green]")
            console.print(f"  [dim]Plist: {plist_path}[/dim]")

        except Exception as e:
            console.print(f"[red]Failed to install {svc}: {e}[/red]")
            success = False

    if success:
        console.print("\n[yellow]To start the service(s), run:[/yellow]")
        console.print("  [cyan]bicameral service start[/cyan]")

    return success


def uninstall_service(service_name: str = None, all_services: bool = False) -> bool:
    """Uninstall launchd service(s)"""

    services_to_uninstall = list(SERVICES.keys()) if all_services else [service_name]

    success = True
    for svc in services_to_uninstall:
        if svc not in SERVICES:
            console.print(f"[red]Unknown service: {svc}[/red]")
            continue

        # Stop service first if running
        if is_service_running(svc):
            stop_service(svc)

        plist_path = get_plist_path(svc)
        if plist_path.exists():
            try:
                plist_path.unlink()
                console.print(f"[green]Uninstalled {SERVICES[svc]['description']}[/green]")
            except Exception as e:
                console.print(f"[red]Failed to uninstall {svc}: {e}[/red]")
                success = False
        else:
            console.print(f"[yellow]{svc} was not installed[/yellow]")

    return success


def start_service(service_name: str = None, all_services: bool = False) -> bool:
    """Start launchd service(s)"""

    services_to_start = list(SERVICES.keys()) if all_services else [service_name]

    success = True
    for svc in services_to_start:
        if svc not in SERVICES:
            console.print(f"[red]Unknown service: {svc}[/red]")
            continue

        plist_path = get_plist_path(svc)
        if not plist_path.exists():
            console.print(f"[yellow]{svc} is not installed. Run: bicameral service install {svc}[/yellow]")
            continue

        if is_service_running(svc):
            console.print(f"[yellow]{svc} is already running[/yellow]")
            continue

        try:
            result = subprocess.run(
                ['launchctl', 'load', str(plist_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                console.print(f"[green]Started {SERVICES[svc]['description']}[/green]")
            else:
                console.print(f"[red]Failed to start {svc}: {result.stderr}[/red]")
                success = False
        except Exception as e:
            console.print(f"[red]Failed to start {svc}: {e}[/red]")
            success = False

    return success


def stop_service(service_name: str = None, all_services: bool = False) -> bool:
    """Stop launchd service(s)"""

    services_to_stop = list(SERVICES.keys()) if all_services else [service_name]

    success = True
    for svc in services_to_stop:
        if svc not in SERVICES:
            console.print(f"[red]Unknown service: {svc}[/red]")
            continue

        plist_path = get_plist_path(svc)
        if not plist_path.exists():
            console.print(f"[yellow]{svc} is not installed[/yellow]")
            continue

        if not is_service_running(svc):
            console.print(f"[yellow]{svc} is not running[/yellow]")
            continue

        try:
            result = subprocess.run(
                ['launchctl', 'unload', str(plist_path)],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                console.print(f"[green]Stopped {SERVICES[svc]['description']}[/green]")
            else:
                console.print(f"[red]Failed to stop {svc}: {result.stderr}[/red]")
                success = False
        except Exception as e:
            console.print(f"[red]Failed to stop {svc}: {e}[/red]")
            success = False

    return success


def restart_service(service_name: str = None, all_services: bool = False) -> bool:
    """Restart launchd service(s)"""
    stop_service(service_name, all_services)
    return start_service(service_name, all_services)


def show_status():
    """Show status of all services"""

    table = Table(title="Bicameral Services")
    table.add_column("Service", style="cyan")
    table.add_column("Description")
    table.add_column("Installed")
    table.add_column("Running")
    table.add_column("PID")

    for name, service in SERVICES.items():
        installed = is_service_installed(name)
        running = is_service_running(name)
        pid = get_service_pid(name) if running else None

        table.add_row(
            name,
            service['description'],
            "[green]Yes[/green]" if installed else "[dim]No[/dim]",
            "[green]Yes[/green]" if running else "[dim]No[/dim]",
            str(pid) if pid else "-"
        )

    console.print(table)

    # Show log file locations
    console.print("\n[bold]Log files:[/bold]")
    for name in SERVICES.keys():
        log_file = LOG_DIR / f'{name}.log'
        error_log = LOG_DIR / f'{name}.error.log'
        console.print(f"  {name}: {log_file}")
        if error_log.exists():
            console.print(f"  {name} (errors): {error_log}")


def show_logs(service_name: str, follow: bool = False, lines: int = 50):
    """Show logs for a service"""

    if service_name not in SERVICES:
        console.print(f"[red]Unknown service: {service_name}[/red]")
        return

    log_file = LOG_DIR / f'{service_name}.log'
    error_log = LOG_DIR / f'{service_name}.error.log'

    if not log_file.exists():
        console.print(f"[yellow]No logs found for {service_name}[/yellow]")
        return

    if follow:
        # Use tail -f
        try:
            subprocess.run(['tail', '-f', str(log_file)])
        except KeyboardInterrupt:
            pass
    else:
        # Show last N lines
        result = subprocess.run(
            ['tail', '-n', str(lines), str(log_file)],
            capture_output=True,
            text=True
        )
        console.print(f"[bold]Last {lines} lines of {log_file}:[/bold]\n")
        console.print(result.stdout)

        # Also show errors if any
        if error_log.exists() and error_log.stat().st_size > 0:
            result = subprocess.run(
                ['tail', '-n', '20', str(error_log)],
                capture_output=True,
                text=True
            )
            if result.stdout.strip():
                console.print(f"\n[bold red]Recent errors:[/bold red]\n")
                console.print(result.stdout)
