import json
from importlib.metadata import distribution
from pathlib import Path
from urllib.parse import unquote, urlparse


def get_root() -> Path:
    dist = distribution("starter-home")
    direct_url = None
    if dist.files is None:
        raise RuntimeError("Could not find starter-home directory")

    for file in dist.files:
        if str(file).endswith("direct_url.json"):
            direct_url = file
            break

    if direct_url is None:
        raise RuntimeError("Could not find starter-home directory")

    with open(direct_url.locate(), "r") as f:
        data = json.load(f)

    if "dir_info" not in data:
        raise RuntimeError("Not installed from a local directory")

    return Path(unquote(urlparse(data["url"]).path)).resolve()


ROOT = get_root()

BASE_CONFIG = ROOT / "virtual-machine" / "base_config.json"
CUSTOM_CONFIG = ROOT / "virtual-machine" / "custom_config.json"

HOST_STORAGE = ROOT / "host-storage"

GENERATED_CONFIG = ROOT / "virtual-machine" / "generated_config.json"

SECRETS = ROOT / "secrets"
HOST_KEY = SECRETS / "ssh_host_ed25519_key"
HOST_KEY_PUBLIC = SECRETS / "ssh_host_ed25519_key.pub"
SSH_KEY = SECRETS / "id_ed25519"
SSH_KEY_PUBLIC = SECRETS / "id_ed25519.pub"

KNOWN_HOSTS = SECRETS / "known_hosts"

SERVICES = ROOT / "services"

BACKUP = ROOT / "backup"
LOCAL_BACKUP_ENV = BACKUP / "local_backup.env"
REMOTE_BACKUP_ENV = BACKUP / "remote_backup.env"
