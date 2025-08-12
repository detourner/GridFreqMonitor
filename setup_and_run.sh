#!/bin/bash

# Variables
VENV_DIR="/home/pi/grid_freq_monitor/grid_freq_monitor_env"
SCRIPT_PATH="/home/pi/grid_freq_monitor/grid_freq_monitor.py"

# 1. Create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
fi

# 2. Activate the virtual environment
source "$VENV_DIR/bin/activate"
if [ $? -ne 0 ]; then
    echo "Error: Failed to activate virtual environment."
    exit 1
fi

# 3. Install dependencies
pip install --upgrade pip
pip install pigpio websockets
if [ $? -ne 0 ]; then
    echo "Error: Failed to install dependencies."
    exit 1
fi

# 4. Start pigpiod if it is not already running
if ! pgrep -x "pigpiod" > /dev/null; then
    sudo pigpiod
    if [ $? -ne 0 ]; then
        echo "Error: Failed to start pigpiod."
        exit 1
    fi
    sleep 1  # wait for pigpiod to start
fi

# 5. Run the Python script
python3 "$SCRIPT_PATH"
if [ $? -ne 0 ]; then
    echo "Error: Failed to run the Python script."
    exit 1
fi