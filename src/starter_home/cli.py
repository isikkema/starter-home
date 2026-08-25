import click

from .backup import backup
from .clean import clean
from .deploy import deploy


@click.group()
def cli() -> None:
    pass


cli.add_command(backup)
cli.add_command(clean)
cli.add_command(deploy)


if __name__ == "__main__":
    cli()
