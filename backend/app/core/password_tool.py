import getpass
import sys

from app.core.security import generate_password_hash


def main() -> None:
    password = sys.argv[1] if len(sys.argv) > 1 else getpass.getpass("Owner password: ")
    if len(password) < 12:
        raise SystemExit("Use an owner password with at least 12 characters")
    print(generate_password_hash(password))


if __name__ == "__main__":
    main()
