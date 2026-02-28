# InstaGrow — Cinematic Reel Automation

InstaGrow is a premium automation suite for generating and posting cinematic Instagram Reels.

## Project Structure

- **`agents/`**: High-level automation agents.
  - `content_flood.py`: Batch generation of premium reels.
  - `instagram_agent.py`: Automated posting to Instagram Graph API.
  - `generate_quotes_agent.py`: AI-driven quote generation.
- **`engine/`**: Core generation logic.
  - `generate_reels.py`: The cinematic rendering engine.
  - `fetch_pexels_video.py`: Background asset fetcher.
  - `trending_audio.py`: Contextual music selector.
- **`assets/`**: Brand assets, fonts, and local audio library.
- **`data/`**: Content calendar (`content_calendar.csv`) and quotes.
- **`output/`**: Final rendered reels.
- **`logs/`**: Execution and debug logs.

## Setup

1. Copy `.env.template` to `.env` and fill in your keys.
2. Install dependencies: `pip install -r requirements.txt`.

## Usage

1. **Generate Quotes**: `python agents/generate_quotes_agent.py`
2. **Generate Reels**: `python agents/content_flood.py`
3. **Post to Instagram**: `python agents/instagram_agent.py`
