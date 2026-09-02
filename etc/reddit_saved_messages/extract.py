"""
extract.py — read-only archive of your Reddit saved POSTS.

Safe to run repeatedly. It never unsaves anything.

For each saved post it writes:
    reddit_saves/<subreddit>/<YYYY-MM-DD>_<slug>.txt
containing the post metadata, body (or link target), and the top comments.

It also writes:
    reddit_saves/_manifest.json  (drives unsave.py)
    reddit_saves/_index.md       (human-readable master list)

Run:  python extract.py
"""
from __future__ import annotations

import datetime as dt
import json

import praw  # noqa: F401  (imported for type context / clear errors)

from reddit_common import (
    INDEX_PATH,
    MANIFEST_PATH,
    OUTPUT_DIR,
    TOP_COMMENTS,
    get_reddit,
    sanitize,
    unique_path,
)


def fmt_date(created_utc: float) -> str:
    return dt.datetime.fromtimestamp(created_utc, tz=dt.timezone.utc).strftime("%Y-%m-%d")


def post_body(submission) -> str:
    """Return the readable body: selftext for text posts, else the link target."""
    if getattr(submission, "is_self", False):
        text = submission.selftext or ""
        return text if text.strip() else "(empty text post)"

    kind = "link"
    if getattr(submission, "is_video", False):
        kind = "video"
    elif getattr(submission, "is_gallery", False):
        kind = "gallery"
    elif str(getattr(submission, "post_hint", "")) == "image":
        kind = "image"
    return f"[{kind} post]\nURL: {submission.url}"


def top_comments(submission) -> list[dict]:
    """Top-level comments, highest score first, capped at TOP_COMMENTS."""
    try:
        submission.comments.replace_more(limit=0)
        top = [c for c in submission.comments if getattr(c, "body", None)]
        top.sort(key=lambda c: getattr(c, "score", 0), reverse=True)
        out = []
        for c in top[:TOP_COMMENTS]:
            out.append(
                {
                    "author": str(c.author) if c.author else "[deleted]",
                    "score": getattr(c, "score", 0),
                    "body": c.body,
                }
            )
        return out
    except Exception as exc:  # noqa: BLE001
        print(f"    ! could not load comments: {exc}")
        return []


def render(submission, comments: list[dict]) -> str:
    lines = []
    lines.append(submission.title or "(no title)")
    lines.append("=" * min(len(submission.title or "x"), 100))
    lines.append("")
    lines.append(f"Subreddit : r/{submission.subreddit.display_name}")
    lines.append(f"Author    : u/{submission.author if submission.author else '[deleted]'}")
    lines.append(f"Date      : {fmt_date(submission.created_utc)}")
    lines.append(f"Score     : {submission.score}")
    lines.append(f"Permalink : https://www.reddit.com{submission.permalink}")
    lines.append("")
    lines.append("-" * 60)
    lines.append("POST")
    lines.append("-" * 60)
    lines.append(post_body(submission))
    lines.append("")
    if comments:
        lines.append("-" * 60)
        lines.append(f"TOP {len(comments)} COMMENTS")
        lines.append("-" * 60)
        for i, c in enumerate(comments, 1):
            lines.append(f"\n[{i}] u/{c['author']}  ({c['score']} points)")
            lines.append(c["body"])
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    reddit = get_reddit()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest: list[dict] = []
    index_rows: list[str] = []
    skipped = 0
    errors = 0

    print("Fetching saved items (this can take a while for large accounts)...")
    saved = reddit.user.me().saved(limit=None)

    for saved_index, item in enumerate(saved):
        # Skip saved comments; we only archive posts.
        if not isinstance(item, praw.models.Submission):
            skipped += 1
            continue

        try:
            title = item.title or "(no title)"
            subreddit = item.subreddit.display_name
            date = fmt_date(item.created_utc)

            sub_dir = OUTPUT_DIR / sanitize(subreddit, max_len=60)
            sub_dir.mkdir(parents=True, exist_ok=True)

            filename = f"{date}_{sanitize(title)}.txt"
            path = unique_path(sub_dir / filename)

            comments = top_comments(item)
            path.write_text(render(item, comments), encoding="utf-8")

            rel = path.relative_to(OUTPUT_DIR).as_posix()
            manifest.append(
                {
                    "id": item.id,
                    "fullname": item.fullname,   # e.g. "t3_abc123" — used to unsave
                    "subreddit": subreddit,
                    "title": title,
                    "saved_index": saved_index,
                    "file_path": rel,
                    "permalink": f"https://www.reddit.com{item.permalink}",
                    "extracted_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                }
            )
            index_rows.append(
                f"| {title.replace('|', '/')} | r/{subreddit} | {date} | "
                f"[link](https://www.reddit.com{item.permalink}) | `{rel}` |"
            )
            print(f"  saved: r/{subreddit} — {title[:70]}")

        except Exception as exc:  # noqa: BLE001
            errors += 1
            print(f"  ! error on item {getattr(item, 'id', '?')}: {exc}")

    # Write manifest.
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")

    # Write human-readable index.
    header = (
        "# Reddit saved posts — index\n\n"
        f"Total posts archived: **{len(manifest)}**  \n"
        f"Generated: {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        "| Title | Subreddit | Date | Reddit | Local file |\n"
        "|---|---|---|---|---|\n"
    )
    INDEX_PATH.write_text(header + "\n".join(index_rows) + "\n", encoding="utf-8")

    print("\n" + "=" * 50)
    print(f"Archived posts : {len(manifest)}")
    print(f"Skipped (non-post saves): {skipped}")
    print(f"Errors         : {errors}")
    print(f"Output folder  : {OUTPUT_DIR}")
    print(f"Manifest       : {MANIFEST_PATH.name}")
    print(f"Index          : {INDEX_PATH.name}")
    print("=" * 50)
    print("\nReview the files. When ready to remove them from your account:")
    print("  python unsave.py            (dry run — shows what would be unsaved)")
    print("  python unsave.py --confirm  (actually unsaves)")


if __name__ == "__main__":
    main()
