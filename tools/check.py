#!/usr/bin/env python3
"""check.py <issue-body-file> [--pinned <commit>] [--record <out.json>] [--hash <sha256>] [--flags <out>] [--update <out>]

Reads a Publish or an Update issue (the issue form's markdown), pins the commit (the one given, or
the repo's head now), runs the same checks a user's Store runs (aequalyn-store check
<kind> <repo> --at <commit> --market; apps get their own checks below) and prints the
report as markdown. With --record, the approved record is written too; with --flags,
why a person must read its code first, if anything; with --update, the commit in the
catalog now, when the issue updates an item. Exit 0 = pass.

An item belongs to the repository it came from, and to who submitted it or owns that
repository: nobody else's issue can take its id or update it.
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


SUBMISSIONS = Path(__file__).resolve().parent.parent / "submissions"


def same_repo(a, b):
    """one repository, however its URL is written"""
    def plain(u):
        u = re.sub(r"(\.git)?/*$", "", u.strip())
        # GitHub does not mind the case; another host may
        return u.lower() if u.lower().startswith("https://github.com/") else u
    return plain(a) == plain(b)


def github(repo):
    m = re.match(r"^https://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$", repo, re.I)
    return (m.group(1), m.group(2)) if m else None


def records(folder=SUBMISSIONS):
    out = []
    for f in sorted(Path(folder).glob("*.json")):
        out.append(json.loads(f.read_text()))
    return out


def in_catalog(kind, ident, repo, author, known):
    """(the record an issue updates, or None; why it may not, or "")"""
    if not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,63}", ident):
        return None, "Its id could not be read: lowercase letters, digits and dashes."
    mine = [r for r in known if r["kind"] == kind and (r["id"] == ident or same_repo(r["repo"], repo))]
    old = next((r for r in mine if r["id"] == ident), None)
    if old is None and mine:
        return None, f"This repository is in the catalog as `{kind}:{mine[0]['id']}`, and an id never changes: this one says `{ident}`."
    if old is None:
        return None, ""
    if not same_repo(old["repo"], repo):
        return None, f"The id `{ident}` belongs to {old['repo']}: pick another one."
    owner = github(old["repo"])
    allowed = {str(old.get("by", "")).lower()} | ({owner[0].lower()} if owner else set())
    if author.lower() not in allowed - {""}:
        return None, f"Only who published `{kind}:{ident}`, or owns its repository, can update it."
    return old, ""


def history(repo, commit, old=""):
    """(why the commit may not be used, or ""; what a reviewer must know, or "")
    A host also hands out the commits of a repository's forks: it must be on its own branch."""
    with tempfile.TemporaryDirectory() as tmp:
        r = run(["git", "clone", "-q", "--bare", "--single-branch", "--filter=tree:0", repo, tmp + "/r"],
                env=dict(os.environ, GIT_TERMINAL_PROMPT="0"))
        if r.returncode:
            return "Its history could not be read: " + (r.stderr.strip().splitlines() or ["git failed"])[-1], ""

        def before(a, b):
            return run(["git", "-C", tmp + "/r", "merge-base", "--is-ancestor", a, b],
                       env=dict(os.environ, GIT_NO_LAZY_FETCH="1")).returncode == 0
        if not before(commit, "HEAD"):
            return "That commit is not on the repository's default branch.", ""
        if not old:
            return "", ""
        if commit == old:
            return "That commit is the one in the catalog already: push the new version first.", ""
        if before(commit, old):
            return "That commit is older than the one in the catalog.", ""
        return "", "" if before(old, commit) else "its history was rewritten since the last review: read all of it"


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


