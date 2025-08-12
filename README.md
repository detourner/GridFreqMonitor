# GridFreqMonitor
This project configures a Raspberry Pi to measure the electrical grid frequency (50 Hz) in real-time and streams the data via a WebSocket server. Written in Python, it enables live monitoring of power grid stability and frequency variations for analysis or integration with other systems.

# Operating Principle
The circuit used to measure the grid frequency is based on a [mains module](https://fr.aliexpress.com/item/32828199766.htm), with a small modification. The modification involves removing the smoothing capacitor, which results in a 100 Hz signal being sent to the optocoupler (a pulse at each zero crossing).

This frequency is then compared to a 1 Hz reference signal obtained from the PPS signal of a GPS [GT-U7](https://fr.aliexpress.com/item/32832919409.html) module (based on an atomic clock). To achieve this, the number of pulses from the 100 Hz signal is counted during 10 pulses of the 1 Hz signal (i.e., over 10 seconds). 

The grid frequency value is calculated by dividing the 100 Hz signal by 2 and averaging it over 10 seconds. The frequency is updated every second using a sliding average.

## Features
- Measures 100Hz input pulses and averages over 10 seconds.
- Sends grid frequency data every second over WebSocket.
- Runs as a systemd service on Raspberry Pi.
- Uses a Python virtual environment for dependencies.

## Setup Instructions

1. Copy all files to your Raspberry Pi user's home directory (e.g., `/home/pi/grid_freq_monitor/`).

2. Make the setup script executable:
   ```bash
   chmod +x setup_and_run.sh

3. Enable and start the systemd service:

   ```bash
    sudo cp grid_freq_monitor.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable grid_freq_monitor.service
    sudo systemctl start grid_freq_monitor.service

4. Check service status and logs:

   ```bash
    sudo systemctl status grid_freq_monitor.service
    journalctl -u grid_freq_monitor.service -f

## Usage
- The service will start automatically at boot.
- Connect a WebSocket client to ws://<raspberry-pi-ip>:8765 to receive JSON messages:

   ```json
    {
    "timestamp": 1690000000.123456,
    "last_update_time": 1690000000.123999,
    "frequency": 99.7
    }

## Notes
- Update user 'pi' if necessary (update grid_freq_monitor.service file) 
- Make sure pigpiod daemon is running (the service starts it if needed).
- GPIO pins 17 and 27 must be connected to your frequency sources.
- Modify GPIO pin numbers and other parameters in grid_freq_monitor.py if necessary.

## Reference
- https://www.swissgrid.ch/en/home/operation/grid-data/current-data.html#frequency
- https://oinkzwurgl.org/projaeggd/mains-frequency/
- https://revspace.nl/MainsFrequency
- https://mainsfrequency.com/impressum.htm


## License
MIT License.
