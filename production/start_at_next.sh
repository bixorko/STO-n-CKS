#!/bin/bash

# Function to calculate next trigger time (HH:00:02 or HH:30:02)
calculate_next_time() {
    CURRENT_MIN=$(date +%M)
    CURRENT_SEC=$(date +%S)

    # Determine if the closest time is XX:00 or XX:30
    if [ "$CURRENT_MIN" -lt 30 ]; then
        TARGET_MIN=0
    else
        TARGET_MIN=30
    fi

    # Wait until XX:TARGET_MIN:02
    TARGET_TIME=$(date -d "today $TARGET_MIN:02" +%s)
    CURRENT_TIME=$(date +%s)

    # If the time already passed, set for the next hour
    if [ "$CURRENT_TIME" -ge "$TARGET_TIME" ]; then
        TARGET_TIME=$(date -d "1 hour $TARGET_MIN:02" +%s)
    fi

    WAIT_TIME=$((TARGET_TIME - CURRENT_TIME))
    echo "Waiting for $WAIT_TIME seconds until the next trigger time..."
    sleep $WAIT_TIME
}

# Calculate and wait for the next time slot
calculate_next_time

# Start the Python script
echo "Starting Claude script..."
python claude.py
