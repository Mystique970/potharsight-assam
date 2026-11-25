"""Create or reset a PotharSight portal account with a random password.

python tools/make_user.py <username> "<Display name>" [role] [password]   (random password if omitted)
Writes the salted hash to app/users.yaml and the plain password ONLY to docs/DEMO_LOGIN.md (git-ignored).
"""
import hashlib
import os
import secrets
import string
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
uid, name = sys.argv[1].lower(), sys.argv[2]
role = sys.argv[3] if len(sys.argv) > 3 else "official"
alphabet = string.ascii_letters + string.digits
pw = sys.argv[4] if len(sys.argv) > 4 else "".join(secrets.choice(alphabet) for _ in range(10))
salt = os.urandom(16)
h = hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 200_000).hex()

f = ROOT / "app" / "users.yaml"
data = yaml.safe_load(f.read_text()) if f.exists() else {"users": {}}
data["users"][uid] = {"name": name, "role": role, "salt": salt.hex(), "hash": h}
f.write_text("# Portal accounts: salted PBKDF2-SHA256 hashes only. Create with tools/make_user.py\n" + yaml.safe_dump(data, sort_keys=False))

note = ROOT / "docs" / "DEMO_LOGIN.md"
lines = note.read_text().splitlines() if note.exists() else ["# PotharSight demo accounts (keep private; not in git)", ""]
lines = [l for l in lines if not l.startswith(f"- User ID: `{uid}`")]
lines.append(f"- User ID: `{uid}` · Password: `{pw}` · {name} ({role})")
note.write_text("\n".join(lines) + "\n")
print(f"account '{uid}' written; password saved in docs/DEMO_LOGIN.md")
