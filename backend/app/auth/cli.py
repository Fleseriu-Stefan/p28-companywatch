import sys
from getpass import GetPassWarning, getpass
from warnings import catch_warnings, simplefilter

from sqlalchemy.exc import SQLAlchemyError

from app.auth.accounts import AccountError, bootstrap_admin
from app.config import Settings
from app.db import create_database_engine


def main():
    if sys.argv[1:] != ["bootstrap-admin"] or not sys.stdin.isatty():
        print("Run bootstrap-admin in an interactive terminal.", file=sys.stderr)
        return 2
    engine = None
    try:
        email = input("Administrator email: ")
        with catch_warnings():
            simplefilter("error", GetPassWarning)
            password = getpass("Administrator password: ")
            if password != getpass("Confirm password: "):
                raise AccountError("Passwords do not match.")
        engine = create_database_engine(Settings.from_env())
        bootstrap_admin(engine, email, password)
    except AccountError as error:
        print(str(error), file=sys.stderr)
        return 2
    except (SQLAlchemyError, ValueError, EOFError, GetPassWarning, KeyboardInterrupt):
        print("Administrator bootstrap did not complete.", file=sys.stderr)
        return 2
    finally:
        if engine is not None:
            engine.dispose()
    print("Administrator created.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
