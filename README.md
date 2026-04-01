# Pokemon TCG Video Generator

An automated pipeline that fetches the most expensive Pokemon TCG cards for a set expansion, renders a portrait-format video with price overlays and crossfade transitions, and uploads it as a YouTube Short — fully automated via GitHub Actions, running 5 times a day without any manual intervention.

## What It Does

Every run goes through the same four stages:

**1. Fetch expansion & cards**
Queries the Pokemon TCG API (via RapidAPI) to pick the next unused expansion and retrieves its top 15 most expensive cards ranked by market price. A state file (`db/state.json`) tracks which expansions have already been covered so no set is repeated. The list resets automatically at the start of each month.

**2. Generate the video**
Builds a 1080×1980 portrait video using Pillow and MoviePy:
- A header slide with the expansion logo and current month/year
- One slide per card showing the card image, its rank, name, and market price
- An ending slide crediting the background music
- Smooth crossfade transitions between every slide

**3. Add background music**
Downloads a random audio track from a private Google Drive folder, then loops or trims it to exactly match the video length.

**4. Upload to YouTube**
Publishes the finished video as a public YouTube Short with an auto-generated title, description, and hashtags built from the expansion name and music info.

## Project Structure

```
.
├── main.py                     # Entry point — orchestrates the full pipeline
├── app/
│   ├── TCGApi.py               # RapidAPI Pokemon TCG client + state management
│   ├── VideoCreation.py        # Image composition & video rendering
│   └── UploadContent.py        # YouTube Data API v3 upload
├── auth/
│   └── google_auth.py          # Google OAuth2 helper (env vars or pickle token)
├── backgrounds/                # Background images used across video frames
├── font/                       # Bangers-Regular.ttf (Pokemon-style font)
├── db/
│   └── state.json              # Tracks used expansions + last run date
└── .github/workflows/
    └── upload_video.yml        # GitHub Actions workflow
```

## Automation with GitHub Actions

The workflow runs on a cron schedule — 5 times a day at 10:00, 13:00, 16:00, 19:00, and 21:00 UTC. It can also be triggered manually from the GitHub UI.

After each successful run, the workflow commits the updated `db/state.json` back to the repository so the next run always knows where it left off. All credentials (RapidAPI key, YouTube OAuth, Drive OAuth) are stored as GitHub Actions secrets and injected at runtime — nothing sensitive lives in the codebase.

## Tech Stack

| Area | Tools |
|------|-------|
| Video rendering | MoviePy, Pillow, OpenCV |
| API communication | Requests, Google API Python Client |
| Image & text layout | Pillow (ImageDraw, ImageFont, ImageFilter) |
| Fuzzy name matching | TheFuzz |
| Auth | Google OAuth 2.0 (refresh token flow) |
| Automation | GitHub Actions |
