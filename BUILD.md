# Govorim — offline app (Tauri v2)

Tauri **v2** — required for Android/iOS targets. If you unpacked an earlier v1
scaffold, delete `src-tauri/` entirely and unpack this over it; the config
schemas are incompatible and v1 files will fail the build.

## Architecture

On launch the app starts a tiny HTTP server on 127.0.0.1 and points the webview
at it. That server answers everything the frontend already requests, from local
disk — so **`src/App.jsx` needs no changes at all**.

| Request | Served from |
|---|---|
| `/books/…` `/vocab/…` `/music/…` `/grammar/…` `/audio/…` | your data folder |
| `/api/catalogue` | `private/books/index.json` on disk |
| `/api/user-data` GET/POST | `%APPDATA%\Govorim\userdata\*.json` |
| `/api/auth/me` | stub — always "signed in" |
| `/api/media?audio=` | your data folder |
| `/api/define?word=` | **proxied to Vercel — the only network call** |
| `/api/auth/*` `/api/admin/*` `/api/forum/*` | 404 (online-only, removed) |
| anything else | the bundled frontend |

## Windows build

```bash
npm install --save-dev @tauri-apps/cli@^2
npm run build
npx tauri build
```
Needs rustup + MSVC build tools. WebView2 ships with Windows 11.
Output: `src-tauri/target/release/bundle/`.

Icons first, or the bundler complains:
```bash
npx tauri icon path/to/logo.png
```

## Android build

```bash
npx tauri android init
npx tauri android build --apk
```
Needs Android Studio (SDK + NDK) and a JDK, with `ANDROID_HOME` and
`NDK_HOME` set. Produces a sideloadable APK — no Play Store account.

Android has no folder picker for app-private storage, so the library is pushed
to the device instead:
```bash
adb push <your library> /sdcard/Android/data/dev.govorim.app/files/library
```

Cleartext to localhost needs `android:usesCleartextTraffic="true"` in the
generated `AndroidManifest.xml` (under `gen/android/`), or the webview refuses
to load `http://127.0.0.1`.

## The define key (required, or every word click 401s)

This build serves the app from localhost, so it has no browser session cookie —
and `/api/define` is account-gated. It authenticates with a shared secret instead.

1. Pick any long random string.
2. Add it to Vercel as env var `DESKTOP_KEY`, and redeploy.
3. Put the same value in `%APPDATA%\Govorim\settings.json` as `define_key`.

`api/define.js` accepts either a normal browser session (how the iPhone web app
works) or this header, so both paths keep working. Backup of the original at
`api/define.js.bak-desktopkey`.

## First run (desktop)

Asks once for your library folder, laid out as:
```
<data root>/
  books/          private/books/   vocab/   music/   grammar/
  audio/          (your R2 mirror)
```
Remembered in `%APPDATA%\Govorim\settings.json` alongside `define_url`.

## Seed your vocab
```bash
mkdir -p "$APPDATA/Govorim/userdata"
cp ~/govorim-r2-mirror/userdata/u_8692ed92d5aec0de5adbe0cc/*.json "$APPDATA/Govorim/userdata/"
```

## iPhone

No native build without a Mac. The iPhone uses the **existing web app** instead:
Safari → Share → Add to Home Screen. It streams audio from R2 and uses the
normal login, exactly as it does today — nothing to build or maintain.

`lib.rs` is already marked `mobile_entry_point`, so the native iOS path is ready
if a Mac ever turns up.

## Known limitation: two vocab lists

The desktop app keeps vocab in `%APPDATA%\Govorim\userdata\`; the iPhone web
app keeps it in R2. They do **not** sync — words saved on one will not appear on
the other. Fixing that means giving `/api/user-data` the same shared-key
treatment as `define` and having the desktop app read/write it over the network,
which trades away offline vocab saving. Left alone for now, deliberately.
