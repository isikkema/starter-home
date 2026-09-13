import json
import sys
from pathlib import Path

import click
import dotenv
from invoke.runners import Result

from .backup_restore import restore_backup
from .files import LOCAL_BACKUP_ENV, REMOTE_BACKUP_ENV
from .server import server_connect


@click.group()
def backup() -> None:
    pass


@backup.command()
def create() -> None:
    server = server_connect()

    server.run(
        "restic cat config",
        env=get_local_backup_env(),
        hide=True,
    )

    server.run(
        "systemctl --user start local-backup.service",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
    )

    remote_backup_env = get_remote_backup_env()

    output: Result = server.run(
        "restic cat config",
        env=remote_backup_env,
        hide=True,
        warn=True,
    )

    match output.return_code:
        case 0:
            pass
        case 10:
            server.run(
                "restic init",
                env=remote_backup_env,
                hide=True,
            )
        case n:
            print(f"Failed to create remote backup:\n{output.stderr}")
            sys.exit(n)

    server.run(
        "systemctl --user start remote-backup.service",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
    )


@backup.group("list")
def list_() -> None:
    pass


@list_.command("local")
def list_local():
    local_backups = list_local_backups()

    for backup in local_backups:
        print(
            f"{backup['short_id']}  {backup['time']}  {backup['files_changed']:>3} files changed  {backup['total_files_processed']:>3} files total  {backup['data_added']:>11} B added  {backup['total_bytes_processed']:>11} B total"
        )


@list_.command("remote")
def list_remote():
    remote_backups = list_remote_backups()

    for backup in remote_backups:
        print(
            f"{backup['short_id']}  {backup['time']}  {backup['files_changed']:>3} files changed  {backup['total_files_processed']:>3} files total  {backup['data_added']:>11} B added  {backup['total_bytes_processed']:>11} B total"
        )


@backup.group()
def verify() -> None:
    pass


@verify.command("local")
def verify_local() -> None:
    server = server_connect()
    output: Result = server.run(
        "restic check --read-data",
        env=get_local_backup_env(),
        warn=True,
    )

    if output.failed:
        sys.exit(output.return_code)


@verify.command("remote")
def verify_remote() -> None:
    server = server_connect()
    output: Result = server.run(
        "restic check --read-data",
        env=get_remote_backup_env(),
        warn=True,
    )

    if output.failed:
        sys.exit(output.return_code)


@backup.group()
def restore():
    pass


@restore.command("local")
@click.argument("snapshot_id", type=str)
def restore_local(snapshot_id: str):
    server = server_connect()

    restore_dir = Path("/home/starter-home/local_restore")
    restore_backup(server, restore_dir, get_local_backup_env(), snapshot_id)


@restore.command("remote")
@click.argument("snapshot_id", type=str)
def restore_remote(snapshot_id: str):
    server = server_connect()

    restore_dir = Path("/home/starter-home/remote_restore")
    restore_backup(server, restore_dir, get_remote_backup_env(), snapshot_id)


def list_local_backups() -> list[dict[str, str]]:
    server = server_connect()
    output: Result = server.run(
        "restic snapshots --json",
        env=get_local_backup_env(),
        hide=True,
    )

    verbose_backups = json.loads(output.stdout)
    verbose_backups.sort(
        key=lambda backup: backup["time"],
    )

    backups = []
    for backup in verbose_backups:
        backups.append(
            {
                "time": backup["time"],
                "short_id": backup["short_id"],
                "files_changed": backup["summary"]["files_changed"],
                "total_files_processed": backup["summary"]["total_files_processed"],
                "data_added": backup["summary"]["data_added"],
                "total_bytes_processed": backup["summary"]["total_bytes_processed"],
            }
        )

    return backups


def list_remote_backups() -> list[dict[str, str]]:
    server = server_connect()
    output: Result = server.run(
        "restic snapshots --json",
        env=get_remote_backup_env(),
        hide=True,
    )

    verbose_backups = json.loads(output.stdout)
    verbose_backups.sort(
        key=lambda backup: backup["time"],
    )

    backups = []
    for backup in verbose_backups:
        backups.append(
            {
                "time": backup["time"],
                "short_id": backup["short_id"],
                "files_changed": backup["summary"]["files_changed"],
                "total_files_processed": backup["summary"]["total_files_processed"],
                "data_added": backup["summary"]["data_added"],
                "total_bytes_processed": backup["summary"]["total_bytes_processed"],
            }
        )

    return backups


def get_local_backup_env() -> dict[str, str | None]:
    return dotenv.dotenv_values(LOCAL_BACKUP_ENV, interpolate=False)


def get_remote_backup_env() -> dict[str, str | None]:
    return dotenv.dotenv_values(REMOTE_BACKUP_ENV, interpolate=False)
