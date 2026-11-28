#!/usr/bin/env python3
"""python3 tests/test_market.py -- submissions, updates and whose they are, with the real bot.sh and
check.py on a catalog, repositories and a gh of its own; without a network."""
import json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails = 0


def ok(cond, what):
    global fails
    if not cond:
        fails += 1
        print("FAIL", what)


GH = r'''#!/usr/bin/env python3
import json, os, sys
p = os.environ["ISSUE_FILE"]; i = json.load(open(p)); a = sys.argv[1:]
def arg(n): return a[a.index(n) + 1] if n in a else ""
if a[:2] == ["issue", "view"]:
    what = arg("--json")
    if what == "labels": print("\n".join(i["labels"]))
    elif what == "author": print(i["author"])
    else: print(i[what])
elif a[:2] == ["issue", "edit"]:
    if arg("--add-label") and arg("--add-label") not in i["labels"]: i["labels"].append(arg("--add-label"))
    if arg("--remove-label") in i["labels"]: i["labels"].remove(arg("--remove-label"))
elif a[:2] == ["issue", "comment"]:
    i["comments"].append(arg("--body") or open(arg("--body-file")).read())
elif a[:2] == ["issue", "close"]: i["state"] = "closed"
elif a[0] == "api" and "/permission" in a[1]: print("write" if "reviewer" in a[1] else "read")
elif a[0] == "api":
    print("\n".join(c.split("\n")[0] for c in i["comments"]))
json.dump(i, open(p, "w"))
'''
STORE = '''#!/bin/sh
# check <kind> <repo> --at <commit> --market: passes, with the id its repository says
cd "$(mktemp -d)" && git init -q && git fetch -q "$3" "$5" 2>/dev/null && id=$(git show FETCH_HEAD:id) || exit 1
echo "OK  $2 '$id' passes every check at $5"
'''

