# Crossplay Radar

An English-language, mobile-friendly directory for discovering **PS5 ↔ PC crossplay games**.

## Features
- Search by game title, genre, or studio
- Filter by genre, free/paid, and status
- Separate **Available**, **Upcoming**, and **Needs verification** lists
- Game cover art where available
- Source-discovery links

## Data quality
This is a **starter catalog, not an exhaustive or fully verified database**. Status entries are editorial leads, not real-time guarantees. Crossplay may be restricted by game mode, generation, account, region, or platform. The "Upcoming" tab is a watchlist and is not a confirmed release-date calendar.

The weekly GitHub Actions workflow validates the JSON structure and catches duplicate titles. **It does not automatically research or update crossplay status.** Editorial verification and a licensed authoritative data feed are still needed before claiming automated status updates.

## Publish with GitHub Pages
Go to **Settings → Pages → Build and deployment → Source: Deploy from a branch → main → / (root) → Save**.

Expected URL after GitHub Pages activates:
https://vetrix999-lab.github.io/crossplay-radar/

## Data editing
Edit `data/games.json` and commit the change. Each entry includes a status, platform tags, and a link for researching publisher evidence. Prefer replacing generic search links with direct official documentation after verification.

## License
Code is provided for this repository. Third-party game artwork and names remain the property of their respective owners.
