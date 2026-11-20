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
4. A reviewer with write access comments `/approve` (the checks run once more at the
   pinned commit, and it joins the catalog) or `/reject <reason>`.

## What is here

```
.github/ISSUE_TEMPLATE/   the Publish forms, one per kind
.github/workflows/        check.yml (the report on every submission), review.yml (/approve, /reject)
docs/guidelines/          what each kind must carry, how it is checked, what it must not do
submissions/<id>.json     one record per approved submission
db/market.json            the catalog, built from submissions/ by tools/build_db.py
db/market.json.sha256     its checksum, verified by every Store before reading it
tools/check.py            the checks, as the bot and reviewers run them
```

## Install from it

The Store reads `db/market.json` (`aequalyn-store refresh`) and installs every item with
`aequalyn-store install <kind> <repo> --at <commit>`: the database only points, at the
commit that was checked; it never carries code.

A Look is a set of visual settings, one piece or several: the bar, the docks, the cursor,
the lock screen, the lock and sleep timings, the login screen. A user wears all of it or
only the pieces they pick.
