// Govorim — offline shell (Windows + Android).
//
// The web app talks to its data through ordinary fetch() calls: /books/…,
// /vocab/…, /music/…, /grammar/… for static assets and a handful of /api/…
// endpoints. Rather than rewrite ~7,600 lines of App.jsx to use Tauri's file
// APIs, this binary starts a tiny HTTP server on localhost that answers all of
// those from local disk, and points the window at it. The frontend cannot tell
// the difference, so it needs no changes at all.
//
// The ONE call that still reaches the internet is /api/define, proxied to the
// deployed Vercel function so the Yandex API key stays server-side rather than
// shipping inside the app.



use serde::{Deserialize, Serialize};
use std::fs;
use std::io::Cursor;
use std::path::{Path, PathBuf};
use std::sync::Arc;
use tiny_http::{Header, Response, Server};

#[derive(rust_embed::RustEmbed)]
#[folder = "../dist/"]
struct Dist;

#[derive(Serialize, Deserialize, Clone)]
struct Settings {
    /// Folder holding books/, vocab/, music/, grammar/ and the audio tree.
    data_root: String,
    /// Deployed /api/define endpoint. The only network dependency.
    define_url: String,
    /// Shared secret matching DESKTOP_KEY on the server. This build serves the
    /// app from localhost, so it has no browser session cookie to send; the
    /// key is what lets /api/define accept the call.
    #[serde(default)]
    define_key: String,
}

impl Default for Settings {
    fn default() -> Self {
        Settings {
            data_root: String::new(),
            define_url: "https://govorim.dev/api/define".into(),
            define_key: String::new(),
        }
    }
}

fn config_dir() -> PathBuf {
    let base = std::env::var("APPDATA")
        .map(PathBuf::from)
        .unwrap_or_else(|_| {
            PathBuf::from(std::env::var("HOME").unwrap_or_else(|_| ".".into())).join(".config")
        });
    base.join("Govorim")
}

fn load_settings() -> Settings {
    let p = config_dir().join("settings.json");
    fs::read_to_string(p)
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_default()
}

fn save_settings(s: &Settings) {
    let dir = config_dir();
    let _ = fs::create_dir_all(&dir);
    if let Ok(txt) = serde_json::to_string_pretty(s) {
        let _ = fs::write(dir.join("settings.json"), txt);
    }
}

fn userdata_path(kind: &str) -> PathBuf {
    let dir = config_dir().join("userdata");
    let _ = fs::create_dir_all(&dir);
    dir.join(format!("{kind}.json"))
}

fn read_json_array(kind: &str) -> serde_json::Value {
    fs::read_to_string(userdata_path(kind))
        .ok()
        .and_then(|s| serde_json::from_str(&s).ok())
        .unwrap_or_else(|| serde_json::json!([]))
}

fn json_response(body: String, code: u16) -> Response<Cursor<Vec<u8>>> {
    let hdr = Header::from_bytes(&b"Content-Type"[..], &b"application/json; charset=utf-8"[..])
        .unwrap();
    Response::from_string(body).with_header(hdr).with_status_code(code)
}

/// Resolve a URL path inside the data root, refusing anything that escapes it.
fn safe_join(root: &Path, rel: &str) -> Option<PathBuf> {
    let decoded = urlencoding::decode(rel).ok()?.into_owned();
    let candidate = root.join(decoded.trim_start_matches('/'));
    let root_c = fs::canonicalize(root).ok()?;
    let cand_c = fs::canonicalize(&candidate).ok()?;
    if cand_c.starts_with(&root_c) { Some(cand_c) } else { None }
}

