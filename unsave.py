"""
unsave.py — remove archived posts from your Reddit saves.

DESTRUCTIVE. Only unsaves items listed in reddit_saves/_manifest.json, i.e.
posts that extract.py successfully wrote to disk.

    python unsave.py            -> dry run (prints what it would do, changes nothing)
    python unsave.py --confirm  -> actually unsaves each item

Resumable: already-unsaved items are recorded in _unsaved_log.json and skipped
on re-runs.
"""
from __future__ import annotations

import datetime as dt
import json
import sys

from reddit_common import MANIFEST_PATH, UNSAVE_LOG_PATH, get_reddit


def load_json(path, default):
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return default


def main() -> None:
    confirm = "--confirm" in sys.argv[1:]

    if not MANIFEST_PATH.exists():
        sys.exit(f"No manifest found at {MANIFEST_PATH}. Run extract.py first.")

    manifest = load_json(MANIFEST_PATH, [])
    if not manifest:
        sys.exit("Manifest is empty — nothing to unsave.")

    log = load_json(UNSAVE_LOG_PATH, [])
    already_done = {entry["fullname"] for entry in log if entry.get("status") == "unsaved"}

    todo = [m for m in manifest if m["fullname"] not in already_done]

    print(f"Manifest items      : {len(manifest)}")
    print(f"Already unsaved      : {len(already_done)}")
    print(f"To unsave this run   : {len(todo)}")
    print()

    if not confirm:
        print("DRY RUN — nothing will be changed. These would be unsaved:\n")
        for m in todo:
            print(f"  r/{m['subreddit']} — {m['title'][:70]}")
        print("\nRe-run with --confirm to actually unsave them.")
        return

    if not todo:
        print("Nothing left to unsave.")
        return

    reddit = get_reddit()
    unsaved = 0
    errors = 0

    for m in todo:
        try:
            # Reconstruct the submission from its fullname (t3_xxx) and unsave.
            submission = reddit.submission(id=m["id"])
            submission.unsave()
            log.append(
                {
                    "fullname": m["fullname"],
                    "id": m["id"],
                    "title": m["title"],
                    "subreddit": m["subreddit"],
                    "status": "unsaved",
                    "at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                }
            )
            unsaved += 1
            print(f"  unsaved: r/{m['subreddit']} — {m['title'][:70]}")
        except Exception as exc:  # noqa: BLE001
            errors += 1
            log.append(
                {
                    "fullname": m["fullname"],
                    "id": m["id"],
                    "title": m["title"],
                    "status": "error",
                    "error": str(exc),
                    "at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                }
            )
            print(f"  ! error unsaving {m['id']}: {exc}")

        # Persist the log after every item so the run is fully resumable.
        UNSAVE_LOG_PATH.write_text(
            json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print("\n" + "=" * 50)
    print(f"Unsaved this run : {unsaved}")
    print(f"Errors           : {errors}")
    print(f"Log              : {UNSAVE_LOG_PATH}")
    print("=" * 50)


if __name__ == "__main__":
    main()
