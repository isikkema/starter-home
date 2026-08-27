import click

from .incus import new_incus_client, start_instance


@click.command()
def start() -> None:
    client = new_incus_client()
    start_instance(client)
