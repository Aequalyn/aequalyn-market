#!/usr/bin/env python3
"""build_db.py -- db/market.json from every approved submission (submissions/*.json).

The version goes up by one whenever the items change; db/market.json.sha256 is written
beside it, which every Store checks before it reads the catalog.
"""
import hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent.parent
db_path = root / "db/market.json"
items = []
for f in sorted((root / "submissions").glob("*.json")):
    items.append(json.loads(f.read_text()))
items.sort(key=lambda i: (i["kind"], i["id"]))
old = json.loads(db_path.read_text()) if db_path.exists() else {"version": 0, "items": []}
if old.get("items") == items and "--force" not in sys.argv:
    print(f"db unchanged at version {old.get('version', 0)}")
    sys.exit(0)
db = {"version": int(old.get("version", 0)) + 1,
      "updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "items": items}
text = json.dumps(db, indent=2) + "\n"
db_path.write_text(text)
(root / "db/market.json.sha256").write_text(hashlib.sha256(text.encode()).hexdigest() + "  market.json\n")
print(f"db version {db['version']}: {len(items)} items")