with tempfile.TemporaryDirectory() as tmp:
    tmp = pathlib.Path(tmp)
    (tmp / "bin").mkdir()
    for n, t in (("gh", GH), ("aequalyn-store", STORE)):
        (tmp / "bin" / n).write_text(t)
        (tmp / "bin" / n).chmod(0o755)
    conf = tmp / "gitconfig"
    conf.write_text(f'[user]\nname = t\nemail = t@t\n[init]\ndefaultBranch = main\n[url "file://{tmp}/hub/"]\ninsteadOf = https://github.com/\n'
                    '[uploadpack]\nallowFilter = true\nallowAnySHA1InWant = true\n[protocol "file"]\nallow = always\n')
    env = dict(os.environ, HOME=str(tmp), GIT_CONFIG_GLOBAL=str(conf), GIT_CONFIG_NOSYSTEM="1", REPO="x/market",
               PATH=f"{tmp}/bin:" + os.environ["PATH"], PYTHONDONTWRITEBYTECODE="1", ISSUE_FILE=str(tmp / "issue.json"))

    def git(where, *a):
        r = subprocess.run(["git", "-C", str(where), *a], env=env, capture_output=True, text=True)
        assert r.returncode == 0, (a, r.stderr)
        return r.stdout.strip()

    def repo(name, ident):
        d = tmp / "hub" / name
        d.mkdir(parents=True)
        git(d, "init", "-q")
        (d / "id").write_text(ident)
        return d, push(d, "one")

    def push(d, text):
        (d / "file").write_text(text)
        git(d, "add", "-A")
        git(d, "commit", "-qm", text)
        return git(d, "rev-parse", "HEAD")

    market = tmp / "market"
    market.mkdir()
    for n in ("tools", "db", "submissions"):
        shutil.copytree(ROOT / n, market / n)
    for f in (market / "submissions").glob("*.json"):
        f.unlink()
    git(market, "init", "-q")
    git(market, "add", "-A")
    git(market, "commit", "-qm", "start")
    git(tmp, "clone", "-q", "--bare", str(market), str(tmp / "market.git"))
    git(market, "remote", "add", "origin", str(tmp / "market.git"))

    def form(**f):
        return "\n\n".join(f"### {k}\n\n{v or '_No response_'}" for k, v in f.items())

    def issue(title, author, body, approve=True):
        """what the bot makes of an issue: (its labels, its state, what it said)"""
        pathlib.Path(env["ISSUE_FILE"]).write_text(json.dumps({"title": title, "author": author, "body": body, "state": "open",
                                                               "labels": ["submission"], "comments": []}))
        bot("check", "7")
        i = json.loads(pathlib.Path(env["ISSUE_FILE"]).read_text())
        first = list(i["labels"])
        if approve:
            i["labels"] = [x for x in i["labels"] if x != "security-review"] + ["approved"]
            pathlib.Path(env["ISSUE_FILE"]).write_text(json.dumps(i))
            bot("review", "7", "approved", "reviewer")
            i = json.loads(pathlib.Path(env["ISSUE_FILE"]).read_text())
        return first, i["state"], "\n".join(i["comments"])

    def bot(*a):
        r = subprocess.run(["bash", "tools/bot.sh", *a], cwd=market, env=env, capture_output=True, text=True)
        ok(r.returncode == 0, f"bot {a}: {r.stderr[-300:]}")

    def catalog():
        text = git(tmp / "market.git", "show", "main:db/market.json")
        return {f"{i['kind']}:{i['id']}": i for i in json.loads(text)["items"]}

    d, c1 = repo("ann/aequalyn-plugin-one", "one")
    url = "https://github.com/ann/aequalyn-plugin-one"
    labels, state, said = issue("[plugin] One", "ann", form(Repository=url, Commit="", Name="One", About="First", License="MIT"))
    ok("needs-review" in labels and "update" not in labels, f"a new item: {labels} {said}")
    ok(state == "closed" and catalog()["plugin:one"]["commit"] == c1, f"approved: {said}")

    labels, state, said = issue("[plugin] One", "ann", form(Repository=url, Commit="", Name="One", About="First", License="MIT"))
    ok("changes-requested" in labels and "already" in said and state == "open", f"nothing new: {labels}")

    c2 = push(d, "two")
    ok(catalog()["plugin:one"]["commit"] == c1, "a push alone changes nothing")
    labels, state, said = issue("[update] One", "ann", form(Kind="plugin", Repository=url + "/", Commit="", **{"What changed": "x"}, Name="", About="", License=""))
    ok("update" in labels and "needs-review" in labels, f"an update: {labels} {said}")
    ok(f"compare/{c1}...{c2}" in said and "every Store offers it" in said, f"what changed is linked: {said}")
    r = catalog()["plugin:one"]
    ok((r["commit"], r["name"], r["about"], r["license"], r["by"], r["repo"]) == (c2, "One", "First", "MIT", "ann", url), f"the record: {r}")

    labels, state, said = issue("[update] One", "ann", form(Kind="plugin", Repository=url, Commit=c1, **{"What changed": "x"}))
    ok("changes-requested" in labels and "older" in said, f"an older commit: {labels}")

    c3 = push(d, "three")
    labels, state, said = issue("[update] One", "mallory", form(Kind="plugin", Repository=url, Commit="", **{"What changed": "x"}))
    ok("changes-requested" in labels and "can update it" in said and state == "open", f"someone else: {labels}")
    ok("update" not in labels, "a refused update is no update")

    repo("mallory/aequalyn-plugin-one", "one")
    labels, state, said = issue("[plugin] One", "mallory", form(Repository="https://github.com/mallory/aequalyn-plugin-one", Commit="", Name="One", About="Mine", License="MIT"))
    ok("changes-requested" in labels and "belongs to" in said and state == "open", f"its id from another repo: {labels}")
    labels, state, said = issue("[update] One", "mallory", form(Kind="plugin", Repository="https://github.com/mallory/aequalyn-plugin-one", Commit="", **{"What changed": "x"}))
    ok("belongs to" in said and catalog()["plugin:one"]["commit"] == c2, "nor as an update")
    repo("mallory/aequalyn-theme-one", "one")
    labels, state, said = issue("[theme] One", "mallory", form(Repository="https://github.com/mallory/aequalyn-theme-one", Commit="", Name="One", About="x", License="MIT"))
    ok(state == "closed" and "theme:one" in catalog(), f"another kind may share the name: {said}")

    # a fork's commit, served through the original
    git(d, "checkout", "-qb", "fork")
    evil = push(d, "evil")
    git(d, "checkout", "-q", "main")
    for who, c in (("ann", evil),):
        labels, state, said = issue("[update] One", who, form(Kind="plugin", Repository=url, Commit=c, **{"What changed": "x"}))
        ok("changes-requested" in labels and "default branch" in said, f"a commit off the branch: {labels}")

    (d / "id").write_text("two")
    c4 = push(d, "renamed")
    labels, state, said = issue("[update] One", "ann", form(Kind="plugin", Repository=url, Commit="", **{"What changed": "x"}))
    ok("changes-requested" in labels and "never changes" in said, f"a new id: {labels}")
    (d / "id").write_text("../x")
    push(d, "odd")
    labels, state, said = issue("[plugin] X", "ann", form(Repository=url, Commit="", Name="X", About="x", License="MIT"))
    ok("changes-requested" in labels, "an odd id")

    git(d, "checkout", "-q", "--orphan", "fresh")
    (d / "id").write_text("one")
    c5 = push(d, "rewritten")
    git(d, "branch", "-qf", "main", "fresh")
    git(d, "checkout", "-q", "main")
    labels, state, said = issue("[update] One", "ann", form(Kind="plugin", Repository=url, Commit="", **{"What changed": "x"}))
    ok("security-review" in labels and "rewritten" in said and catalog()["plugin:one"]["commit"] == c5, f"rewritten history: {labels} {said}")

    repo("ann/aequalyn-plugin-new", "new")
    labels, state, said = issue("[update] New", "ann", form(Kind="plugin", Repository="https://github.com/ann/aequalyn-plugin-new", Commit="", **{"What changed": "x"}))
    ok("changes-requested" in labels and "Publish form" in said, f"an update of nothing: {labels}")
    labels, state, said = issue("[update] New", "ann", form(Kind="nope", Repository="https://github.com/ann/aequalyn-plugin-new", Commit=""))
    ok("changes-requested" in labels and "Unknown kind" in said, "an unknown kind")
    labels, state, said = issue("[plugin] Bad", "ann", "nothing at all")
    ok("changes-requested" in labels, "an empty issue")

    # an app: its id is made from its name once, and stays when the name changes
    a, _ = repo("ann/aequalyn-app-my-app", "x")
    (a / "README.md").write_text("x"); (a / "icon.png").write_text("x"); (a / "PKGBUILD").write_text("pkgname=x\npkgver=1\npkgrel=1\narch=(any)\n")
    push(a, "app")
    body = dict(Repository="https://github.com/ann/aequalyn-app-my-app", Commit="", Name="My App", About="x", License="MIT")
    labels, state, said = issue("[app] My App", "ann", form(**body))
    ok("app:my-app" in catalog(), f"an app: {said}")
    c = push(a, "app two")
    labels, state, said = issue("[update] App", "ann", form(Kind="app", Repository=body["Repository"], Commit="", **{"What changed": "x"}, Name="Other name"))
    ok(catalog().get("app:my-app", {}).get("commit") == c and catalog()["app:my-app"]["name"] == "Other name" and "app:other-name" not in catalog(), f"its update: {said}")

    # a new id is strict: no two can be mistaken for each other, nor for Aequalyn's own
    for who, name, ident, why in (
            ("bob", "bob/aequalyn-plugin-o-ne", "o-ne", "reads the same as"),
            ("bob", "bob/aequalyn-plugin-bar", "bar", "Aequalyn's own"),
            ("bob", "bob/aequalyn-plugin-battery-guard", "battery-guard", "Aequalyn's own"),
            ("bob", "bob/aequalyn-plugin-aequalyn", "aequalyn", "Aequalyn's own"),
            ("bob", "bob/aequalyn-plugin-two-_x", "two-_x", "cannot be an id"),
            ("bob", "bob/aequalyn-plugin-Up", "Up", "could not be read"),
            ("bob", "bob/my-plugin", "mine", "Name the repository `aequalyn-plugin-mine`")):
        repo(name, ident)
        labels, state, said = issue("[plugin] X", who, form(Repository=f"https://github.com/{name}", Commit="", Name="X", About="x", License="MIT"))
        ok("changes-requested" in labels and why in said and state == "open", f"{ident} from {name}: {labels} {said[-200:]}")
    repo("bob/aequalyn-theme-amber", "amber")
    labels, state, said = issue("[theme] Amber", "bob", form(Repository="https://github.com/bob/aequalyn-theme-amber", Commit="", Name="Amber", About="x", License="MIT"))
    ok("changes-requested" in labels and "Aequalyn's own" in said, f"a built-in theme's name: {labels}")
    repo("bob/aequalyn-wallpapers-dusk", "dusk")
    labels, state, said = issue("[wallpaper] Dusk", "bob", form(Repository="https://github.com/bob/aequalyn-wallpapers-dusk", Commit="", Name="Dusk", About="x", License="MIT"))
    ok(state == "closed" and "wallpaper:dusk" in catalog(), f"a wallpaper pack's repository: {said[-200:]}")

print(f"market: {fails} failures")
sys.exit(1 if fails else 0)
