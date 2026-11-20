# Aequalyn Market — cursor guidelines

Everything a cursor submission is checked against, and why. Read this before you open
a submission issue: the bot checks all of it, at the commit your issue pins.

## 1. How the shell works

The pointer is managed by **Plume**, the shell's "Cursor and pointer effects" plugin,
behind the control center's Cursor page. Two systems draw cursors on this desktop and
Plume sets both:

- **Hyprland** draws the pointer everywhere with the theme it is told:
  `hyprctl setcursor <theme> <size>` — a Hyprcursor theme if `enable_hyprcursor` is
  on (Plume turns it on when needed).
- **GTK 3 programs draw the cursor themselves**, from gsettings
  (`org.gnome.desktop.interface cursor-theme` and `cursor-size`), so the same theme
  and size go there too.

Plume finds themes by scanning the icon directories — in order:

```
~/.local/share/icons     where the Store installs yours
~/.icons
/usr/local/share/icons
/usr/share/icons
```

An **XCursor theme** is a folder with a `cursors/` directory; a **Hyprcursor theme**
is one with `manifest.hl` (or `manifest.toml`). The session's own theme
(`XCURSOR_THEME`, `XCURSOR_SIZE`) is remembered before anything is changed, so "As the
system sets it" is always one click away — your theme must survive being taken off as
cleanly as it was put on.

Two names are reserved and rejected: `default` (the system alias) and anything
matching `plume-[a-z]` (the folders Plume forges its own designed cursors into, taking
turns so Hyprland always loads one fresh).

## 2. What you make

One folder named after your theme (letters, digits, dots, underscores, plus and
spaces — up to 63 characters):

```
<Name>/
├── manifest.hl          the Hyprcursor manifest (or manifest.toml — then cursors/ for XCursor)
├── cursors/             the XCursor binaries, for the programs that only know XCursor
├── icon.png             the card icon — the Store cannot guess what your arrow looks like
└── README.md           parsed and presented on your item's page
```

- **Carry both when you can.** A Hyprcursor manifest alone covers the desktop; the
  XCursor copy beside it covers GTK and the older tools. Ship both and everything
  draws the same pointer.
- **Shapes people actually see**: at minimum `left_ptr` (the arrow), `text` (the beam),
  `pointer/hand2` (links), `grabbing` (drags), `crosshair`, the four `sb_*_arrow`
  resizes and their corners, `watch`/`left_ptr_watch` (busy). A missing shape falls
  back to the default theme — a reviewer clicks through a full desktop with yours and
  notes every fallback.
- **Sizes**: ship at least 16, 24, 32 and 48; Hyprland accepts 8–256, and people run
  HiDPI. Hyprcursor scales SVGs for you; XCursor needs the sizes baked.
- **Hotspots are part of the cursor**: the arrow's tip, the beam's centre, the
  resize edges — at every size. A hotspot that drifts by a pixel at 32 makes every
  click land wrong, and the test catches it.

`icon.png` is required — a real image, under the size cap, showing the arrow: it is
what the Store's card and the market site show, because no icon set on earth carries
a third-party cursor.

## 3. How it integrates

The Store copies your folder, at the pinned commit, into
`~/.local/share/icons/<Name>/` — never `/usr/share/icons` — and calls
`qs ipc call plume rescan`; `qs ipc call plume themes` lists you at once. Wearing is
`qs ipc call plume cursor <name>`: Plume sets Hyprland, sets GTK, and remembers what
was on before. Taking it off is "As the system sets it"; uninstalling asks the user
to wear something else first, then removes the folder and rescans — so nothing ever
points at a folder that is gone.

You never set environment variables, never write Hyprland's config, never touch
gsettings yourself: Plume owns the pointer, and two writers make a flickering cursor.

## 4. What not to do

- **No install scripts, no hooks, no symlinks** — a cursor theme is files; the folder
  is copied, nothing of yours ever runs.
- **Don't write configuration**: no `hyprland.conf`/`hyprland.lua` edits, no
  `~/.icons/default`, no env files. Plume does the applying.
- **Don't name yourself `default` or `plume-*`** — reserved, and rejected on sight.
- **Don't put executables in the folder.** Any executable bit fails the check, the
  `cursors/` binaries excepted — and those must be real XCursor files.
- **No paths outside your folder** in the manifest: every `cursors/` reference stays
  inside; a manifest pointing at `../` or an absolute path is traversal and fails.
- **Don't ship half a theme**: missing everyday shapes reads as broken, whatever the
  arrow looks like.

## 5. Checking the syntax, before you submit

- The manifest parses: `manifest.toml` as toml; `manifest.hl` against hyprcursor's
  own format — every `define_shape` with a name, a size and a hotspot.
- The XCursor files are what they claim: the checker reads magic bytes; so can you —
  `file cursors/left_ptr` should not say "data".
- `icon.png` opens as an image and is under the cap.
- `aequalyn-store check cursor .` runs the whole battery, as the bot will.

## 6. The tests it must pass

- **Listed**: `qs ipc call plume themes` shows your name after a rescan.
- **Worn at each size**: 16, 24, 32, 48 — crisp at HiDPI, hotspot true at every one.
- **Everyday shapes**: the reviewer spends a minute on the desktop — links, text
  fields, drags, resizes, busy waits — and no shape falls back to the default.
- **GTK agrees**: a GTK 3 program draws the same pointer (gsettings were set), not a
  mix of yours and the old one.
- **Taken off cleanly**: "As the system sets it" restores the remembered theme, and
  the desktop keeps working after your folder is removed.
- **The icon shows** on the Store's card and the market site.

## 7. Security concerns

- Binary cursors are the one place this kind has bytes — so the checker sniffs every
  file by magic bytes and rejects anything that is not a real XCursor or a real
  image. No executable bits anywhere in the folder.
- No script, no symlink, no path traversal — the manifest is walked, every reference
  resolved inside the folder.
- Filenames sanitized; size caps on every file, the icon included.
- The catalog pins the commit it approved, and the sha256 of every file; users curl
  your folder at that commit, and an update is re-checked before it re-pins.
