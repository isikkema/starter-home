from fabric import Config, Connection
from paramiko.client import RejectPolicy
from paramiko.config import SSHConfig

from .files import KNOWN_HOSTS, SSH_KEY


def server_connect() -> Connection:
    ssh_config = SSHConfig.from_text(f"""
    Host 10.50.0.100
        User starter-home
        IdentityFile {SSH_KEY!s}
        IdentitiesOnly yes
        ConnectTimeout 10
    """)

    config = Config(
        ssh_config=ssh_config,
    )

    server = Connection(
        "10.50.0.100",
        config=config,
        connect_timeout=5,
    )

    if server.client is not None:
        server.client.set_missing_host_key_policy(RejectPolicy())
        server.client.load_host_keys(str(KNOWN_HOSTS))

    return server
