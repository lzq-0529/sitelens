"""SiteLens CLI.

    python -m sitelens.manage create-owner --username me
    python -m sitelens.manage reset-password --username me
    python -m sitelens.manage seed-demo
    python -m sitelens.manage show-geo-token
    python -m sitelens.manage tick
    python -m sitelens.manage geo-agent --dry-run
"""

from __future__ import annotations

import argparse
import getpass
import json
import secrets
import sys

from sqlalchemy import select

from . import config
from . import db as db_module
from .auth import OWNER, audit, check_password_strength, create_user, hash_password
from .demo import seed_demo
from .models import User


def _password(args) -> str:
    password = args.password or getpass.getpass("密码（至少 10 位）：")
    if not args.password and password != getpass.getpass("再输入一次："):
        raise SystemExit("两次输入的密码不一致")
    return password


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m sitelens.manage")
    sub = parser.add_subparsers(dest="command", required=True)
    owner = sub.add_parser("create-owner")
    owner.add_argument("--username", required=True)
    owner.add_argument("--password", default="")
    owner.add_argument("--display-name", default="")
    reset = sub.add_parser("reset-password")
    reset.add_argument("--username", required=True)
    reset.add_argument("--password", default="")
    demo = sub.add_parser("seed-demo")
    demo.add_argument("--username", default="owner")
    demo.add_argument("--password", default="sitelens-demo")
    sub.add_parser("show-geo-token")
    sub.add_parser("show-cron-token")
    tick_cmd = sub.add_parser("tick")
    tick_cmd.add_argument("--force", action="store_true")
    geo = sub.add_parser("geo-agent")
    geo.add_argument("--base-url", default="")
    geo.add_argument("--token", default="")
    geo.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    db_module.init_db()
    with db_module.SessionLocal() as session:
        if args.command == "create-owner":
            user = create_user(session, args.username, _password(args), role=OWNER, display_name=args.display_name)
            audit(session, user, "create_owner_cli", user.username)
            from .siteconfig import load_site, save_site

            site = load_site(session)
            if not site.get("collect_token") or not site.get("hook_token"):
                save_site(
                    session,
                    {
                        "collect_token": site.get("collect_token") or "slcol_" + secrets.token_urlsafe(18),
                        "hook_token": site.get("hook_token") or "slhook_" + secrets.token_urlsafe(18),
                    },
                )
            print(f"已创建管理员：{user.username}")
        elif args.command == "reset-password":
            user = session.scalar(select(User).where(User.username == args.username))
            if user is None:
                raise SystemExit("账号不存在")
            password = _password(args)
            check_password_strength(password)
            user.password_hash = hash_password(password)
            audit(session, user, "reset_password_cli", user.username)
            print(f"已重置密码：{user.username}")
        elif args.command == "seed-demo":
            result = seed_demo(session, owner_username=args.username, owner_password=args.password)
            print(result)
        elif args.command == "tick":
            from .alerts import tick

            print(tick(session, force=args.force))
        elif args.command == "geo-agent":
            from .geo_agent import run

            token = args.token or config.geo_token()
            base = args.base_url or "http://127.0.0.1:8788"
            print(json.dumps(run(base, token, dry_run=args.dry_run), ensure_ascii=False, indent=2))
        elif args.command == "show-cron-token":
            print(config.cron_token())
        else:
            print(config.geo_token())
        session.commit()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(getattr(exc, "detail", exc), file=sys.stderr)
        raise SystemExit(1)
