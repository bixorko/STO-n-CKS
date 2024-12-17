#!/bin/bash

# Function to calculate next trigger time (HH:00:02 or HH:30:02)
calculate_next_time() {
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)
    CURRENT_SEC=$(date +%S)

    # Determine the next closest time: XX:00:02 or XX:30:02
    if [ "$CURRENT_MIN" -lt 30 ]; then
        TARGET_MIN="00"
    else
        TARGET_MIN="30"
    fi

    TARGET_SEC="02"

    # Construct the full timestamp for today at XX:TARGET_MIN:02
    TARGET_TIME_STR="${CURRENT_HOUR}:${TARGET_MIN}:${TARGET_SEC}"
    TARGET_TIME=$(date -d "$TARGET_TIME_STR" +%s 2>/dev/null)

    # Handle edge case: if the time already passed, set it to the next hour
    if [ "$(date +%s)" -ge "$TARGET_TIME" ]; then
        TARGET_TIME=$(date -d "next hour ${TARGET_MIN}:${TARGET_SEC}" +%s)
    fi

    # Calculate the wait time
    CURRENT_TIME=$(date +%s)
    WAIT_TIME=$((TARGET_TIME - CURRENT_TIME))

    echo "Waiting for $WAIT_TIME seconds until the next trigger time..."
    sleep $WAIT_TIME
}

# Calculate and wait for the next time slot
calculate_next_time

# Start the Python script
echo "Starting Claude script..."
python claude.py
