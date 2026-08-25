import httpx
from httpx import Client

from .config import INSTANCE

INCUS_SOCKET = "/var/lib/incus/unix.socket"

BASE_URL = "http://incus/1.0"
INSTANCE_URL = BASE_URL + "/instances"


class Instance:
    def __init__(self, state: str, ip_address: str) -> None:
        self.state: str = state
        self.ip_address: str = ip_address


def new_incus_client() -> Client:
    transport = httpx.HTTPTransport(uds=INCUS_SOCKET)
    return Client(transport=transport)


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
