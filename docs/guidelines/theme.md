# Aequalyn Market — theme guidelines

Everything a theme submission is checked against, and why. Read this before you open
a submission issue: the bot checks all of it, at the commit your issue pins.

## 1. How the shell works

The desktop's colours come from one place, the `Theme` singleton, out of two sources
(set on the control center's Theme page):

- **A theme** — a folder with its palette and its own wallpapers. Picking one puts
  its colours everywhere at once, and its first wallpaper on — unless one of its own
  is already on.
- **The wallpaper itself** — colours generated from whatever background is showing,
  made with matugen, following every change of it. Your theme must live beside this
  mode, not fight it.

Picking a theme recolours, at once: the whole shell (every plugin binds the shared
palette), the window borders (`~/.config/hypr/aequalyn/colors.lua`, then
`hyprctl reload`), kitty, the lock screen, other terminals (`aequalyn-apply-palette`),
the GNOME colour-scheme preference, Nautilus/libadwaita CSS and the browser chrome.

**Where themes live**, in lookup order — a later one shadows an earlier with the same id:

```
/usr/share/aequalyn/themes     shipped with the desktop
~/.local/share/aequalyn/themes user-installed
~/.config/aequalyn/themes      where the Store installs yours
```

The active one is recorded in `~/.config/quickshell/theme.conf` (`theme:<id>`, or
`wallpaper` in wallpaper mode) and in the symlink `~/.config/aequalyn/current/theme`.
Your theme never writes either: the shell does, when it applies you.

## 2. What you make

One folder named after your id:

```
<id>/
├── theme.json      the palette (or colors.toml — never both as the source of truth)
├── backgrounds/    images or videos, applied in name order
├── preview.png     optional: the card image the pickers show
└── README.md       parsed and presented on your item's page
```

`theme.json` — the palette, every key:

```json
{
  "name": "crest",
  "family": "crest",
  "author": "nova",
  "variant": "dark",
  "palette": {
    "bgBase": "#16202f",
    "bgSurface": "#1f2c40",
    "bgHover": "#26354c",
    "bgSelected": "#2b3a55",
    "bgBorder": "#31405c",
    "textPrimary": "#c8d3f0",
    "textSecondary": "#a5b3d6",
    "textMuted": "#5d6b8f",
    "accentPrimary": "#7aa2f7",
    "accentCyan": "#7dcfff",
    "accentGreen": "#9ece6a",
    "accentOrange": "#ff9e64",
    "accentRed": "#f7768e"
  },
  "borderColors": ["#7aa2f7", "#7dcfff"]
}
```

- Colours are `#rrggbb` and nothing else — no `rgb()`, no names, no alpha.
- `borderColors` (optional) is the window-border gradient; without it the border runs
  from your accent to your cyan.
- A **backgrounds folder without a palette is a wallpaper pack**, a different kind:
  see the wallpaper guidelines.

`colors.toml` is accepted instead of `theme.json`'s palette — `key = "#rrggbb"` lines,
the same keys, read as a flat colour map.

The palette must work as a desktop, not just as a card:

- The shell decides **light or dark from `bgBase`'s luminance** — set `bgBase`
  accordingly and keep `variant` honest.
- `textPrimary` on `bgBase` at comfortable reading size, `textMuted` still visible,
  `bgSelected` distinct from `bgSurface`, every accent visible on both `bgBase` and
  `bgSurface`. A reviewer switches to your theme and reads the desktop with it.

`backgrounds/` takes `jpg jpeg png webp bmp gif mp4 webm mkv mov`, applied in name
order — number them if the order matters (`01-dawn.jpg`, `02-noon.jpg`, …).

## 3. How it integrates

The Store's pipeline at your pinned commit: the folder is checked
(`jq` for the JSON, or the toml parse; the media formats), copied by
`aequalyn-themes install` into `~/.config/aequalyn/themes/<id>/`, and
`qs ipc call theme reload` makes the running shell see it — Atelier, the Theme page,
and the Store list it at once. Applying is `qs ipc call theme set <id>`; taking it
back off is the Theme page or `aequalyn-themes remove <id>`, which clears the active
link first so the desktop never points at a folder that is gone.

Nothing in your theme runs anything. There is no install script, no hooks, no
side effects — a theme is data, and the checker treats any executable bit or script
file in it as a rejection.

## 4. What not to do

- **No scripts, no executables** — no `install.sh`, no compiled helpers, no symlinks.
- **Don't write configuration**: not `theme.conf`, not Hyprland's files, not kitty's.
  The shell writes those when it applies you.
- **No absolute paths and no remote URLs** inside the folder — backgrounds reference
  nothing; they are files.
- **Don't shadow a shipped theme's id** unless you mean to replace it deliberately:
  your `~/.config` copy wins over `/usr/share`, and the catalog will say so.
- **Don't fight the wallpaper mode**: your palette is one choice among two; a theme
  that breaks when colours follow the wallpaper is rejected.
- **No alpha, no non-hex colours, no invented keys** — unknown palette keys are
  ignored, and a missing key is a failed check, not a default.

## 5. Checking the syntax, before you submit

- `jq . theme.json` — it must parse; `jq -e '.palette | length' theme.json` — all
  thirteen keys.
- The toml, if you use it: plain `key = "#rrggbb"` lines; no tables, no arrays.
- `aequalyn-themes list --json` shows your folder locally, with the palette parsed.
- `aequalyn-store check theme .` runs the whole battery, as the bot will.

## 6. The tests it must pass

- **Listed**: appears in `aequalyn-themes list --json`, correct name, backgrounds
  counted, preview found.
- **Applied everywhere**: `qs ipc call theme set <id>` — the shell, the window
  borders, kitty, the lock screen, the terminal palette, the colour-scheme
  preference, Nautilus, the browser: all change at once. A surface that keeps the old
  colour is a bug in the palette, not in the shell.
- **Light and dark**: the desktop reads correctly with your palette on; nothing
  invisible, no accent lost against a background.
- **Its wallpapers**: the first goes on when applied; the rest rotate in name order;
  a video loops if you ship one.
- **Reverted**: switching back to the previous theme restores everything; switching
  to wallpaper mode still works.
- **Reloaded**: `qs ipc call theme reload` while the shell runs lists it again
  without a restart.

## 7. Security concerns

- A theme is data: the checker rejects any executable file, any script, any symlink
  in the folder — there is nothing a theme needs to run, so there is nothing it may
  run.
- Every background and `preview.png` is sniffed by magic bytes and capped in size —
  a file claiming to be a `jpg` that is not a `jpg` fails, whatever it really is.
- Filenames are sanitized (no traversal, no absolute paths), and the checker walks
  the folder — nothing hidden in dotfiles or nested directories.
- The catalog records the commit it approved; users install at that commit, so what
  was read is exactly what lands.
