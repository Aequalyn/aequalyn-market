# Aequalyn Market

The catalog every Aequalyn Store reads: plugins, themes, cursors, wallpaper packs, looks
and apps from source that others published, each reviewed and pinned to the commit that
was checked.

## Publish

1. Read the guidelines for your kind in [`docs/guidelines/`](docs/guidelines/):
   [plugin](docs/guidelines/plugin.md) · [theme](docs/guidelines/theme.md) ·
   [cursor](docs/guidelines/cursor.md) · [wallpaper pack](docs/guidelines/wallpaper.md) ·
   [look](docs/guidelines/look.md) · [app](docs/guidelines/app.md).
2. Run the same checks the bot runs: `aequalyn-store check <kind> . --market`.
3. Open an issue with the Publish form for your kind. The bot pins the commit, checks
   it and posts its report on the issue.
4. A reviewer answers with a label (below): `approved` runs the checks once more at the
   pinned commit and puts it in the catalog, `rejected` closes the issue.

## Update

A Store installs and updates only to the commit that was reviewed: what you push after it
reaches nobody until it is reviewed too.

1. Push the new version to the repo it was published from.
2. Open an issue with the Update form. The bot checks it as a new one, sets `update` and
   links what changed since the reviewed commit.
3. Approved, it replaces the old commit, and every Store offers the update.

An item belongs to its repository: only who published it, or owns that repository, can
update it, its id never changes, and the commit must be on the repository's default branch.

## Review

| Label | Set by | Means |
| --- | --- | --- |
| `needs-review` | the bot | every check passes: waiting for a reviewer |
| `changes-requested` | the bot | a check failed: fix it and edit the issue |
| `update` | the bot | a new version of an item: its report links what changed |
| `security-review` | the bot or a reviewer | it runs code (scripts, programs, root, a login screen, an app): read it, then take the label off. Nothing is approved while it is on |
| `approved` | a reviewer | into the catalog, at the commit of the newest report |
| `rejected` | a reviewer | closed; say why in a comment |

Only labels set by someone who can write to this repository count. Editing an issue takes
its labels off and checks it again. To check one again by hand: Actions, "Check a
submission", Run workflow.

## What is here

```
.github/ISSUE_TEMPLATE/   the Publish forms, one per kind, and the Update form
.github/workflows/        check.yml (the report on every submission), review.yml (the reviewers' labels)
docs/guidelines/          what each kind must carry, how it is checked, what it must not do
submissions/<kind>-<id>.json   one record per approved submission
db/market.json            the catalog, built from submissions/ by tools/build_db.py
db/market.json.sha256     its checksum, verified by every Store before reading it
tools/check.py            the checks, as the bot and reviewers run them
tools/bot.sh              what the workflows do with an issue: checks, labels, approvals
```

## Install from it

The Store reads `db/market.json` (`aequalyn-store refresh`) and installs every item with
`aequalyn-store install <kind> <repo> --at <commit>`: the database only points, at the
commit that was checked; it never carries code.

A Look is a set of visual settings, one piece or several: the bar, the docks, the cursor,
the lock screen, the lock and sleep timings, the login screen. A user wears all of it or
only the pieces they pick.
