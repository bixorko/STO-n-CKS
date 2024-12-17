#!/bin/bash

# Function to calculate next trigger time (HH:00:02 or HH:30:02)
calculate_next_time() {
    CURRENT_TIME=$(date +%s)
    CURRENT_HOUR=$(date +%H)
    CURRENT_MIN=$(date +%M)

    # Determine the next closest time: XX:00:02 or XX:30:02
    if [ "$CURRENT_MIN" -lt 30 ]; then
        TARGET_MIN="00"
    else
        # If past 30 minutes, go to the next hour
        TARGET_MIN="30"
        CURRENT_HOUR=$(printf "%02d" $((10#$CURRENT_HOUR + 1)))
    fi

    # Construct the full timestamp for the next trigger time
    TARGET_TIME_STR=$(date -d "${CURRENT_HOUR}:${TARGET_MIN}:02" +%s)

    # Calculate the wait time
    WAIT_TIME=$((TARGET_TIME_STR - CURRENT_TIME))

    # Ensure wait time is not negative
    if [ $WAIT_TIME -lt 0 ]; then
        WAIT_TIME=0
    fi

    echo "Waiting for $WAIT_TIME seconds until the next trigger time..."
    sleep $WAIT_TIME
}

# Calculate and wait for the next time slot
calculate_next_time

# Start the Python script
echo "Starting Claude script..."
python claude.py