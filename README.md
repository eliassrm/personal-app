# Reddit Saves Archiver

Archives your Reddit **saved posts** to local text files (one folder per
subreddit, including each post's top comments), then optionally **unsaves**
them from your account — in two deliberate steps so nothing is removed before
you've reviewed it.

## 1. Create a Reddit app (one time)

1. Go to <https://www.reddit.com/prefs/apps>.
2. Click **create another app...** at the bottom.
3. Fill in:
   - **name:** anything, e.g. `saves-archiver`
   - type: select **script**
   - **redirect uri:** `http://localhost:8080` (required but unused)
4. Click **create app**.
5. Note the two values:
   - **client id** — the string just under the app name (near "personal use script")
   - **secret** — the `secret` field

## 2. Configure credentials

```powershell
copy .env.example .env
```

Open `.env` and fill in your client id, secret, Reddit username, and password.
`.env` is git-ignored and never leaves your machine.

## 3. Install dependencies

```powershell
pip install -r requirements.txt
```

(Optional but recommended: create a virtual env first —
`python -m venv .venv ; .\.venv\Scripts\Activate.ps1`)

## 4. Extract (safe, read-only)

```powershell
python extract.py
```

Produces:

```
reddit_saves/
  <subreddit>/<YYYY-MM-DD>_<title>.txt
  _manifest.json   # list of archived posts — drives unsaving
  _index.md        # master table of everything archived
```

Run it as many times as you like; it never changes your account.

## 5. Review

Open `reddit_saves/_index.md` and browse the per-subreddit folders. Make sure
everything you care about is captured.

## 6. Unsave (destructive — only when ready)

```powershell
python unsave.py            # DRY RUN: prints what it would unsave, changes nothing
python unsave.py --confirm  # actually unsaves the archived posts
```

Only posts present in `_manifest.json` are unsaved, so nothing gets removed
that wasn't archived first. Progress is written to `_unsaved_log.json` after
every item, so the run is safely resumable if interrupted.

## Notes

- **Scope:** saved *posts* only (saved comments are skipped), plus the top 10
  comments on each post. Change `TOP_COMMENTS` in `reddit_common.py` to adjust.
- **Deleted/removed posts:** handled gracefully; body/comments may be missing.
- **Rate limits:** PRAW throttles automatically; large accounts just take a
  while. Per-item errors are logged and the run continues.
- **Two-factor auth:** if your account uses 2FA, set the password in `.env` to
  `password:123456` (your password, a colon, then the current 6-digit code).
  A password-only login won't work with 2FA enabled.
