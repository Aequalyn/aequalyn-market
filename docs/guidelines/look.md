# Aequalyn Market — look guidelines

A look dresses part of the desktop, or all of it: the bar, the docks, the cursor, the
lock screen, the lock and sleep timings and the login screen. Publish one piece or
several in one look; a user wears all of it or only the pieces they pick.

## 1. How the shell works

Each piece already has a home in the shell, and a look only fills it:

| Piece | Where it lives | How the Store wears it |
| --- | --- | --- |
| `bar` | `barStyle` in `~/.config/aequalyn/settings.json` | merged into `barStyle`; the bar redraws at once |
| `dock` | the docks' style in `~/.config/aequalyn/docks.json` | `qs ipc call dock importLook <json>`: every dock wears it and stops following the bar |
| `cursor` | Plume's look (`~/.local/state/aequalyn-plume/`) | `qs ipc call plume importLook <json>` |
| `lock` | a design in `~/.config/hypr/lockscreens/` | copied as `look-<id>.conf`, chosen as the lock style, rendered by `aequalyn-lockscreen` in the user's own colours |
| `sleep` | `power` in `settings.json` | the timings merged in, then `aequalyn-idle` rewrites hypridle |
| `sddm` | `/usr/share/sddm/themes/` | copied as `aequalyn-look-<id>` and chosen in `/etc/sddm.conf.d/aequalyn-theme.conf` — the one piece that asks for the user's password |

## 2. What you make

```
aequalyn-look-<id>/
├── look.json        the look — what the Store reads
├── lock.conf        optional: the lock screen design (a piece names it)
├── sddm/            optional: the login theme (Main.qml, metadata.desktop, its files)
├── preview.png      what the Market shows
└── README.md        parsed and presented on your item's page
```

`look.json`:

```json
{
  "id": "harbour-night",
  "name": "Harbour night",
  "version": "1.0.0",
  "repo": "https://github.com/you/aequalyn-look-harbour-night",
  "pieces": {
    "bar":    { "shape": "islands", "ends": "capsule", "radius": 10, "surface": "glass" },
    "dock":   { "ends": "capsule", "surface": "glass", "opacity": 85 },
    "cursor": { "shape": "arrow", "size": 28 },
    "lock":   "lock.conf",
    "sleep":  { "lockMinutes": 10, "screenOffMinutes": 12, "suspendMinutes": 30 },
    "sddm":   "sddm/"
  }
}
```

- `pieces` holds one or more of `bar`, `dock`, `cursor`, `lock`, `sleep`, `sddm`.
- `bar`, `dock` and `cursor` are flat objects of the shell's own keys: the bar and dock
  keys of `style/Style.js` and `style/BarLooks.js`, Plume's look keys (an export from
  `qs ipc call plume exportLook` is the easiest start). Unknown keys are dropped, and
  every value is cleaned by the shell as if set by hand.
- `sleep` takes only `lockEnabled`, `screenOffEnabled`, `suspendEnabled` (booleans) and
  `lockMinutes`, `screenOffMinutes`, `suspendMinutes` (1–240).
- `lock` names a `.conf` beside `look.json`: a hyprlock template in the shape of the
  shell's own designs (`config/hypr/lockscreens/*.conf`), with `{{FONT}}` and the colour
  placeholders the renderer fills in.

## 3. How it integrates

The Store's pipeline, at the commit your submission pins:

1. `git clone` at that commit.
2. `look.json` parsed and every piece checked as below.
3. The SDDM theme's QML goes through qmllint and the banned patterns.
4. On pass: the folder lands in `~/.local/share/aequalyn/looks/<id>/`. Nothing is worn
   until the user asks: **Wear all**, or one piece at a time.

## 4. What not to do

- Don't carry a theme or wallpapers: a look dresses the shell's parts and leaves the
  colours to the user's theme. Publish a theme for those.
- Don't run anything from the lock screen: no `cmd[...]`, `exec`, `$(...)` or backticks.
  A lock screen only draws.
- Don't reach outside the folder: no symlinks out, no absolute paths, no `../`.

## 5. Checking the syntax, before you submit

- `jq . look.json` — it must parse.
- `aequalyn-store check look . --market` runs the whole battery, as the bot will.
- For the lock screen: `aequalyn-lockscreen try look-<id>` after copying `lock.conf`
  to `~/.config/hypr/lockscreens/look-<id>.conf`.

## 6. The tests it must pass

- Every piece is one of the six, with the shape above.
- `lock.conf` exists beside `look.json` and runs nothing.
- `sddm/` has `Main.qml` and `metadata.desktop`, and its QML lints clean.
- `README.md` exists.

## 7. Security concerns

- A look changes settings, never code: the bar, dock and cursor pieces are data the
  shell cleans; the sleep piece is six known keys in a range.
- The lock screen is a hyprlock config: the commands it could run are banned.
- The SDDM theme runs as the login manager: its QML is linted and grepped for the
  banned patterns (no network, no shells, no downloads), and installing it asks for
  the user's password, every time.
- A user's Store wears the look at the commit that was checked.
