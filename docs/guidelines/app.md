# Aequalyn Market — app guidelines

Everything an app-from-source submission is checked against, and why. Read this
before you open a submission issue: the bot checks all of it, at the commit your issue
pins — and for this kind, a human reads every line of your build before approving.

## 1. How the shell works

Apps on this desktop arrive through **backends**, and the Store's Apps page knows
them all — `command -v` at open, an Install button per backend, and a Backend install
button for the ones missing:

| Backend | Source | Install command |
| --- | --- | --- |
| pacman | Arch repos, incl. multilib — always there | `sudo pacman -S <pkg>` |
| yay | aur.archlinux.org, built locally | `yay -S <pkg>` |
| flatpak | Flathub | `flatpak install flathub <ref>` |
| snap | the Snap Store | `snap install <pkg>` |

An **app from source** is the fifth road: your own PKGBUILD, built on the user's
machine with makepkg, exactly the way the AUR does it — but pinned. The submission
records the commit; the catalog records it and the sha256 of your sources; the user's
Store builds **that commit**, never a floating branch; and when your repo moves, the
watcher re-checks the new commit before anyone's Store offers it as an update.

Your submission also carries `icon.png`: the Store's card needs an image, and no icon
set on earth can be assumed to have yours. (If dashboardicons.com has your app, say
so in the README — the Store prefers its copy.)

## 2. What you make

One folder named after your app:

```
<app>/
├── PKGBUILD          the build — what pacman installs from (or build.sh, read by the checker)
├── .SRCINFO          optional, `makepkg --printsrcinfo`
├── icon.png          the card icon — a real image, under the cap
└── README.md         parsed and presented on your item's page
```

The PKGBUILD rules, and none of them are style:

- **Sources pinned.** Every `source=` entry is a URL that resolves at your pinned
  commit — a release tarball, or a codeload URL
  (`https://github.com/<you>/<app>/archive/<commit>.tar.gz`) — each with a correct
  `sha256sums=` entry. A floating `HEAD`, a `refs/heads/main` URL, or a missing sum
  fails.
- **`depends` declared, nothing implicit.** If it links against it, it's in the list.
- **No `-git` floating inside**: if you ship a VCS package, its source is still the
  pinned commit; the branch moves, your submission doesn't.
- **Nothing prebuilt unless declared.** If a source tarball ships binaries, say so in
  the README with the upstream's justification — the reviewer reads it and decides;
  an undeclared binary is an automatic rejection.

## 3. How it integrates

The Store installs your app by building it as the AUR would: `makepkg -si` at the
pinned commit — sources fetched and hashed, compiled, packaged, installed through
pacman's own bookkeeping. It lands in the system paths like any package, shows in the
launcher, and **uninstalls through the backend that owns it** — `pacman -R <pkg>` —
with the Store's Remove button running exactly that. Updates come from the market
watcher: a newer commit on your repo, re-checked at that commit, seeds every Store
with "Update available", and the rebuild happens locally again — never a silent
branch pull.

## 4. What not to do

- **No `curl … | sh`**, anywhere — not in `build()`, not in `prepare()`, not in a
  helper the PKGBUILD calls. Sources come from `source=` with sha256s, or they don't
  come.
- **No network in `package()`**: everything it needs is already built; a packaging
  step that reaches out is a red flag the checker greps for and a reviewer rejects.
- **No writing outside the package.** No `$HOME` writes in install hooks, no
  `post_install` touching rc files or autostart, no edits to `/etc` beyond your own
  `backup=(` entries. A package installs files; it does not reconfigure a person's
  machine.
- **No `sudo`, no `root` assumptions inside build steps** — makepkg handles
  privileges; your script never asks.
- **No name-colliding with an official repo package**: if `pacman -Si <name>` finds
  yours in the repos already, your submission is redundant — point the Store's
  popular grid at the backend instead.
- **No telemetry added by you.** If upstream has an opt-in, the README says how to
  turn it off.

## 5. Checking the syntax, before you submit

- `makepkg --printsrcinfo` — it must parse and match the PKGBUILD.
- `namcap PKGBUILD` — its warnings are the reviewer's first questions; answer them in
  the README or fix them.
- If you ship `build.sh` instead: `shellcheck build.sh` clean.
- Verify each sha256 yourself: `updpksums` or by hand — one wrong sum is a failed
  install for every user.
- `aequalyn-store check app .` runs the whole battery, as the bot will.

## 6. The tests it must pass

The bot checks structure and sums; then the build runs in a sandbox, and what it
built is used:

- **Builds in a clean chroot** — no dependency silently picked up from the builder's
  machine.
- **Installs, launches, removes**: the app opens from the launcher after `makepkg
  -si`; `pacman -R <pkg>` leaves no orphans behind.
- **`$HOME` stays untouched during install** — the sandbox runs the install with a
  watched HOME; a single write outside it fails the submission.
- **The icon shows** on the Store's card and in the launcher.
- **The version reports honestly**: what the package claims is what runs.
- **The pinned-commit test**: the build is repeated from a bare clone at your pinned
  commit — if the two builds differ, the submission describes something other than
  what it pins.

## 7. Security concerns

This is the one kind where the submission *builds and runs code* on the user's
machine, so the bar is the highest of the five:

- **Everything is hashed**: every source's sha256, recorded in the catalog at
  approval, verified at every install and every update — a swapped upstream tarball
  is a failed install, not a surprise.
- **The PKGBUILD is read line by line by a human with write access**, not just
  pattern-matched: greps catch the lazy attacks; the reviewer catches the clever ones.
- **The build is sandboxed**: no network beyond pinned sources, a watched `$HOME`,
  no access to the user's shell config — whatever the build tries outside its box,
  the box reports.
- **Binaries declared or rejected**: prebuilt payloads are the classic supply-chain
  move, so they require an upstream justification in the README and a reviewer's
  explicit sign-off.
- **Updates re-run all of it** at the new commit before anyone's Store offers the
  update — a repo that goes bad never rides its own update into anyone's desktop.
