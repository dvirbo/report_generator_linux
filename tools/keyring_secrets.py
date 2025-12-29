#!/usr/bin/env python
"""
Keyring secrets helper

Usage examples:
  python tools/keyring_secrets.py set db_password
  python tools/keyring_secrets.py set smtp_password --value "PlainText"
  python tools/keyring_secrets.py get db_password
  python tools/keyring_secrets.py delete db_password
"""

import argparse
import getpass
import sys

import keyring

DEFAULT_SERVICE = "report_generator"


def cmd_set(args: argparse.Namespace) -> None:
    value = args.value
    if value is None:
        prompt = f"Enter secret for {args.account}: "
        value = getpass.getpass(prompt)
    keyring.set_password(args.service, args.account, value)
    print(f"Stored secret for service='{args.service}' account='{args.account}'")


def cmd_get(args: argparse.Namespace) -> None:
    secret = keyring.get_password(args.service, args.account)
    if secret is None:
        print(f"No secret found for service='{args.service}' account='{args.account}'", file=sys.stderr)
        sys.exit(1)
    print(secret)


def cmd_delete(args: argparse.Namespace) -> None:
    keyring.delete_password(args.service, args.account)
    print(f"Deleted secret for service='{args.service}' account='{args.account}'")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage application secrets stored in the system keyring."
    )
    parser.add_argument(
        "--service",
        default=DEFAULT_SERVICE,
        help=f"Keyring service name (default: {DEFAULT_SERVICE})",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    set_cmd = sub.add_parser("set", help="Store/update a secret")
    set_cmd.add_argument("account", help="Logical account name (e.g., db_password)")
    set_cmd.add_argument("--value", help="Secret value (omit to be prompted securely)")
    set_cmd.set_defaults(func=cmd_set)

    get_cmd = sub.add_parser("get", help="Read a secret")
    get_cmd.add_argument("account", help="Logical account name")
    get_cmd.set_defaults(func=cmd_get)

    del_cmd = sub.add_parser("delete", help="Remove a secret")
    del_cmd.add_argument("account", help="Logical account name")
    del_cmd.set_defaults(func=cmd_delete)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()


