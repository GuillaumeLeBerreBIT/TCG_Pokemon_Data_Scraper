# YouTube Shorts Video Improvements — Design

**Date:** 2026-07-12
**Status:** Approved

## Goal

Improve retention and watch quality of the auto-generated "most expensive cards" Shorts:
faster pacing with more cards, price shown on the card itself, a hook opening, and subtle
motion on each card. Total video stays under 60 seconds so the Short loops.

Out of scope this round (candidates for later): per-Pokémon videos (e.g. "Top 10 Charizard
cards"), price-history snapshots for "biggest gainers" videos.

## Changes

### 1. Pacing & card count (20 cards in ~60s)

- `VideoCreation.clip_duration`: 4 → 2.5 seconds; `fade_duration`: 1 → 0.5 seconds.
  Net time per card ≈ 2.0s.
- `TCGApi.retrieve_cards_list`: raise the card cap from 15 to 20 (both the early-break
  and the final slice). Bump the API `per_page` from 20 to 30 so failed image downloads
  don't leave the video short of 20 cards.
- `TCGApi.get_cards_expansion`: **keep** the ≥15-cards threshold. Raising it to 20 would
  skip small expansions; instead videos show *up to* 20 cards and the actual count flows
  into titles/filenames dynamically (§5).
- Rough timeline: 2s hook + 2.5s logo header + 20×2s cards + ending ≈ 48s; the existing
  pad-to-60s logic on the ending clip absorbs the remainder.

### 2. Price overlay on the card

- In `VideoCreation.process_cards`, draw the price right-aligned just **above the card's
  top-right corner**, using the already-computed card `x_offset`/`y_offset`. Top-right
  because rank+name text is top-center and Pokémon card names print top-left.
- Text shortens from `Market Price: $123.45` to `$123.45` (long prefix overflows the card
  width at font size 120). The old bottom-center price line is removed.
- Rank + card name stay top-center, unchanged.

### 3. Hook intro (~2s)

- New `VideoCreation.create_hook_image`: blurred background + the **#1 most expensive
  card** + large text like `This card is worth $340!?` (price taken from that card).
- Clip order becomes: hook (~2s) → expansion-logo header (2.5s) → countdown from #N up
  to #1 (unchanged order) → ending/music-credit clip. The hook teases the top price but
  the countdown still builds to the #1 reveal.

### 4. Ken Burns zoom on card clips

- Each card clip gets a subtle time-varying scale (~1.00 → 1.04 over its duration) via
  moviepy `resized`, composited so the frame stays 1080×1980. Alternate zoom-in /
  zoom-out per card. Hook, header, and ending clips stay static.

### 5. Metadata consistency

- `UploadContent.initialize_upload`: replace hardcoded "Top 15" in title and description
  with the actual card count (`Top {n}`), passed through from video creation.
- Output filename `TOP_10_EXPENSIVE_CARDS_…` in `VideoCreation.create_composite_clip`
  becomes `TOP_{n}_EXPENSIVE_CARDS_…`.

## Data flow

`TCGApi.get_cards_expansion()` → up to 20 cards → `VideoCreation.build_clip()` returns
`(video_path, expansion_full_name, song_name, card_count)` → `UploadContentYouTube`
uses `card_count` for title/description.

## Error handling

No changes to API-retry, state tracking, or upload behavior. Card-count logic must
tolerate fewer than 20 cards (small sets) everywhere it is displayed.

## Verification

Run `main.py` up to video creation (skip upload) and check the output mp4: hook plays
first, price badge sits above the card's top-right corner, cards advance ~every 2s with
subtle zoom, total length ≤ 60s, title/filename card counts match the actual number of
cards shown.
