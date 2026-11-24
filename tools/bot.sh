#!/usr/bin/env bash
# bot.sh -- what the workflows run on a Publish issue. Needs gh (GH_TOKEN), REPO and python3.
#
#   bot.sh check <issue>                    check it, post the report, set its labels
#   bot.sh review <issue> <label> <actor>   a reviewer set `approved` or `rejected`
#
# Labels: needs-review and changes-requested are the bot's; security-review is set by the
# bot (or a reviewer) and holds an approval back until a reviewer takes it off; approved
# and rejected are a reviewer's. Only someone who can write to this repository is one: a
# label can also be set by people who cannot.
set -euo pipefail

cmd=${1:?} issue=${2:?}
tools=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT

say() { gh issue comment "$issue" --repo "$REPO" --body "$1" >/dev/null; }
label() { gh issue edit "$issue" --repo "$REPO" --add-label "$1" >/dev/null; }
unlabel() {
    local l
    for l in "$@"; do
        if has "$l"; then gh issue edit "$issue" --repo "$REPO" --remove-label "$l" >/dev/null; fi
    done
}
has() { gh issue view "$issue" --repo "$REPO" --json labels --jq '.labels[].name' | grep -qx -- "$1"; }
# the issue as it is now; its hash ties a report to exactly the text that was checked
read_issue() {
    gh issue view "$issue" --repo "$REPO" --json title --jq .title > "$work/title"
    gh issue view "$issue" --repo "$REPO" --json body --jq .body > "$work/body.md"
    ISSUE_TITLE=$(cat "$work/title")
    ISSUE_AUTHOR=$(gh issue view "$issue" --repo "$REPO" --json author --jq .author.login)
    ISSUE_NUMBER=$issue
    export ISSUE_TITLE ISSUE_AUTHOR ISSUE_NUMBER
    hash=$(cat "$work/title" "$work/body.md" | sha256sum | cut -d' ' -f1)
}

do_check() {
    has submission || { echo "not a submission"; return 0; }
    unlabel approved rejected needs-review changes-requested
    read_issue
    local ok=0
    python3 "$tools/check.py" "$work/body.md" --hash "$hash" --flags "$work/flags" > "$work/report.md" && ok=1
    cat "$work/report.md"
    gh issue comment "$issue" --repo "$REPO" --body-file "$work/report.md" >/dev/null
    if [[ $ok -eq 1 ]]; then
        if [[ -s "$work/flags" ]]; then label security-review; fi
        label needs-review
    else
        label changes-requested
    fi
}

do_review() {
    local want=${1:?} actor=${2:?} perm
    perm=$(gh api "repos/$REPO/collaborators/$actor/permission" --jq .permission 2>/dev/null || true)
    if [[ "$perm" != admin && "$perm" != write ]]; then
        unlabel "$want"
        say "\`$want\` is a reviewer's label: it was taken off."
        return 0
    fi
    if [[ "$want" == rejected ]]; then
        unlabel approved needs-review changes-requested
        gh issue close "$issue" --repo "$REPO" --reason "not planned" >/dev/null
        return 0
    fi
    if has security-review; then
        unlabel approved
        say "It still has \`security-review\`: take that off once its code has been read, then set \`approved\` again."
        return 0
    fi
    if ! has needs-review; then
        unlabel approved
        say "It has no passing check to approve (\`needs-review\` is not set)."
        return 0
    fi
    read_issue
    # the newest report of ours; only its first line counts, the rest quotes the submission
    local mark pinned
    mark=$(gh api "repos/$REPO/issues/$issue/comments" --paginate \
        --jq '.[] | select(.user.login == "github-actions[bot]") | .body | split("\n")[0]' \
        | tr -d '\r' | grep -E '^<!-- aequalyn-market pinned:' | tail -n1 || true)
    pinned=$(sed -nE 's/^<!-- aequalyn-market pinned:([0-9a-f]{40}) issue:([0-9a-f]{64}) -->$/\1/p' <<<"$mark")
    if [[ -z "$pinned" || "$mark" != *"issue:$hash -->" ]]; then
        unlabel approved needs-review
        say "The issue is not the one that was checked: it is checked again now."
        do_check
        return 0
    fi
    if ! python3 "$tools/check.py" "$work/body.md" --pinned "$pinned" --hash "$hash" --record "$work/record.json" > "$work/report.md"; then
        unlabel approved needs-review
        label changes-requested
        gh issue comment "$issue" --repo "$REPO" --body-file "$work/report.md" >/dev/null
        return 0
    fi
    # several approvals may run at once: each starts from the newest catalog
    local i name done=0
    for i in 1 2 3 4 5 6 7 8; do
        git fetch -q origin main
        git reset -q --hard origin/main
        name=$(python3 - "$work/record.json" "$actor" <<'PY'
import json, sys, datetime, pathlib
r = json.load(open(sys.argv[1]))
r["approved"] = datetime.date.today().isoformat()
r["approvedBy"] = sys.argv[2]
pathlib.Path("submissions").mkdir(exist_ok=True)
# by kind too: a theme and a look may share a name
pathlib.Path(f"submissions/{r['kind']}-{r['id']}.json").write_text(json.dumps(r, indent=2) + "\n")
print(r["kind"], r["id"])
PY
)
        python3 tools/build_db.py
        git add submissions db
        if git diff --cached --quiet; then done=1; break; fi
        git commit -qm "feat(market): approve $name at ${pinned:0:12} (#$issue)"
        if git push -q origin HEAD:main; then done=1; break; fi
        sleep $((RANDOM % 6 + 2))
    done
    if [[ $done -ne 1 ]]; then
        unlabel approved
        say "The catalog could not be written just now: set \`approved\` again."
        return 1
    fi
    unlabel needs-review
    say "Approved at \`${pinned:0:12}\` by @$actor: it is in the catalog."
    gh issue close "$issue" --repo "$REPO" --reason completed >/dev/null
}

case "$cmd" in
    check) do_check ;;
    review) do_review "${3:?}" "${4:?}" ;;
    *) echo "unknown: $cmd" >&2; exit 2 ;;
esac
