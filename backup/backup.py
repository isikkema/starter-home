import subprocess
import sys
from pathlib import Path


def main(export_dir: Path) -> None:
    volumes = get_volumes()
    if len(volumes) == 0:
        return

    export_dir.mkdir(exist_ok=True)

    containers = get_running_containers_with_volumes()
    stop_containers(containers)

    export_volumes(export_dir, volumes)
    backup_exports(export_dir)

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


def export_volumes(export_dir: Path, volumes: list[str]) -> None:
    for volume in volumes:
        output_path = export_dir / f"{volume}.tar"

        _ = subprocess.run(
            ["podman", "volume", "export", volume, "--output", str(output_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )


def backup_exports(export_dir: Path) -> None:
    _ = subprocess.run(
        [
            "restic",
            "backup",
            ".",
        ],
        cwd=export_dir,
        check=True,
    )


if __name__ == "__main__":
    export_dir = Path(sys.argv[1]).resolve()

    main(export_dir)
