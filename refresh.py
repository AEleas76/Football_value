"""One command to bring the website up to date:  python refresh.py
  1. (if APIFOOTBALL_KEY is set) fetch current stats / World Cup / summer transfers   -> data/live/*.csv
  2. rebuild the predictions (re-scores players who moved clubs)                       -> api/predictions.json
  3. rebuild the statistics (adds the season in progress)                              -> api/stats.json
Then restart the API (uvicorn) and refresh the browser.
Needs the trained pipeline to have been run once (build_* scripts, train_model.py).
"""
import os, subprocess, sys

steps = []
if os.environ.get("APIFOOTBALL_KEY"):
    steps.append([sys.executable, "update_live.py", "--max-requests", "90", "--world-cup", "--transfers"])
else:
    print("APIFOOTBALL_KEY is not set: skipping the live download (see update_live.py for how to get a free key).")
steps += [[sys.executable, "export_predictions.py"], [sys.executable, "export_stats.py"]]

for cmd in steps:
    print("\n>>", " ".join(cmd))
    if subprocess.run(cmd).returncode != 0:
        sys.exit(f"Stopped: {' '.join(cmd[1:])} failed (see the message above).")
print("\nDone. Restart the API and refresh the browser.")