#!/usr/bin/env python3
"""reserved.py [--shell DIR] [--themes DIR] [--out tools/reserved.json]

The ids Aequalyn's own plugins, themes, wallpapers, cursors and looks already use, per kind:
a community item may not take one (it would be installed over, or under, the built-in
one). Read from the shell's Plugins.js and style/AequalynLooks.js and from the themes
repository; without folders, straight from GitHub's main branches. The check workflow runs
it before every report; the file in git is what is used when GitHub cannot be reached.
"""
import argparse, json, re, subprocess, sys, tempfile, urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = "https://raw.githubusercontent.com/Aequalyn/{repo}/main/{path}"


def fetch(repo, path, local):
    if local:
        return (Path(local) / path).read_text()
    with urllib.request.urlopen(RAW.format(repo=repo, path=path), timeout=20) as r:
        return r.read().decode()


def theme_tree(local):
    if local:
        root = Path(local)
        return ([p.parent.name for p in (root / "themes").glob("*/theme.json")],
                [p.name for p in (root / "wallpapers").glob("*") if p.is_file()])
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["git", "clone", "-q", "--depth", "1", "--filter=blob:none", "--no-checkout",
                        "https://github.com/Aequalyn/aequalyn-themes", tmp], check=True, timeout=120)
        names = subprocess.run(["git", "-C", tmp, "ls-tree", "-r", "--name-only", "HEAD"],
                               capture_output=True, text=True, check=True).stdout.split()
    themes = [n.split("/")[1] for n in names if re.fullmatch(r"themes/[^/]+/theme\.json", n)]
    walls = [n.split("/")[1] for n in names if re.fullmatch(r"wallpapers/[^/]+", n)]
    return themes, walls


def main():
    a = argparse.ArgumentParser()
    a.add_argument("--shell")
    a.add_argument("--themes")
    a.add_argument("--out", default=str(HERE / "reserved.json"))
    o = a.parse_args()
    plugins = re.findall(r'\bid:\s*"([^"]+)"', fetch("aequalyn-shell", "Plugins.js", o.shell))
    # the ready-made looks the Store lists: the keys of the ensembles array only
    src = fetch("aequalyn-shell", "style/AequalynLooks.js", o.shell)
    m = re.search(r"var ensembles\s*=\s*\[(.*?)\n\];", src, re.S)
    looks = re.findall(r'\bkey:\s*"([^"]+)"', m.group(1)) if m else []
    themes, walls = theme_tree(o.themes)
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")
    out = {
        "plugin": sorted({slug(p) for p in plugins}),
        "theme": sorted({slug(t) for t in themes}),
        "wallpaper": sorted({slug(Path(w).stem) for w in walls}),
        "cursor": ["plume"],
        "look": sorted({slug(k) for k in looks}),
        "app": [],
    }
    Path(o.out).write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(f"reserved: {sum(len(v) for v in out.values())} ids -> {o.out}")


if __name__ == "__main__":
    sys.exit(main())
