#!/bin/bash
# Auto-restart wrapper for boss-worker medium puzzles
# Keeps relaunching until all 30 puzzles are complete

cd /Users/masashakra/Desktop/game

MAX_ATTEMPTS=50
attempt=0

while [ $attempt -lt $MAX_ATTEMPTS ]; do
    attempt=$((attempt + 1))

    # Count how many puzzles are done
    RUN_DIR=$(ls -td output/runs/boss_worker_medium_deepseek_* 2>/dev/null | head -1)
    if [ -n "$RUN_DIR" ]; then
        done=$(ls "$RUN_DIR"/MM_*.json 2>/dev/null | wc -l | tr -d ' ')
    else
        done=0
    fi

    echo ""
    echo "================================================"
    echo " AUTO-RESTART WRAPPER — Attempt $attempt"
    echo " Puzzles done so far: $done/30"
    echo " $(date)"
    echo "================================================"

    # Check if all 30 are done
    if [ "$done" -ge 30 ]; then
        echo "All 30 puzzles complete! Exiting."
        break
    fi

    # Run the script
    python3 run_boss_worker_medium30.py 2>&1

    EXIT_CODE=$?
    echo ""
    echo "Script exited with code $EXIT_CODE"

    # Re-check after exit
    if [ -n "$RUN_DIR" ]; then
        done=$(ls "$RUN_DIR"/MM_*.json 2>/dev/null | wc -l | tr -d ' ')
    fi

    if [ "$done" -ge 30 ]; then
        echo "All 30 puzzles complete! Done."
        break
    fi

    echo "Only $done/30 done — restarting in 5 seconds..."
    sleep 5
done

echo "Wrapper finished after $attempt attempt(s)."
