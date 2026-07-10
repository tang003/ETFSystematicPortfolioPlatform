import getpass
import re
import secrets

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.security import hash_password  # noqa: E402


def main() -> None:
    username = input("管理员用户名 [admin]: ").strip() or "admin"
    if not re.fullmatch(r"[A-Za-z0-9_.-]{1,64}", username):
        raise SystemExit("用户名只能包含字母、数字、点、下划线和连字符，最多 64 位。")
    password = getpass.getpass("管理员密码（至少 12 位）: ")
    confirmation = getpass.getpass("再次输入密码: ")
    if password != confirmation:
        raise SystemExit("两次输入的密码不一致。")

    print("\n请将以下内容写入服务器 .env：")
    print("AUTH_ENABLED=true")
    print(f"AUTH_ADMIN_USERNAME={username}")
    print(f"AUTH_ADMIN_PASSWORD_HASH='{hash_password(password)}'")
    print(f"AUTH_SESSION_SECRET='{secrets.token_urlsafe(48)}'")
    print("AUTH_SESSION_TTL_HOURS=12")
    print("AUTH_COOKIE_SECURE=true")


if __name__ == "__main__":
    main()
