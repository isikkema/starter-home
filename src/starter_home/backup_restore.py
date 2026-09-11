from pathlib import Path

from fabric.connection import Connection


def restore_backup(
    server: Connection, restore_dir: Path, env_file: Path, snapshot_id: str
) -> None:
    volumes = get_volumes(server)
    if len(volumes) == 0:
        print("No volumes to restore.")
        return

    server.run(f"mkdir -p {restore_dir!s}")

    restore_volumes(server, restore_dir, env_file, snapshot_id)

    containers = get_running_containers_with_volumes(server)
    stop_containers(server, containers)

    import_volumes(server, restore_dir, volumes)

    start_containers(server, containers)


def get_running_containers_with_volumes(server: Connection) -> list[str]:
    all_containers = server.run(
        "podman ps --format '{{ .Names }}'",
        hide=True,
    ).stdout.splitlines()

    filtered_containers: list[str] = []
    for container in all_containers:
        output = server.run(
            f"podman container inspect --format '{{ range .Mounts }}{{ .Type }} {{ end }}' {container}",
            hide=True,
        )

        if "volume" in output.stdout:
            filtered_containers.append(container)

    return filtered_containers


def stop_containers(server: Connection, containers: list[str]) -> None:
    if len(containers) == 0:
        return

    server.run(
        f"podman stop {' '.join(containers)}",
        hide=True,
    )


def start_containers(server: Connection, containers: list[str]) -> None:
    if len(containers) == 0:
        return

    server.run(
        f"podman start {' '.join(containers)}",
        hide=True,
    )


def get_volumes(server: Connection) -> list[str]:
    return server.run(
        "podman volume ls --format '{{ .Name }}'",
        hide=True,
    ).stdout.splitlines()


def import_volumes(server: Connection, restore_dir: Path, volumes: list[str]) -> None:
    for volume in volumes:
        import_path = restore_dir / f"{volume}.tar"

        server.run(
            f"podman volume import {volume} {import_path!s}",
            hide=True,
        )


def restore_volumes(
    server: Connection, restore_dir: Path, env_file: Path, snapshot_id: str
) -> None:
    server.run(
        f"""
        set -a
        . {env_file!s}
        set +a
        restic restore {snapshot_id} --target {restore_dir!s}
        """,
    )
