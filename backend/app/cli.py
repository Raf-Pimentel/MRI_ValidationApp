"""Admin commands: python -m app.cli init-db | load-manifest | create-rater."""

import argparse

from sqlmodel import Session

from . import service
from .config import Settings
from .db import init_db, make_engine
from .loader import load_manifest


def main() -> None:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init-db", help="create the database and tables")
    sub.add_parser("load-manifest", help="load the prepared manifest.json")
    cr = sub.add_parser("create-rater", help="create a rater and print the token")
    cr.add_argument("--name")
    cr.add_argument("--email")
    args = parser.parse_args()

    settings = Settings.from_env()
    engine = make_engine(settings.db_path)
    init_db(engine)
    with Session(engine) as session:
        if args.cmd == "init-db":
            print(f"Database ready at {settings.db_path}")
        elif args.cmd == "load-manifest":
            print(load_manifest(session, settings.prepared_dir))
        else:
            rater = service.create_rater(session, args.name, args.email)
            print(f"Token: {rater.token}")


if __name__ == "__main__":
    main()
