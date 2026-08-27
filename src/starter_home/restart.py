import click

from .incus import new_incus_client, start_instance, stop_instance


@click.command()
def restart() -> None:
    client = new_incus_client()
    stop_instance(client, error_on_missing=True)
    start_instance(client)
