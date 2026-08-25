import subprocess

import click

from .config import INSTANCE


@click.command()
def status() -> None:
    out = subprocess.run(
        ["sudo", "incus", "list", INSTANCE, "--format", "csv", "--columns", "s4"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()

    if len(out) == 0:
        state = "NOT CREATED"
        ip = "NONE"
    else:
        state, ip = out.split(",")
        ip = ip.split(" ")[0]
        if len(ip) == 0:
            ip = "NONE"

    print(f"Server:     {state}")
    print(f"IP address: {ip}")
