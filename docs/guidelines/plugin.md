# Aequalyn Market — plugin guidelines

Everything a plugin submission is checked against, and why it is checked. Read this
before you open a submission issue: the bot checks all of it, at the commit your issue
pins, and a reviewer reads what the bot cannot.

## 1. How the shell works

The Aequalyn desktop is **one long-running QuickShell process** (`qs`), started by
Hyprland at login. Every element of the desktop — the bar, the docks, the launcher,
the notifications, the control center itself — is a plugin, loaded by
`PluginManager.qml`:

- One entry QML per plugin. The manager keeps one `Loader` per plugin, active only
  while the plugin's id is in `AequalynSettings.enabledPlugins`
  (`~/.config/aequalyn/settings.json`, under `plugins`). Turning one on or off loads
  or drops it **at once, without a restart**.
- Your entry is an **`Item`, never a `ShellRoot`**. The shell is the one `ShellRoot`;
  you are loaded inside it. You own your surfaces (a `PanelWindow`, an overlay layer)
  and their whole lifecycle.
- Anything that exposes a **`theme` property** receives the shell's palette
  (`bgBase`, `bgSurface`, `bgHover`, `bgSelected`, `bgBorder`, `textPrimary`,
  `textSecondary`, `textMuted`, `accentPrimary`, `accentCyan`, `accentGreen`,
  `accentOrange`, `accentRed`). Take every colour from it: when the theme changes,
  your plugin changes with the desktop. A hard-coded colour is a bug, a fallback
  excepted.
- The rest of the shell reaches your plugin through **one `<Name>Host.qml` singleton**
  — never by searching for you:

  ```qml
  pragma Singleton
  Singleton {
      property var svc: null        // set by the plugin while it runs
  }
  ```

  Your entry sets `<Name>Host.svc = root` in `Component.onCompleted` and clears it in
  `Component.onDestruction`. Everything that uses the host checks for `null`: the
  plugin may be off.
- **Commands and keys**: an `IpcHandler { target: "<id>" }` gives you
  `qs ipc call <id> <verb>` (`toggle`, `open`, `next`, `status` — name them as verbs).
  A key binding is a line in the Hyprland config that calls one of your commands.
- **Settings**: a few keys live in `~/.config/aequalyn/settings.json`; a plugin with
  many keeps its own files under `~/.local/state/aequalyn-<id>/` and saves as things
  change. Nothing else on disk is yours to write.
- **Quiet when idle.** Draw nothing and run nothing that isn't needed: timers and
  processes only while they matter. A plugin that keeps the CPU busy while hidden is
  rejected on that alone.

The full standard the built-in plugins follow is `PLUGINS.md`, shipped in the shell's
folder (`~/.config/quickshell/PLUGINS.md`). A plugin that reads like the built-ins
feels built in — that is the bar.

## 2. What you make

One folder, named `aequalyn-plugin-<id>`:

```
aequalyn-plugin-<id>/
├── plugin.json        the manifest — what the shell and the Store read
├── <Name>.qml         the entry: an Item
├── <Name>Host.qml     the singleton linking you to the shell
├── qmldir             in every folder imported with root:/
├── Preview.qml        what the Store shows, live, on your item's page
└── README.md          parsed and presented on your item's page
```

`plugin.json` — every field required:

```json
{
  "id": "pomodoro",
  "label": "Pomodoro",
  "entry": "Pomodoro.qml",
  "icon": "Ｆ0F6E",
  "group": "screen",
  "keys": "Super + Alt + P",
  "about": "Focus rounds with long breaks, on the bar.",
  "version": "1.2.0",
  "repo": "https://github.com/you/aequalyn-plugin-pomodoro"
}
```

- `id` is short, lowercase, and never changes: it names the IPC target, the settings
  folder and the catalog entry.
- `group` is one of `screen` (always on the desktop), `key` (called up by a key) or
  `background` (works out of sight) — the same groups the control center's Plugins
  page shows.
- `icon` is a Nerd Font codepoint, as the shell's own `PluginInfo.js` uses.

**`Preview.qml`** is the contract the Store relies on: an `Item` about 360×220 that
exposes a `theme` property and draws your plugin's own look with nothing else — no
windows, no processes, no sockets, no state. The Store loads it live in a box on your
item's page, fed the shell's theme, exactly as the control center loads its stage
pictures. It is qmllinted with everything else.

