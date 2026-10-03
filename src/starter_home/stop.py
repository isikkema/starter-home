import click

from .backup import create_backups
from .incus import get_instance, new_incus_client, stop_instance


@click.command()
def stop() -> None:
    client = new_incus_client()
    instance = get_instance(client)
    if instance is not None and instance.state.lower() == "running":
        create_backups()

    stop_instance(client, error_on_missing=True)
