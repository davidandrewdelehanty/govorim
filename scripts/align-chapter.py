#!/usr/bin/env python3
"""Align a single chapter MP3 + text file → per-chapter JSON."""
import argparse, json, os, tempfile

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True)
    ap.add_argument("--text", required=True)
    ap.add_argument("--audio-url", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--narrator", default="")
    ap.add_argument("--year", default="")
    ap.add_argument("--language", default="rus")
    args = ap.parse_args()

    from aeneas.executetask import ExecuteTask
    from aeneas.task import Task
    from aeneas.runtimeconfiguration import RuntimeConfiguration

    config_str = (
        f"task_language={args.language}|"
        "is_text_type=plain|"
        "os_task_file_format=json"
    )
    rconf = RuntimeConfiguration("tts=espeak-ng|tts_path=/usr/bin/espeak-ng")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as tf:
        tmp_out = tf.name

    try:
        task = Task(config_string=config_str, rconf=rconf)
        task.audio_file_path_absolute = os.path.abspath(args.audio)
        task.text_file_path_absolute = os.path.abspath(args.text)
        task.sync_map_file_path_absolute = tmp_out
        ExecuteTask(task, rconf=rconf).execute()
        task.output_sync_map_file()
        with open(tmp_out, encoding="utf-8") as f:
            sync = json.load(f)
        frags = []
        for f in sync.get("fragments", []):
            begin = float(f["begin"])
            end = float(f["end"])
            if end <= begin: continue
            text = " ".join((f.get("lines") or [""])).strip()
            if not text: continue
            frags.append({
                "begin": round(begin, 3),
                "end":   round(end, 3),
                "text":  text,
            })
        out = {
            "version": 1,
            "language": args.language,
            "audio_url": args.audio_url,
            "fragments": frags,
        }
        if args.narrator: out["narrator"] = args.narrator
        if args.year:     out["year"]     = args.year
        os.makedirs(os.path.dirname(args.out), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
        print(f"  {len(frags)} fragments → {os.path.basename(args.out)}")
    finally:
        try: os.unlink(tmp_out)
        except: pass

if __name__ == "__main__":
    main()