fn serve(settings: Arc<Settings>, port: u16) {
    let server = Server::http(("127.0.0.1", port)).expect("failed to bind local port");
    let root = PathBuf::from(&settings.data_root);

    for mut req in server.incoming_requests() {
        let raw = req.url().to_string();
        let (path, query) = match raw.split_once('?') {
            Some((p, q)) => (p.to_string(), q.to_string()),
            None => (raw.clone(), String::new()),
        };
        let method = req.method().as_str().to_string();

        // ── /api/auth/me — offline: always "signed in", so the gate passes ──
        if path == "/api/auth/me" {
            let body = serde_json::json!({
                "user": { "id": "local", "email": "local", "isAdmin": true }
            });
            let _ = req.respond(json_response(body.to_string(), 200));
            continue;
        }

        // ── /api/catalogue — the manifest, straight off disk ──
        if path == "/api/catalogue" {
            let p = root.join("private/books/index.json");
            let p = if p.exists() { p } else { root.join("books/index.json") };
            match fs::read_to_string(&p) {
                Ok(txt) => { let _ = req.respond(json_response(txt, 200)); }
                Err(e) => {
                    let body = serde_json::json!({ "error": format!("Catalogue unavailable: {e}") });
                    let _ = req.respond(json_response(body.to_string(), 500));
                }
            }
            continue;
        }

        // ── /api/user-data — vocab, tips, progress, settings ──
        if path == "/api/user-data" {
            if method == "GET" {
                let body = serde_json::json!({
                    "vocab": read_json_array("vocab"),
                    "tips":  read_json_array("tips"),
                });
                let _ = req.respond(json_response(body.to_string(), 200));
                continue;
            }
            let mut buf = String::new();
            let _ = req.as_reader().read_to_string(&mut buf);
            let parsed: serde_json::Value =
                serde_json::from_str(&buf).unwrap_or_else(|_| serde_json::json!({}));
            let kind = query
                .split('&')
                .find_map(|kv| kv.strip_prefix("type="))
                .unwrap_or("");
            match kind {
                "progress" | "settings" => {
                    let val = parsed.get(kind).cloned().unwrap_or(serde_json::json!({}));
                    let _ = fs::write(userdata_path(kind), val.to_string());
                }
                _ => {
                    for k in ["vocab", "tips"] {
                        let val = parsed.get(k).cloned().unwrap_or(serde_json::json!([]));
                        let _ = fs::write(userdata_path(k), val.to_string());
                    }
                }
            }
            let _ = req.respond(json_response(r#"{"ok":true}"#.into(), 200));
            continue;
        }

        // ── /api/define — the only call that leaves the machine ──
        if path == "/api/define" {
            let url = format!("{}?{}", settings.define_url, query);
            let out = ureq::get(&url)
                .set("x-govorim-key", &settings.define_key)
                .call();
            match out {
                Ok(resp) => {
                    let txt = resp.into_string().unwrap_or_else(|_| "{}".into());
                    let _ = req.respond(json_response(txt, 200));
                }
                Err(ureq::Error::Status(401, _)) => {
                    let body = serde_json::json!({
                        "error": "Definition lookup was rejected. Check define_key in settings.json matches DESKTOP_KEY on the server."
                    });
                    let _ = req.respond(json_response(body.to_string(), 401));
                }
                Err(e) => {
                    let body = serde_json::json!({
                        "error": format!("Definition lookup needs an internet connection ({e})")
                    });
                    let _ = req.respond(json_response(body.to_string(), 503));
                }
            }
            continue;
        }

        // ── /api/media?audio=… — restricted books; local now, so just serve it ──
        if path == "/api/media" {
            if let Some(rel) = query.split('&').find_map(|kv| kv.strip_prefix("audio=")) {
                if let Some(p) = safe_join(&root, rel) {
                    if let Ok(bytes) = fs::read(&p) {
                        let mime = mime_guess::from_path(&p).first_or_octet_stream();
                        let hdr = Header::from_bytes(&b"Content-Type"[..], mime.as_ref().as_bytes()).unwrap();
                        let _ = req.respond(Response::from_data(bytes).with_header(hdr));
                        continue;
                    }
                }
            }
            let _ = req.respond(json_response(r#"{"error":"not found"}"#.into(), 404));
            continue;
        }

        // Endpoints that only ever made sense online.
        if path.starts_with("/api/auth/") || path.starts_with("/api/admin/")
            || path.starts_with("/api/forum/")
        {
            let _ = req.respond(json_response(r#"{"error":"offline build"}"#.into(), 404));
            continue;
        }

        // ── data files: /books/…, /vocab/…, /music/…, /grammar/… ──
        let is_data = ["/books/", "/vocab/", "/music/", "/grammar/", "/audio/"]
            .iter()
            .any(|p| path.starts_with(p));
        if is_data {
            if let Some(p) = safe_join(&root, &path) {
                if let Ok(bytes) = fs::read(&p) {
                    let mime = mime_guess::from_path(&p).first_or_octet_stream();
                    let hdr = Header::from_bytes(&b"Content-Type"[..], mime.as_ref().as_bytes()).unwrap();
                    let _ = req.respond(Response::from_data(bytes).with_header(hdr));
                    continue;
                }
            }
            let _ = req.respond(Response::from_string("not found").with_status_code(404));
            continue;
        }

        // ── everything else: the bundled frontend, SPA-style ──
        let key = path.trim_start_matches('/');
        let key = if key.is_empty() { "index.html" } else { key };
        let asset = Dist::get(key).or_else(|| Dist::get("index.html"));
        match asset {
            Some(f) => {
                let mime = mime_guess::from_path(key).first_or_octet_stream();
                let hdr = Header::from_bytes(&b"Content-Type"[..], mime.as_ref().as_bytes()).unwrap();
                let _ = req.respond(Response::from_data(f.data.into_owned()).with_header(hdr));
            }
            None => {
                let _ = req.respond(Response::from_string("not found").with_status_code(404));
            }
        }
    }
}

fn free_port() -> u16 {
    std::net::TcpListener::bind("127.0.0.1:0")
        .and_then(|l| l.local_addr())
        .map(|a| a.port())
        .unwrap_or(17817)
}


// ── entry point ─────────────────────────────────────────────────────────────
// Marked as the mobile entry point so the Android (and later iOS) harness calls
// straight into this, while `main.rs` remains the desktop entry.

use tauri::Manager;
use tauri_plugin_dialog::DialogExt;

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .setup(|app| {
            let mut settings = load_settings();

            if settings.data_root.is_empty() || !Path::new(&settings.data_root).exists() {
                // Desktop: ask where the library lives, once.
                // Mobile: there is no user-visible filesystem to browse, so the
                // library lives in app-private storage and is pushed there by
                // `adb push` (Android) rather than chosen in a dialog.
                #[cfg(desktop)]
                {
                    let picked = app
                        .dialog()
                        .file()
                        .set_title("Where is your Govorim library? (the folder holding books/ and audio/)")
                        .blocking_pick_folder();
                    match picked {
                        Some(p) => settings.data_root = p.to_string(),
                        None => {
                            eprintln!("No data folder chosen — exiting.");
                            std::process::exit(0);
                        }
                    }
                }
                #[cfg(mobile)]
                {
                    let dir = app
                        .path()
                        .app_data_dir()
                        .expect("no app data dir")
                        .join("library");
                    let _ = fs::create_dir_all(&dir);
                    settings.data_root = dir.to_string_lossy().to_string();
                }
                save_settings(&settings);
            }

            let port = free_port();
            let s = Arc::new(settings);
            std::thread::spawn(move || serve(s, port));

            let url = format!("http://127.0.0.1:{port}/");
            tauri::WebviewWindowBuilder::new(
                app,
                "main",
                tauri::WebviewUrl::External(url.parse().unwrap()),
            )
            .title("Говорим")
            .inner_size(1280.0, 860.0)
            .build()?;
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running Govorim");
}
