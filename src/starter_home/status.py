import click

from .incus import get_instance, new_incus_client


@click.command()
def status() -> None:
    client = new_incus_client()
    instance = get_instance(client)
    if instance is None:
        print("Server:     Not deployed")
        print("IP address: None")
        return

    print(f"Server:     {instance.state}")
    print(f"IP address: {instance.ip_address}")
