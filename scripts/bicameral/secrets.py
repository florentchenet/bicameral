"""
1Password CLI integration for secret management
"""
import subprocess
import json

def create_1password_vault(vault_name="Bicameral"):
    """Create 1Password vault for Bicameral secrets"""
    try:
        subprocess.run(['op', 'vault', 'create', vault_name], check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def create_secret(vault, title, fields):
    """
    Create a secret in 1Password

    Args:
        vault: Vault name
        title: Item title
        fields: Dict of field_name: value
    """
    template = {
        "title": title,
        "category": "password",
        "fields": [
            {"label": k, "value": v, "type": "concealed" if "password" in k.lower() or "token" in k.lower() else "string"}
            for k, v in fields.items()
        ]
    }

    try:
        subprocess.run(
            ['op', 'item', 'create', '--vault', vault],
            input=json.dumps(template).encode(),
            check=True
        )
        return True
    except subprocess.CalledProcessError:
        return False

def get_secret(reference):
    """
    Get secret from 1Password

    Args:
        reference: op:// reference (e.g., "op://Bicameral/Local Redis/password")

    Returns:
        Secret value
    """
    try:
        result = subprocess.run(
            ['op', 'read', reference],
            capture_output=True,
            check=True,
            timeout=5
        )
        return result.stdout.decode().strip()
    except subprocess.CalledProcessError:
        return None
