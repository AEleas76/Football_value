# Football Value Predictor

A full-stack machine learning application that predicts, explains, and tracks the market valuations of footballers across Europe's top five leagues (Premier League, LaLiga, Serie A, Bundesliga, Ligue 1).

Powered by **XGBoost** with Tree SHAP explainability, a **FastAPI** backend, and a modern **React + Vite** frontend.

---

## Key Highlights

- **Predictive Modeling ($R^2 \approx 0.87$, ~25% Median Error)**: Predicts player transfer values using match aggregates, playing time trends, opposition strength, and multi-season performance history.
- **Explainable Estimates (Tree SHAP)**: Breaks down every prediction into human-readable percentage drivers (Age, Goals & Assists, Club Strength, Recent Big-Club Moves, European Football, etc.).
- **Transfer Step-Up Boost**: Factors in transfer market dynamics from `transfers.csv`—players transferring to significantly bigger clubs receive an explicit prestige boost in their valuation.
- **2026 FIFA World Cup Integration**: Counts the entire 2026 World Cup as part of the 2025–26 season, incorporating all knockout matches, tournament stats, and post-tournament market values.
- **Automated Data Sync**: Includes `update_data.py` and GitHub Actions workflows to ingest ongoing season data, keep the database current, and rebuild models automatically.
- **Transfermarkt-Style Visuals**: Full, uncropped 3:4 portrait player photos with automatic high-resolution image upscaling.
- **Interactive UI**:
  - **Player Profile**: Market valuation vs. model estimate, 80% confidence interval, key valuation drivers, contract details, and 5-season competition breakdowns.
  - **Head-to-Head Comparison**: Compare any two players side-by-side with grouped output charts.
  - **Season Explorer**: Filter and rank top-5 league players by goals, assists, G+A/90, minutes, or market value.
  - **Model vs. Market Discrepancies**: Find the most undervalued and overvalued players in Europe.

---

## Architecture & Project Structure

```
├── api/
│   ├── main.py                     # FastAPI REST API
│   ├── model.json                  # Serialized XGBoost model
│   ├── predictions.json            # Model estimates, 80% ranges, and explanation drivers
│   └── stats.json                  # 5-season competition stats and leaderboards
├── frontend/                       # React 18 + Vite frontend
│   ├── src/
│   │   ├── components/             # Avatar, PlayerCard, SearchBox, FiveYearStats, etc.
│   │   ├── pages/                  # Home, Player, Compare, SeasonsPage, StatsPage, GapsPage
│   │   ├── api.js                  # Frontend API client
│   │   └── format.js               # Formatting utilities (currency, dates, labels)
│   └── package.json
├── data/                           # Relational CSV dataset (games, appearances, valuations, etc.)
├── .github/workflows/
│   └── update_pipeline.yml         # Automated weekly GitHub Actions sync & rebuild
├── scripts/
│   └── schedule_updater.ps1        # Windows Task Scheduler automation script
├── build_features.py               # Feature building: match-level aggregations and targets
├── build_club_features.py          # Club squad strength & recent big-club move stepups
├── build_history_features.py       # Multi-season rolling weighted performance metrics
├── train_model.py                  # Model training (Ridge baseline & XGBoost) and evaluation
├── export_predictions.py           # Generates api/predictions.json with SHAP explanations
├── export_stats.py                 # Generates api/stats.json with player histories
├── update_data.py                  # Ingestion utility to fetch latest data and enforce rules
└── requirements.txt                # Python package dependencies
```

---

## Getting Started

### Prerequisites

- **Python 3.11+**
- **Node.js 18+** & **npm**

### 1. Backend Setup

1. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell)
   python -m venv venv
   .\venv\Scripts\Activate.ps1

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Data & Model Pipeline** (if building from source):
   ```bash
   python build_features.py
   python build_club_features.py
   python build_history_features.py
   python train_model.py
   python export_predictions.py
   python export_stats.py
   ```

4. **Start the FastAPI server**:
   ```bash
   uvicorn api.main:app --reload
   ```
   API will be live at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

### 2. Frontend Setup

1. **Install Node dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Start the Vite development server**:
   ```bash
   npm run dev
   ```
   Open your browser at `http://localhost:5173`.

---

## Data Synchronization & Automation

### Syncing Data to the Present Date
The sync script connects to [Football-Data.org](https://www.football-data.org/) using your personal API token (authenticated via the `X-Auth-Token` header) configured in `.env` (`FOOTBALL_DATA_API_KEY`):

```bash
# Sync data and enforce season mappings
python update_data.py

# Or specify a token directly via CLI
python update_data.py --token <YOUR_TOKEN>

# Sync data and automatically re-run the full pipeline
python update_data.py --rebuild
```

### Scheduled Automation
- **GitHub Actions**: [`.github/workflows/update_pipeline.yml`](.github/workflows/update_pipeline.yml) runs automatically every Monday at 04:00 UTC (after weekend matchdays).
- **Windows Task Scheduler**: Register a weekly local Windows task by executing:
  ```powershell
  powershell -ExecutionPolicy Bypass -File scripts\schedule_updater.ps1
  ```

---

## REST API Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/health` | `GET` | Health check, active season metadata, baseline value, and median error. |
| `/api/featured?limit=8` | `GET` | Most valuable players in the active season. |
| `/api/players/search?q={name}` | `GET` | Autocomplete search by player name (accents stripped). |
| `/api/players/{player_id}` | `GET` | Detailed player profile, model estimate, confidence interval, and drivers. |
| `/api/players/{player_id}/stats` | `GET` | 5-season historical statistics broken down by competition. |
| `/api/compare?a={id}&b={id}` | `GET` | Side-by-side data for two players. |
| `/api/gaps?direction=under\|over` | `GET` | Disagreements between model estimates and market values. |
| `/api/seasons/{season}/leaders` | `GET` | Top-5-league leaderboard filtered by position, league, or minimum minutes. |

---

## Data Attribution & Acknowledgements

- Historical structured data originates from the open-source [transfermarkt-datasets](https://github.com/dcaribou/transfermarkt-datasets) project by David Cariboo.
- Match statistics and player photos originate from [Transfermarkt](https://www.transfermarkt.com).