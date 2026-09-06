import click

from .backup import backup
from .delete import delete
from .deploy import deploy
from .restart import restart
from .setup import setup
from .start import start
from .status import status
from .stop import stop


@click.group()
def cli() -> None:
    pass


cli.add_command(backup)
cli.add_command(delete)
cli.add_command(deploy)
cli.add_command(restart)
cli.add_command(setup)
cli.add_command(start)
cli.add_command(status)
cli.add_command(stop)


if __name__ == "__main__":
    cli()
