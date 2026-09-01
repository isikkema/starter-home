import json
from typing import Any

import httpx
from httpx import Client

from .config import INSTANCE
from .files import ROOT

INCUS_SOCKET = "/var/lib/incus/unix.socket"

BASE_URL = "http://incus"
INSTANCE_URL = BASE_URL + "/1.0/instances"

IMAGE = "debian/13/cloud"
VM_CONFIG = ROOT / "virtual-machine" / "config.json"

SECRETS = ROOT / "secrets"
HOST_KEY = SECRETS / "ssh_host_ed25519_key"
HOST_KEY_PUBLIC = SECRETS / "ssh_host_ed25519_key.pub"
SSH_KEY = SECRETS / "id_ed25519"
SSH_KEY_PUBLIC = SECRETS / "id_ed25519.pub"


class Instance:
    def __init__(self, state: str, ip_address: str | None) -> None:
        self.state: str = state
        self.ip_address: str | None = ip_address


def new_incus_client() -> Client:
    transport = httpx.HTTPTransport(uds=INCUS_SOCKET)
    return Client(transport=transport, timeout=60)


def get_instance(client: Client) -> Instance | None:
    resp = client.get(f"{INSTANCE_URL}/{INSTANCE}/state")
    if resp.status_code == 404:
        return None

    instance_json = resp.raise_for_status().json()

    metadata = instance_json["metadata"]
    status = metadata["status"]
    ip_address = None
    network = metadata["network"]
    if network is not None:
        for iface, iface_info in network.items():
            if iface == "lo":
                continue

            for addr in iface_info["addresses"]:
                if addr["family"] == "inet":
                    ip_address = addr["address"]

    return Instance(status, ip_address)


def create_instance(client: Client) -> None:
    request_base = {
        "name": INSTANCE,
        "type": "virtual-machine",
        "start": True,
        "source": {
            "type": "image",
            "alias": IMAGE,
            "protocol": "simplestreams",
            "server": "https://images.linuxcontainers.org/",
        },
    }

    with open(VM_CONFIG, "r") as f:
        config: dict[str, Any] = json.load(f)

    host_key = ""
    for idx, line in enumerate(HOST_KEY.read_text().strip().splitlines()):
        if idx == 0:
            host_key += " " * 4 + line
        else:
            host_key += "\n" + " " * 8 + line

    cloud_init = config["config"]["cloud-init.user-data"]
    cloud_init = cloud_init.replace("${SSH_HOST_PRIVATE_KEY}", host_key)
    cloud_init = cloud_init.replace(
        "${SSH_HOST_PUBLIC_KEY}", HOST_KEY_PUBLIC.read_text().strip()
    )
    cloud_init = cloud_init.replace(
        "${SSH_PUBLIC_KEY}", SSH_KEY_PUBLIC.read_text().strip()
    )

    config["config"]["cloud-init.user-data"] = cloud_init

    data = dict(request_base, **config)
    resp = client.post(
        INSTANCE_URL,
        json=data,
    )

    _ = resp.raise_for_status()

    operation = resp.json()["operation"]

    resp = client.get(f"{BASE_URL}{operation}/wait")
    _ = resp.raise_for_status()


def start_instance(client: Client) -> None:
    resp = client.put(
        f"{INSTANCE_URL}/{INSTANCE}/state",
        json={"action": "start"},
    )

    _ = resp.raise_for_status()

    operation = resp.json()["operation"]

    resp = client.get(f"{BASE_URL}{operation}/wait")
    _ = resp.raise_for_status()


def stop_instance(client: Client, error_on_missing: bool) -> None:
    resp = client.put(
        f"{INSTANCE_URL}/{INSTANCE}/state",
        json={"action": "stop"},
    )

    if not error_on_missing and resp.status_code == 404:
        return

    _ = resp.raise_for_status()

    operation = resp.json()["operation"]

    resp = client.get(f"{BASE_URL}{operation}/wait", timeout=180)
    _ = resp.raise_for_status()


def delete_instance(client: Client) -> None:
    stop_instance(client, error_on_missing=False)

    resp = client.delete(f"{INSTANCE_URL}/{INSTANCE}")
    if resp.status_code == 404:
        return

    _ = resp.raise_for_status()
