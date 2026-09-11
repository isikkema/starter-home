import json
import sys
from pathlib import Path

import click
from fabric import Config, Connection
from fabric.config import SSHConfig
from invoke.runners import Result
from paramiko.client import RejectPolicy

from .backup_restore import restore_backup
from .deploy import KNOWN_HOSTS
from .incus import SSH_KEY


@click.group()
def backup() -> None:
    pass


@backup.command()
def create() -> None:
    server = server_connect()

    server.run(
        """
        set -a
        . /home/starter-home/backup/local_backup.env
        set +a
        restic cat config
        """,
        hide=True,
    )

    server.run(
        "systemctl --user start local-backup.service",
        env={"XDG_RUNTIME_DIR": "/run/user/1000"},
    )

    output: Result = server.run(
        """
        set -a
        . /home/starter-home/backup/remote_backup.env
        set +a
        restic cat config
        """,
        hide=True,
        warn=True,
    )

    match output.return_code:
        case 0:
            pass
        case 10:
            server.run(
                """
                set -a
                . /home/starter-home/backup/remote_backup.env
                set +a
                restic init
                """,
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
        """
        set -a
        . /home/starter-home/backup/local_backup.env
        set +a
        restic check --read-data
        """,
        warn=True,
    )

    if output.failed:
        sys.exit(output.return_code)


@verify.command("remote")
def verify_remote() -> None:
    server = server_connect()
    output: Result = server.run(
        """
        set -a
        . /home/starter-home/backup/remote_backup.env
        set +a
        restic check --read-data
        """,
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
    env_file = Path("/home/starter-home/backup/local_backup.env")
    restore_backup(server, restore_dir, env_file, snapshot_id)


@restore.command("remote")
@click.argument("snapshot_id", type=str)
def restore_remote(snapshot_id: str):
    server = server_connect()

    restore_dir = Path("/home/starter-home/remote_restore")
    env_file = Path("/home/starter-home/backup/remote_backup.env")
    restore_backup(server, restore_dir, env_file, snapshot_id)


def server_connect() -> Connection:
    ssh_config = SSHConfig.from_text(f"""
    Host 10.50.0.100
        User starter-home
        IdentityFile {SSH_KEY!s}
        IdentitiesOnly yes
        ConnectTimeout 10
    """)

    config = Config(
        ssh_config=ssh_config,
    )

    server = Connection(
        "10.50.0.100",
        config=config,
    )

    if server.client is not None:
        server.client.set_missing_host_key_policy(RejectPolicy())
        server.client.load_host_keys(str(KNOWN_HOSTS))

    return server


def list_local_backups() -> list[dict[str, str]]:
    server = server_connect()
    output: Result = server.run(
        """
        set -a
        . /home/starter-home/backup/local_backup.env
        set +a
        restic snapshots --json
        """,
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
        """
        set -a
        . /home/starter-home/backup/remote_backup.env
        set +a
        restic snapshots --json
        """,
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
