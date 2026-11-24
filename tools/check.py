#!/usr/bin/env python3
"""check.py <issue-body-file> [--pinned <commit>] [--record <out.json>] [--hash <sha256>] [--flags <out>]

Reads a Publish issue (the issue form's markdown), pins the commit (the one given, or
the repo's head now), runs the same checks a user's Store runs (aequalyn-store check
<kind> <repo> --at <commit> --market; apps get their own checks below) and prints the
report as markdown. With --record, the approved record is written too; with --flags,
why a person must read its code first, if anything. Exit 0 = pass.
"""
import json, re, subprocess, sys, tempfile, os
from pathlib import Path

KINDS = {"plugin", "theme", "cursor", "wallpaper", "look", "app"}


def field(body, label):
    m = re.search(r"### " + re.escape(label) + r"\s*\n+(.*?)(?=\n### |\Z)", body, re.S)
    v = m.group(1).strip() if m else ""
    # a field left empty: the next heading is not its value
    return "" if v == "_No response_" or v.startswith("### ") else v


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def check_app(repo, commit):
    """an app from source: a PKGBUILD that parses, pinned sources, no pipes into shells"""
    with tempfile.TemporaryDirectory() as tmp:
        for c in (["git", "init", "-q"], ["git", "remote", "add", "origin", repo],
                  ["git", "fetch", "-q", "--depth", "1", "origin", commit], ["git", "checkout", "-q", "FETCH_HEAD"]):
            r = run(c, cwd=tmp)
            if r.returncode:
                return False, f"git: {r.stderr.strip()}"
        root = Path(tmp)
        for need in ("README.md", "icon.png"):
            if not (root / need).is_file():
                return False, f"{need} is missing"
        pkgbuild = root / "PKGBUILD"
        if not pkgbuild.is_file():
            return False, "PKGBUILD is missing"
        text = pkgbuild.read_text()
        if re.search(r"\|\s*(ba|z)?sh\b|\bcurl\b[^\n]*\|", text):
            return False, "the PKGBUILD pipes something into a shell"
        if re.search(r"sha256sums=\([^)]*SKIP", text) and not re.search(r"source=\([^)]*git\+", text):
            return False, "a source without a sha256 sum (SKIP is only for git sources)"
        if run(["which", "makepkg"]).returncode == 0:
            r = run(["makepkg", "--printsrcinfo"], cwd=tmp)
            if r.returncode:
                return False, "makepkg --printsrcinfo failed:\n" + r.stderr
        return True, "PKGBUILD, sources, README.md and icon.png are in order"


def security(kind, repo, commit):
    """why a reviewer must read the code before it goes out (empty: nothing runs)"""
    if kind == "app":
        return ["it builds and runs code"]
    if kind not in ("plugin", "look"):
        return []
    with tempfile.TemporaryDirectory() as tmp:
        for c in (["git", "init", "-q"], ["git", "remote", "add", "origin", repo],
                  ["git", "fetch", "-q", "--depth", "1", "origin", commit], ["git", "checkout", "-q", "FETCH_HEAD"]):
            if run(c, cwd=tmp).returncode:
                return ["its files could not be read here"]
        root = Path(tmp)
        why = []
        files = [p for p in root.rglob("*") if p.is_file() and not p.is_symlink() and ".git" not in p.relative_to(root).parts]
        if kind == "look":
            if any(p.suffix == ".qml" for p in files):
                why.append("it ships a login screen")
            return why
        if any(p.suffix in (".sh", ".py", ".pl", ".rb") or p.read_bytes()[:2] == b"#!" or p.read_bytes()[:4] == b"\x7fELF"
               or os.access(p, os.X_OK) for p in files):
            why.append("it ships scripts or programs")
        if any(p.suffix == ".qml" and re.search(r"\bProcess\s*\{|execDetached", p.read_text(errors="replace")) for p in files):
            why.append("it starts programs")
        try:
            if json.loads((root / "plugin.json").read_text()).get("needsRoot"):
                why.append("it asks for root")
        except Exception:
            why.append("its plugin.json could not be read here")
        return why


def main():
    args = sys.argv[1:]
    body = Path(args[0]).read_text()
    pinned = args[args.index("--pinned") + 1] if "--pinned" in args else ""
    record = args[args.index("--record") + 1] if "--record" in args else ""
    issue_hash = args[args.index("--hash") + 1] if "--hash" in args else "0" * 64
    flags = args[args.index("--flags") + 1] if "--flags" in args else ""
    title_kind = re.search(r"^\[(\w+)\]", os.environ.get("ISSUE_TITLE", ""))
    kind = (os.environ.get("ISSUE_KIND") or (title_kind.group(1) if title_kind else "")).strip()
    repo = field(body, "Repository")
    commit = pinned or field(body, "Commit")
    lines = []
    ok = True
    ident = ""
    if kind not in KINDS:
        ok, lines = False, [f"Unknown kind `{kind}`."]
    elif not re.match(r"^https://[\w.-]+/[\w./-]+$", repo):
        ok, lines = False, ["The repository must be an https git URL."]
    else:
        if not commit:
            r = run(["git", "ls-remote", repo, "HEAD"])
            commit = r.stdout.split()[0] if r.returncode == 0 and r.stdout else ""
        if not re.match(r"^[0-9a-f]{40}$", commit):
            ok, lines = False, ["Could not pin a full commit id: give one in the form, or check the URL."]
        elif kind == "app":
            ok, msg = check_app(repo, commit)
            lines = [msg]
        else:
            r = run(["aequalyn-store", "check", kind, repo, "--at", commit, "--market"])
            ok = r.returncode == 0
            lines = (r.stdout + r.stderr).strip().splitlines()
            # the id the Store installs it under: the catalog must carry the same one
            m = re.search(r"^OK  " + kind + r" '([^']+)' passes", r.stdout, re.M)
            ident = m.group(1) if m else ""
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        commit = ""                  # the form's own text: never repeated in the line the bot reads back
    print(f"<!-- aequalyn-market pinned:{commit} issue:{issue_hash} -->")
    print(("### ✅ Passes every check" if ok else "### ❌ Does not pass") + f" at `{commit[:12] or '—'}`\n")
    # the lines quote the submission: they must not be able to leave the block
    print("```\n" + "\n".join(lines).replace("```", "\'\'\'") + "\n```")
    if ok:
        why = security(kind, repo, commit)
        if flags:
            Path(flags).write_text("\n".join(why))
        print("\nNext: a reviewer looks at it" + (", and at its code: " + "; ".join(why) if why else "") + ".")
    else:
        print("\nFix it and edit this issue: it is checked again at once.")
    if record and ok:
        name = field(body, "Name")
        ident = ident or re.sub(r"[^a-z0-9-]", "-", (name or Path(repo).name).lower()).strip("-")
        Path(record).write_text(json.dumps({
            "id": ident, "kind": kind, "name": name, "about": field(body, "About"),
            "license": field(body, "License"), "repo": repo, "commit": commit,
            "by": os.environ.get("ISSUE_AUTHOR", ""), "issue": int(os.environ.get("ISSUE_NUMBER", "0") or 0),
        }, indent=2) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