def preview(kind, repo, commit):
    """the picture the Store and the site show: a file of the submission, at its commit"""
    m = re.match(r"^https://github\.com/([\w.-]+/[\w.-]+?)(?:\.git)?/?$", repo)
    if not m:
        return ""
    with tempfile.TemporaryDirectory() as tmp:
        for c in (["git", "init", "-q"], ["git", "remote", "add", "origin", repo],
                  ["git", "fetch", "-q", "--depth", "1", "origin", commit], ["git", "checkout", "-q", "FETCH_HEAD"]):
            if run(c, cwd=tmp).returncode:
                return ""
        root = Path(tmp)
        names = ["preview.png", "preview.jpg", "preview.webp", "icon.png"]
        if kind == "theme" and (root / "backgrounds").is_dir():
            names += sorted("backgrounds/" + p.name for p in (root / "backgrounds").iterdir())
        if kind == "wallpaper":
            try:
                names += [str(w["file"]) for w in json.loads((root / "index.json").read_text())]
            except Exception:
                pass
        for n in names:
            p = root / n
            if (p.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and re.match(r"^[\w./ -]+$", n) and ".." not in n
                    and p.is_file() and not p.is_symlink() and p.stat().st_size <= 8 << 20):
                return f"https://raw.githubusercontent.com/{m.group(1)}/{commit}/" + n.replace(" ", "%20")
    return ""


def main():
    args = sys.argv[1:]
    body = Path(args[0]).read_text()
    pinned = args[args.index("--pinned") + 1] if "--pinned" in args else ""
    record = args[args.index("--record") + 1] if "--record" in args else ""
    issue_hash = args[args.index("--hash") + 1] if "--hash" in args else "0" * 64
    flags = args[args.index("--flags") + 1] if "--flags" in args else ""
    update_out = args[args.index("--update") + 1] if "--update" in args else ""
    author = os.environ.get("ISSUE_AUTHOR", "")
    title_kind = re.search(r"^\[(\w+)\]", os.environ.get("ISSUE_TITLE", ""))
    kind = (os.environ.get("ISSUE_KIND") or (title_kind.group(1) if title_kind else "")).strip()
    # the Update form is one for every kind, and says which
    updating = kind == "update"
    if updating:
        kind = field(body, "Kind")
    repo = field(body, "Repository")
    commit = pinned or field(body, "Commit")
    lines = []
    ok = True
    ident, old, rewritten = "", None, ""
    known = records()
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
        if ok:
            if kind == "app":
                # an app has no manifest: its name makes its id, once
                here = next((r for r in known if r["kind"] == "app" and same_repo(r["repo"], repo)), None)
                ident = here["id"] if here else re.sub(r"[^a-z0-9-]", "-", (field(body, "Name") or Path(repo).name).lower()).strip("-")
            old, why_not = in_catalog(kind, ident, repo, author, known)
            if not why_not and updating and old is None:
                why_not = "It is not in the catalog yet: use the Publish form for its kind."
            if not why_not:
                why_not, rewritten = history(old["repo"] if old else repo, commit, old["commit"] if old else "")
            if why_not:
                ok, lines = False, lines + ["", why_not]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        commit = ""                  # the form's own text: never repeated in the line the bot reads back
    print(f"<!-- aequalyn-market pinned:{commit} issue:{issue_hash} -->")
    print(("### ✅ Passes every check" if ok else "### ❌ Does not pass") + f" at `{commit[:12] or '—'}`\n")
    # the lines quote the submission: they must not be able to leave the block
    print("```\n" + "\n".join(lines).replace("```", "\'\'\'") + "\n```")
    if ok and old:
        gh = github(old["repo"])
        print(f"\n**Update of `{kind}:{ident}`:** `{old['commit'][:12]}` → `{commit[:12]}`"
              + (f" · [what changed](https://github.com/{gh[0]}/{gh[1]}/compare/{old['commit']}...{commit})" if gh else ""))
    if update_out:
        Path(update_out).write_text(old["commit"] if ok and old else "")
    if ok:
        why = security(kind, repo, commit) + ([rewritten] if rewritten else [])
        if flags:
            Path(flags).write_text("\n".join(why))
        print("\nNext: a reviewer looks at it" + (", and at its code: " + "; ".join(why) if why else "") + ".")
    else:
        print("\nFix it and edit this issue: it is checked again at once.")
    if record and ok:
        # what an update leaves empty stays as it is; so does whose it is
        keep = old or {}
        Path(record).write_text(json.dumps({
            "id": ident, "kind": kind, "name": field(body, "Name") or keep.get("name", ""),
            "about": field(body, "About") or keep.get("about", ""),
            "license": field(body, "License") or keep.get("license", ""), "repo": keep.get("repo", repo), "commit": commit, "preview": preview(kind, repo, commit),
            "by": keep.get("by") or author, "issue": int(os.environ.get("ISSUE_NUMBER", "0") or 0),
        }, indent=2) + "\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
