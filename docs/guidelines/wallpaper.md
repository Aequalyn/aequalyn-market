# Aequalyn Market — wallpaper guidelines

Everything a wallpaper-pack submission is checked against, and why. Read this before
you open a submission issue: the bot checks all of it, at the commit your issue pins.

## 1. How the shell works

Two kinds of things carry backgrounds on this desktop:

- a **theme** ships its `backgrounds/` with a palette — see the theme guidelines;
- a **wallpaper pack** is backgrounds alone: no palette of its own. Whatever is on
  becomes the wallpaper, and — in wallpaper mode — the whole desktop's palette is
  generated from it with matugen, following every change.

The wallpaper engine takes a file and sets it (`aequalyn-wallpaper set <file>`); the
rotation walks a folder in name order, static or timed. The Store installs your pack
by reading its **`index.json`** and curling each entry, in order, into:

```
~/.local/share/aequalyn/wallpapers/<pack>/
```

The rotation picks the folder up at once. Your pack is data from end to end: nothing
in it runs, and every file lands where the index says it lands.

Because the desktop may generate its palette from your images, a pack is a colour
decision as much as a picture one: ship images you would want the whole desktop
tinted by.

## 2. What you make

One folder named after your pack:

```
<pack>/
├── index.json     links every wallpaper — what the Store parses
├── README.md      parsed and presented on your item's page
└── (the files themselves, wherever in your repo the urls point)
```

`index.json` — an array, one entry per wallpaper, in the order they should install:

```json
[
  { "file": "01-orion.jpg", "title": "Orion over the ridge",
    "credit": "astro · CC-BY-4.0", "url": "https://raw.githubusercontent.com/astro/nebulae/main/01-orion.jpg" },
  { "file": "02-carina.jpg", "title": "Carina",
    "credit": "astro · CC-BY-4.0", "url": "https://raw.githubusercontent.com/astro/nebulae/main/02-carina.jpg" }
]
```

- `file` is the name it lands as in the pack folder — sanitized, no paths: letters,
  digits, dots, dashes and spaces, nothing else. Number them if the order matters.
- `title` is what the Store shows on the pack's page; `credit` is who made it, and
  the license in one line. Credits are not decoration: the checker reads them and
  the reviewer checks them against what your README claims.
- `url` is **https, inside the pack's own repository** — raw.githubusercontent or a
  release asset of the very repo the submission pins. No third-party hosts, no
  credentials in urls, no redirectors.
- Formats: `jpg jpeg png webp bmp gif mp4 webm mkv mov`. **No SVG, ever** — an SVG
  can carry scripts, and a wallpaper is not a place for scripts. Videos loop through
  the wallpaper engine; keep them short and small.
- Size caps per file and for the pack; a wallpaper bigger than the caps helps no one.

## 3. How it integrates

At your pinned commit the Store parses `index.json`, then curls each `url` in order
into `~/.local/share/aequalyn/wallpapers/<pack>/` under its `file` name, and checks
every one against the **sha256 the catalog recorded when your pack was approved** —
a byte off is a failed install, not a shrug. The rotation takes the folder at once;
a wallpaper pack can also be picked up by a theme that wants its own backgrounds
nearby. Removing the pack removes the folder; a wallpaper in use from it is replaced
first, so the desktop never points at a file that is gone.

## 4. What not to do

- **No SVG** — see above; it is the one format refused on security grounds.
- **No urls outside your repository**: no image hosts, no CDNs, no "mirror" that can
  change under you. The catalog pins bytes by sha256; a hotlink cannot promise bytes.
- **No traversal and no absolute paths** in `file` — `../` and `/`-leading names
  fail before anything is fetched.
- **No executables, no scripts, no archives** — a pack is images and videos; a zip
  inside a pack is a rejection.
- **Don't ship work you can't credit.** Every entry carries its `credit`; a README
  that claims licenses the files don't have is a rejection, and the reviewer checks.
- **Don't point at floating branch heads in a way that can change**: the submission
  pins a commit — use urls that resolve at that commit, and the recorded sha256 keeps
  them honest forever after.

## 5. Checking the syntax, before you submit

- `jq . index.json` — it must parse as one array of objects, each with `file`,
  `title`, `credit`, `url`.
- The `file` names: `ls` them through the sanitizer pattern mentally — if a shell
  would quote it strangely, rename it now.
- Dry-fetch every url: `curl -fsSL -o test <url>` for each; then `file test` and
  `sha256sum test` — the checker does exactly this.
- `aequalyn-store check wallpaper .` runs the whole battery, as the bot will.

## 6. The tests it must pass

- **Every url fetches** at the pinned commit, and the bytes hash to what the catalog
  recorded — the bot curls them all before a human reads your issue.
- **Every file is what it claims**: magic bytes match its extension, sizes within the
  caps, no surprises in the folder.
- **Every file opens** in the wallpaper engine; a video loops without a stutter.
- **One becomes the wallpaper** and the rotation walks the pack in name order.
- **Palette from the wallpaper works**: with one of your darker images on, the
  desktop's generated colours read well; the same with a lighter one. A pack whose
  every image produces unusable palettes is a pack nobody can live in.
- **Removed cleanly**: the folder goes, the wallpaper in use is replaced first, and
  the rotation keeps working.

## 7. Security concerns

- The whole point of `index.json` is that **the database only points, never carries**:
  files come from your repo at the pinned commit, hashed against the catalog — a
  swapped file upstream is a failed install, not a surprise on someone's desktop.
- Magic-byte sniffing on every file: the extension can lie, the bytes can't. Anything
  active — scripts in SVG, executables, archives — fails before a human reads it.
- Filename sanitization on every `file`, and the checker walks your repo for files
  the index forgot — nothing rides along unnamed.
- https-only, same-repo-only urls: no credentials to leak, no third party to trust,
  no redirect that could turn your wallpaper into someone else's payload.
