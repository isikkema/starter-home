import json
import os
import subprocess
import sys

import click

from .files import ROOT

ANSIBLE_CONFIG = ROOT / "automation" / "ansible.cfg"
INVENTORY = ROOT / "automation" / "inventory" / "virtual-machine.yaml"
CREATE_BACKUP_PLAYBOOK = ROOT / "automation" / "manual-backup.yaml"
LIST_LOCAL_BACKUPS_PLAYBOOK = ROOT / "automation" / "list-local-backups.yaml"
LIST_REMOTE_BACKUPS_PLAYBOOK = ROOT / "automation" / "list-remote-backups.yaml"
VERIFY_LOCAL_BACKUPS_PLAYBOOK = ROOT / "automation" / "verify-local-backups.yaml"
VERIFY_REMOTE_BACKUPS_PLAYBOOK = ROOT / "automation" / "verify-remote-backups.yaml"
RESTORE_LOCAL_BACKUP_PLAYBOOK = ROOT / "automation" / "restore-local-backup.yaml"
RESTORE_REMOTE_BACKUP_PLAYBOOK = ROOT / "automation" / "restore-remote-backup.yaml"


@click.group()
def backup() -> None:
    pass


@backup.command()
def create() -> None:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)

    print("Creating backup")
    _ = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(CREATE_BACKUP_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        check=True,
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
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)
    env["ANSIBLE_STDOUT_CALLBACK"] = "json"

    proc = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(VERIFY_LOCAL_BACKUPS_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    ansible_out = json.loads(proc.stdout)
    restic_out = ansible_out["plays"][0]["tasks"][0]["hosts"]["starter-home"]["stdout"]
    restic_err = ansible_out["plays"][0]["tasks"][0]["hosts"]["starter-home"]["stderr"]
    restic_rc = ansible_out["plays"][0]["tasks"][0]["hosts"]["starter-home"]["rc"]
    print(restic_out)
    if proc.returncode != 0:
        print(restic_err)

    sys.exit(restic_rc)


@verify.command("remote")
def verify_remote() -> None:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)
    env["ANSIBLE_STDOUT_CALLBACK"] = "json"

    proc = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(VERIFY_REMOTE_BACKUPS_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    ansible_out = json.loads(proc.stdout)
    restic_out = ansible_out["plays"][0]["tasks"][0]["hosts"]["starter-home"]["stdout"]
    restic_err = ansible_out["plays"][0]["tasks"][0]["hosts"]["starter-home"]["stderr"]
    restic_rc = ansible_out["plays"][0]["tasks"][0]["hosts"]["starter-home"]["rc"]
    print(restic_out)
    if proc.returncode != 0:
        print(restic_err)

    if restic_rc != 0:
        sys.exit(restic_rc)


@backup.group()
def restore():
    pass


@restore.command("local")
@click.argument("snapshot_id", type=str)
def restore_local(snapshot_id: str):
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)

    _ = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(RESTORE_LOCAL_BACKUP_PLAYBOOK),
            "--extra-vars",
            f"snapshot_id={snapshot_id}",
        ],
        env=env,
        cwd=ROOT,
        check=True,
    )


@restore.command("remote")
@click.argument("snapshot_id", type=str)
def restore_remote(snapshot_id: str):
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)

    _ = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(RESTORE_REMOTE_BACKUP_PLAYBOOK),
            "--extra-vars",
            f"snapshot_id={snapshot_id}",
        ],
        env=env,
        cwd=ROOT,
        check=True,
    )


def list_local_backups() -> list[dict[str, str]]:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)
    env["ANSIBLE_STDOUT_CALLBACK"] = "json"

    proc = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(LIST_LOCAL_BACKUPS_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    out = json.loads(proc.stdout)

    for play in out["plays"]:
        for task in play["tasks"]:
            hosts = task.get("hosts")
            if hosts is None:
                continue

            for host in hosts.values():
                facts = host.get("ansible_facts")
                if facts is None:
                    continue

                backups = []
                verbose_backups = facts.get("backups")
                if verbose_backups is None:
                    continue

                verbose_backups.sort(
                    key=lambda backup: backup["time"],
                    reverse=True,
                )

                for backup in verbose_backups:
                    backups.append(
                        {
                            "time": backup["time"],
                            "short_id": backup["short_id"],
                            "files_changed": backup["summary"]["files_changed"],
                            "total_files_processed": backup["summary"][
                                "total_files_processed"
                            ],
                            "data_added": backup["summary"]["data_added"],
                            "total_bytes_processed": backup["summary"][
                                "total_bytes_processed"
                            ],
                        }
                    )

                return backups

    return []


def list_remote_backups() -> list[dict[str, str]]:
    env = os.environ.copy()
    env["ANSIBLE_CONFIG"] = str(ANSIBLE_CONFIG)
    env["ANSIBLE_STDOUT_CALLBACK"] = "json"

    proc = subprocess.run(
        [
            "ansible-playbook",
            "-i",
            str(INVENTORY),
            str(LIST_REMOTE_BACKUPS_PLAYBOOK),
        ],
        env=env,
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )

    out = json.loads(proc.stdout)

    for play in out["plays"]:
        for task in play["tasks"]:
            hosts = task.get("hosts")
            if hosts is None:
                continue

            for host in hosts.values():
                facts = host.get("ansible_facts")
                if facts is None:
                    continue

                backups = []
                verbose_backups = facts.get("backups")
                if verbose_backups is None:
                    continue

                verbose_backups.sort(
                    key=lambda backup: backup["time"],
                    reverse=True,
                )

                for backup in verbose_backups:
                    backups.append(
                        {
                            "time": backup["time"],
                            "short_id": backup["short_id"],
                            "files_changed": backup["summary"]["files_changed"],
                            "total_files_processed": backup["summary"][
                                "total_files_processed"
                            ],
                            "data_added": backup["summary"]["data_added"],
                            "total_bytes_processed": backup["summary"][
                                "total_bytes_processed"
                            ],
                        }
                    )

                return backups

    return []
