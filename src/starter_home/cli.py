import click

from .backup import backup
from .delete import delete
from .deploy import deploy
from .status import status


@click.group()
def cli() -> None:
    pass


cli.add_command(backup)
cli.add_command(delete)
cli.add_command(deploy)
cli.add_command(status)


if __name__ == "__main__":
    cli()