## 3. How it integrates

The Store's install pipeline, at the commit your submission pins:

1. `git clone --depth 1` at that commit, into a temp folder — nothing is installed yet.
2. The main files are checked: `plugin.json` with its `id` and `entry`, the entry QML,
   a `qmldir` in every folder imported with `root:/`.
3. **qmllint** over every `.qml` file. Errors fail; warnings pass; the log is posted.
4. On pass: the folder moves to `~/.local/share/aequalyn/plugins/<id>/`, the id joins
   `enabledPlugins`, and `qs ipc call plugins rescan` makes the running shell load
   and activate you at once.

Your plugin never edits the shell's registries: the manifest replaces the two lines a
built-in has. Uninstalling turns you off, drops your registry record and removes the
folder; your `Component.onDestruction` has already stopped everything you started.

## 4. What not to do

- **Never a `ShellRoot`.** Never start your own QuickShell instance or spawn `qs`.
- **No remote code.** Nothing loaded from a URL — no `Qt.createComponent` on remote
  sources, no `XMLHttpRequest` to anywhere, no piping a download into a shell.
- **No writes outside your own state folder** (`~/.local/state/aequalyn-<id>/` and, if
  you must, `~/.config/aequalyn/settings.json` through `AequalynSettings`). Never rc
  files, never `~/.config/autostart`, never ssh keys, never Hyprland's config.
- **No blobs.** No base64 or hex payloads, no `eval`, no obfuscation. If the checker
  cannot read what your plugin does, no one can approve it.
- **Only allowlisted programs run**: `qs`, `hyprctl`, `gsettings`, and your own
  `bin/` helpers. `git` is allowed at install time, by the installer, not by you.
- **Don't reach into other plugins' internals.** Use their host singletons and their
  IPC, or don't use them at all.
- **Don't fight the theme.** Colours come from `theme`; fonts from `Cc.sans` /
  `Cc.mono` conventions; nothing hard-coded but fallbacks.
- **Don't hold the main thread.** Long work goes to a process; the UI never waits.

## 5. Checking the syntax, before you submit

- `qmllint <file>.qml` for every QML file — the same binary the bot uses. Errors are
  what fail; fix them, don't argue with them.
- `jq . plugin.json` — the manifest must parse.
- Load test: copy the folder into `~/.local/share/aequalyn/plugins/<id>/` and
  `qs ipc call plugins rescan`. Watch the shell's log for load errors, then toggle
  your plugin twice:
  `qs ipc call aequalyn plugin <id> off` … `on`.
- `aequalyn-store check plugin .` runs the whole battery locally, exactly as the bot
  will on your issue.

## 6. The tests it must pass

The bot posts the report on your issue; a reviewer reads the rest:

- **Loads and unloads cleanly**, twice in a row, while the shell runs; no errors in
  the log; nothing left running after `off`.
- **Survives a shell restart** (`pkill -x qs && qs &`): state intact, host re-registered.
- **Follows the theme**: switch themes (`qs ipc call theme set <other>`) — every
  colour of yours changes; nothing turns invisible on a light theme.
- **Answers its IPC**: `qs ipc call <id> status` replies; the documented key works.
- **Keyboard first**: everything a mouse can do, keys can — arrows move, Enter
  applies, Esc closes.
- **Quiet when idle**: no timer ticking, no CPU, while hidden or resting.
- **The preview loads** in the Store's box and paints with the theme.

## 7. Security concerns

The battery, run at your pinned commit — and again at every update commit:

- qmllint, plus greps for the banned patterns: remote loads, `eval`, base64/hex
  blobs, writes outside your folders, rc/autostart edits, `sudo`, pipes into shells.
- The programs you run are checked against the allowlist; arguments are read.
- An `IpcHandler` named exactly after your id, so you never shadow another plugin's
  target — the checker rejects collisions with the built-ins.
- `Preview.qml` is linted and sandboxed like the entry: it is loaded before install,
  so it must be inert.
- A user's Store installs at the commit that was checked — never at a branch head —
  so what was reviewed is exactly what runs.
