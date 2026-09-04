import subprocess
import sys
from pathlib import Path


def main(restore_dir: Path, snapshot_id: str) -> None:
    volumes = get_volumes()
    if len(volumes) == 0:
        return

    restore_dir.mkdir(exist_ok=True)

    restore_volumes(restore_dir, snapshot_id)

    containers = get_running_containers_with_volumes()
    stop_containers(containers)

    import_volumes(restore_dir, volumes)

    start_containers(containers)


def get_running_containers_with_volumes() -> list[str]:
    all_containers = subprocess.run(
        ["podman", "ps", "--format", "{{ .Names }}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()

    filtered_containers: list[str] = []
    for container in all_containers:
        proc = subprocess.run(
            [
                "podman",
                "container",
                "inspect",
                "--format",
                "{{ range .Mounts }}{{ .Type }} {{ end }}",
                container,
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        if "volume" in proc.stdout:
            filtered_containers.append(container)

    return filtered_containers


def stop_containers(containers: list[str]) -> None:
    _ = subprocess.run(
        ["podman", "stop"] + containers,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def start_containers(containers: list[str]) -> None:
    _ = subprocess.run(
        ["podman", "start"] + containers,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True,
    )


def get_volumes() -> list[str]:
    return subprocess.run(
        ["podman", "volume", "ls", "--format", "{{ .Name }}"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()


def import_volumes(restore_dir: Path, volumes: list[str]) -> None:
    for volume in volumes:
        import_path = restore_dir / f"{volume}.tar"

        _ = subprocess.run(
            ["podman", "volume", "import", volume, str(import_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )


def restore_volumes(restore_dir: Path, snapshot_id: str) -> None:
    _ = subprocess.run(
        ["restic", "restore", snapshot_id, "--target", str(restore_dir)],
        check=True,
    )


if __name__ == "__main__":
    snapshot_id = sys.argv[1]
    restore_dir = Path(sys.argv[2]).resolve()

    main(restore_dir, snapshot_id)
