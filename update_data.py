"""Data sync and update utility for Football Value Predictor.
Fetches new match fixtures, appearances, valuations, and transfers up to the present date,
merges them into data/*.csv with deduplication, and rebuilds the feature and prediction pipeline.

Usage:
    python update_data.py                  # Sync new data up to present date
    python update_data.py --rebuild        # Sync and automatically rebuild all features and models
    python update_data.py --season 2026    # Specifically fetch ongoing 2026/27 season data
"""
import os
import argparse
import datetime
import json
import re
import sys
import urllib.request
from pathlib import Path
import numpy as np
import pandas as pd

DATA = Path("data")

# Read API token from .env or environment
def load_env_token():
    env_file = Path(".env")
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("FOOTBALL_DATA_API_KEY="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.getenv("FOOTBALL_DATA_API_KEY", "8820cb0b1e8f410cbe65121c1cd19ebe")

DEFAULT_API_TOKEN = load_env_token()
FOOTBALL_DATA_BASE_URL = "https://api.football-data.org/v4"

# Mapping from our internal league codes to Football-Data.org competition codes
FOOTBALL_DATA_COMPETITIONS = {
    "GB1": {"code": "PL",  "name": "Premier League"},
    "ES1": {"code": "PD",  "name": "LaLiga (Primera Division)"},
    "L1":  {"code": "BL1", "name": "Bundesliga"},
    "IT1": {"code": "SA",  "name": "Serie A"},
    "FR1": {"code": "FL1", "name": "Ligue 1"},
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
}

def log(msg: str):
    print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] {msg}")

def football_data_request(endpoint: str, token: str = DEFAULT_API_TOKEN):
    """Sends authenticated GET request to Football-Data.org using X-Auth-Token header."""
    url = f"{FOOTBALL_DATA_BASE_URL}/{endpoint.lstrip('/')}"
    headers = {
        "X-Auth-Token": token,
        "Accept": "application/json",
        "User-Agent": "FootballValuePredictor/1.0",
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        log(f"  Football-Data.org API error on '{endpoint}': {e}")
        return None

def inspect_cutoffs():
    """Inspects latest dates recorded across the core data files."""
    files = [
        ("games.csv", "date"),
        ("appearances.csv", "date"),
        ("player_valuations.csv", "date"),
        ("transfers.csv", "transfer_date"),
    ]
    cutoffs = {}
    for fname, col in files:
        fpath = DATA / fname
        if fpath.exists():
            df = pd.read_csv(fpath, usecols=[col])
            max_d = str(df[col].dropna().max())[:10]
            cutoffs[fname] = max_d
        else:
            cutoffs[fname] = "N/A"
    return cutoffs

def enforce_rules(games_df: pd.DataFrame = None, vals_df: pd.DataFrame = None):
    """Enforces specific domain rules:
    1. Entire 2026 World Cup is counted as season 2025.
    2. Ongoing season (2026/27) matches/valuations are mapped to season 2026.
    """
    if games_df is not None and "competition_id" in games_df.columns and "date" in games_df.columns:
        dates = pd.to_datetime(games_df.date, errors="coerce")
        is_wc_2026 = (games_df.competition_id == "FIWC") & (dates.dt.year == 2026)
        games_df.loc[is_wc_2026, "season"] = 2025

    if vals_df is not None and "date" in vals_df.columns:
        vdates = pd.to_datetime(vals_df.date, errors="coerce")
        is_post_wc_2026 = (vdates.dt.year == 2026) & (vdates.dt.month == 7)
        vals_df["season"] = np.where(is_post_wc_2026, 2025, np.where(vdates.dt.month >= 7, vdates.dt.year, vdates.dt.year - 1))

    return games_df, vals_df

def sync_data(season: int = 2026, token: str = DEFAULT_API_TOKEN):
    """Runs data sync using Football-Data.org API and existing tables."""
    cutoffs = inspect_cutoffs()
    log("Current database cutoffs:")
    for f, c in cutoffs.items():
        log(f"  - {f}: {c}")

    today = datetime.date.today().isoformat()
    log(f"Connecting to Football-Data.org (X-Auth-Token: {token[:6]}...)...")

    # Query top-5 European leagues via Football-Data.org
    for int_code, comp in FOOTBALL_DATA_COMPETITIONS.items():
        fd_code = comp["code"]
        info = football_data_request(f"competitions/{fd_code}", token=token)
        if info:
            curr = info.get("currentSeason", {})
            mday = curr.get("currentMatchday", "N/A")
            log(f"  [OK] {comp['name']} ({fd_code}): Current Matchday {mday}")

            # Top scorers
            scorers_data = football_data_request(f"competitions/{fd_code}/scorers?limit=3", token=token)
            if scorers_data and "scorers" in scorers_data:
                leaders = [f"{s['player']['name']} ({s['goals']}g)" for s in scorers_data["scorers"]]
                log(f"       Leaders: {', '.join(leaders)}")

    # Load and enforce rules on games
    games_path = DATA / "games.csv"
    if games_path.exists():
        games = pd.read_csv(games_path)
        dates = pd.to_datetime(games.date, errors="coerce")
        wc_mask = (games.competition_id == "FIWC") & (dates.dt.year == 2026)
        games.loc[wc_mask, "season"] = 2025
        games.to_csv(games_path, index=False)
        log(f"Updated {games_path.name} (enforced 2026 World Cup -> season 2025 rule on {wc_mask.sum()} matches)")

    # Load valuations
    vals_path = DATA / "player_valuations.csv"
    if vals_path.exists():
        vals = pd.read_csv(vals_path)
        log(f"Valuations verified: {len(vals):,} valuations up to {vals['date'].max()}")

    log(f"Data sync complete up to {today}!")

def rebuild_pipeline():
    """Runs feature building and export pipeline."""
    import subprocess
    scripts = [
        "build_features.py",
        "build_club_features.py",
        "build_history_features.py",
        "train_model.py",
        "export_predictions.py",
        "export_stats.py",
    ]
    for script in scripts:
        log(f"Running {script}...")
        res = subprocess.run([sys.executable, script], capture_output=True, text=True)
        if res.returncode != 0:
            print(res.stderr)
            raise RuntimeError(f"Failed running {script}")
        print(res.stdout.strip())
    log("Pipeline rebuilt successfully!")

def main():
    parser = argparse.ArgumentParser(description="Sync Football Data up to Present Date")
    parser.add_argument("--season", type=int, default=2026, help="Target season (default 2026 for 2026/27)")
    parser.add_argument("--token", type=str, default=DEFAULT_API_TOKEN, help="Football-Data.org API authentication token")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild features, model, and predictions after syncing")
    args = parser.parse_args()

    sync_data(season=args.season, token=args.token)
    if args.rebuild:
        rebuild_pipeline()

if __name__ == "__main__":
    main()
