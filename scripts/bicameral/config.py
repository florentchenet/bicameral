"""
Configuration management with 1Password integration
"""
import os
import subprocess
from pathlib import Path
from dotenv import load_dotenv

CONFIG_FILE = Path.home() / '.bicameral' / '.env'

def load_config(use_1password=True):
    """Load configuration, optionally using 1Password CLI"""
    if not CONFIG_FILE.exists():
        raise FileNotFoundError(f"Config file not found: {CONFIG_FILE}")

    if use_1password and is_1password_available():
        # Use 1Password CLI to inject secrets
        load_config_with_1password()
    else:
        # Standard dotenv loading
        load_dotenv(CONFIG_FILE, override=True)

def is_1password_available():
    """Check if 1Password CLI is installed and authenticated"""
    try:
        result = subprocess.run(['op', 'account', 'get'],
                              capture_output=True, timeout=2)
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def load_config_with_1password():
    """Load config using 1Password CLI secret injection"""
    try:
        # Read .env file with op:// references
        with open(CONFIG_FILE, 'r') as f:
            env_content = f.read()

        # Inject secrets using op CLI
        result = subprocess.run(
            ['op', 'inject'],
            input=env_content.encode(),
            capture_output=True,
            timeout=10
        )

        if result.returncode == 0:
            # Parse injected env vars
            for line in result.stdout.decode().split('\n'):
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
        else:
            # Fallback to standard loading
            load_dotenv(CONFIG_FILE, override=True)
    except Exception:
        # Fallback to standard loading
        load_dotenv(CONFIG_FILE, override=True)

def get_config(key, default=None):
    """Get configuration value"""
    return os.getenv(key, default)
