from argparse import ArgumentParser

from . import clean, deploy


def main() -> None:
    parser = ArgumentParser(prog="starter-home")
    subparsers = parser.add_subparsers(dest="command", required=True)

    _ = subparsers.add_parser("deploy")

    clean_parser = subparsers.add_parser("clean")
    _ = clean_parser.add_argument("--delete-local-backups", action="store_true")

    args = parser.parse_args()
    match args.command:
        case "deploy":
            deploy.main()
        case "clean":
            clean.main(args.delete_local_backups)
        case s:
            parser.error(f"Unknown command: {s}")


if __name__ == "__main__":
    main()
