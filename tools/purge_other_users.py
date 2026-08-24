#!/usr/bin/env python3
"""Delete every Govorim account except the owner's, from R2.

There is no delete path in the app itself, so this operates on the R2 objects
directly through the rclone remote `r2` already configured on this machine.
No credentials appear in this file.

What belongs to a user (see lib/auth.js and api/user-data.js):
    userdata/accounts/<sha256(email)>.json   the account record
    userdata/accounts/_index.json            emails + ids, powers the admin list
    userdata/<userId>/<type>.json            their vocab, bookmarks, progress

_index.json is REBUILT rather than deleted — dropping it would break the admin
Manage Users screen.

Forum posts (forum/<cat>/…) are reported but NOT touched: deleting an author's
account does not obviously mean deleting threads other people may have replied
to. Decide that separately.

    python3 tools/purge_other_users.py                 # dry run, changes nothing
    python3 tools/purge_other_users.py --apply         # do it (backs up first)
"""
import argparse, json, subprocess, sys, os, datetime

BUCKET = "r2:govorim-audio"
ACCOUNTS = BUCKET + "/userdata/accounts"
KEEP_DEFAULT = "david.andrew.delehanty@gmail.com"


def rclone(*args, check=True):
    env = dict(os.environ, RCLONE_S3_NO_CHECK_BUCKET="true")
    r = subprocess.run(["rclone", *args], capture_output=True, text=True, env=env)
    if check and r.returncode != 0:
        sys.exit("rclone %s failed:\n%s" % (" ".join(args[:2]), r.stderr.strip()))
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", default=KEEP_DEFAULT, help="email to preserve")
    ap.add_argument("--apply", action="store_true", help="actually delete")
    a = ap.parse_args()
    keep = a.keep.strip().lower()

    listing = [f for f in rclone("lsf", ACCOUNTS + "/").split("\n")
               if f.endswith(".json") and f != "_index.json"]
    if not listing:
        sys.exit("No account files found — check the rclone remote and bucket path.")

    keep_rows, drop_rows = [], []
    for fname in listing:
        raw = rclone("cat", "%s/%s" % (ACCOUNTS, fname))
        try:
            acct = json.loads(raw)
        except json.JSONDecodeError:
            print("  !! unreadable, skipping: %s" % fname)
            continue
        row = (fname, acct.get("email", ""), acct.get("id", ""))
        (keep_rows if row[1].strip().lower() == keep else drop_rows).append(row)

    print("Accounts found : %d" % len(listing))
    print("Keeping        : %d  (%s)" % (len(keep_rows), keep))
    print("Deleting       : %d" % len(drop_rows))
    if not keep_rows:
        sys.exit("\nABORT: no account matches --keep %s. Nothing was changed.\n"
                 "Check the email, or the owner account may not exist yet." % keep)
    for _, email, uid in drop_rows:
        print("   - %s   (%s)" % (email, uid))

    if not a.apply:
        print("\nDry run — nothing changed. Re-run with --apply to delete.")
        return

    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    backup = os.path.expanduser("~/govorim-userdata-backup-%s" % stamp)
    print("\nBacking up all userdata/ to %s …" % backup)
    rclone("copy", BUCKET + "/userdata/", backup, "--progress")

    for fname, email, uid in drop_rows:
        print("deleting %s" % email)
        rclone("deletefile", "%s/%s" % (ACCOUNTS, fname))
        if uid:
            rclone("purge", "%s/userdata/%s" % (BUCKET, uid), check=False)

    idx = [{"email": e, "id": i} for _, e, i in keep_rows]
    tmp = "/tmp/_index.json"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(idx, f, ensure_ascii=False)
    rclone("copyto", tmp, ACCOUNTS + "/_index.json")
    print("\nRebuilt _index.json with %d account(s)." % len(idx))

    posts = rclone("lsf", BUCKET + "/forum/", "--recursive", check=False)
    n = len([p for p in posts.split("\n") if p.endswith(".json")])
    if n:
        print("\nNote: %d forum object(s) still in R2 under forum/ — authored by\n"
              "accounts that may no longer exist. Left alone deliberately." % n)
    print("\nDone. Backup: %s" % backup)


if __name__ == "__main__":
    main()
