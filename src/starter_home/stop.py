import click

from .incus import new_incus_client, stop_instance


@click.command()
def stop() -> None:
    client = new_incus_client()
    stop_instance(client, error_on_missing=True)
