"""Shared helpers for the Reddit saves archiver."""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    import praw
except ImportError:
    sys.exit("praw is not installed. Run:  pip install -r requirements.txt")

try:
    from dotenv import load_dotenv
except ImportError:
    sys.exit("python-dotenv is not installed. Run:  pip install -r requirements.txt")


# Root output folder (created next to this script).
OUTPUT_DIR = Path(__file__).resolve().parent / "reddit_saves"
MANIFEST_PATH = OUTPUT_DIR / "_manifest.json"
INDEX_PATH = OUTPUT_DIR / "_index.md"
UNSAVE_LOG_PATH = OUTPUT_DIR / "_unsaved_log.json"

# How many top comments to include per post.
TOP_COMMENTS = 10

# Characters Windows forbids in file/folder names.
_ILLEGAL = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
# Windows reserved device names.
_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def get_reddit() -> "praw.Reddit":
    """Build an authenticated PRAW client from environment variables."""
    load_dotenv(Path(__file__).resolve().parent / ".env")

    required = [
        "REDDIT_CLIENT_ID",
        "REDDIT_CLIENT_SECRET",
        "REDDIT_USERNAME",
        "REDDIT_PASSWORD",
        "REDDIT_USER_AGENT",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        sys.exit(
            "Missing environment variables: "
            + ", ".join(missing)
            + "\nCopy .env.example to .env and fill it in."
        )

    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )
    # Fail early with a clear message if auth is wrong.
    try:
        me = reddit.user.me()
    except Exception as exc:  # noqa: BLE001
        sys.exit(f"Reddit authentication failed: {exc}")
    if me is None:
        sys.exit("Reddit authentication returned no user. Check your credentials.")
    print(f"Authenticated as u/{me}")
    return reddit


def sanitize(name: str, max_len: int = 80) -> str:
    """Make a string safe to use as a Windows file/folder name."""
    name = _ILLEGAL.sub("", name)
    name = name.strip().strip(".")          # no trailing dots/spaces on Windows
    name = re.sub(r"\s+", "-", name)         # spaces -> dashes
    name = re.sub(r"-{2,}", "-", name)       # collapse repeats
    if not name:
        name = "untitled"
    if name.upper() in _RESERVED:
        name = f"_{name}"
    return name[:max_len].strip("-.") or "untitled"


def unique_path(path: Path) -> Path:
    """Return a non-colliding path by adding _1, _2, ... before the suffix."""
    if not path.exists():
        return path
    stem, suffix, parent = path.stem, path.suffix, path.parent
    i = 1
    while True:
        candidate = parent / f"{stem}_{i}{suffix}"
        if not candidate.exists():
            return candidate
        i += 1
