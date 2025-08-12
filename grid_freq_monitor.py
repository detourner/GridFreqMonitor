import pigpio
import time
from collections import deque
import json
import asyncio
import websockets

# === CONFIGURATION ===
GPIO_1HZ = 17               # GPIO pin for 1 Hz reference signal
GPIO_GRIS_SIGNAL = 27       # GPIO pin signal to measure (e.g., from a grid frequency sensor)
WEBSERVER_PORT = 8765
NUMBER_OF_SAMPLES = 1000     # Number of samples to keep in the buffer for frequency calculation
DEBOUNCE_TIME_MS = 8000      # Debounce time in microsecond for the input signal

# Connect to pigpio (make sure to run 'sudo pigpiod' before starting this script)
pi = pigpio.pi()
if not pi.connected:
    exit("Unable to connect to pigpio. Please run 'sudo pigpiod'.")

# === Measurement state ===
ticks_grid_signal = deque(maxlen=NUMBER_OF_SAMPLES) # stores tick times for all last samples of the input grid signal
last_tick_grid_signal = None                        # last tick recorded for the 100 Hz signal
last_tick_1Hz = None                                # last tick recorded for the 1 Hz signal
current_frequency = None                            # most recent calculated average frequency (Hz)
last_update_time = None                             # timestamp (seconds) when current_frequency was last updated


# === Callbacks ===
def cb_grid_signal(gpio, level, tick):
    """
    Callback for the input grid signal.
    - Adds a timestamp to the sample circular buffer.
    - Ignores spurious edges if less than ~8ms apart.
    """
    global last_tick_grid_signal
    if last_tick_grid_signal is None or pigpio.tickDiff(last_tick_grid_signal, tick) >= DEBOUNCE_TIME_MS:  # debounce
        ticks_grid_signal.append(tick)
        last_tick_grid_signal = tick


def cb_1Hz(gpio, level, tick):
    """
    Callback for the 1 Hz reference signal.
    - Updates base_time_seconds based on the time between two 1 Hz edges.
    - Calculates the average frequency of the input grid signal over the last n cycles (samples).
    - Applies correction based on base_time_seconds.
    """
    global last_tick_1Hz, current_frequency, last_update_time

    # Calculate base time (seconds) from the 1 Hz reference
    if last_tick_1Hz is None:
        last_tick_1Hz = tick
        return  # first measurement, no base time yet
    dt_us = pigpio.tickDiff(last_tick_1Hz, tick)
    base_time_seconds = dt_us / 1_000_000.0
    last_tick_1Hz = tick

    # Only compute if there a data in buffer is full
    if len(ticks_grid_signal) >= 2:
        tick_old = ticks_grid_signal[0]
        tick_new = ticks_grid_signal[-1]
        dt_us = pigpio.tickDiff(tick_old, tick_new)

        # Measured frequency over n cycles (there is one sample per cycle) and convert to Hz
        measured_freq = (len(ticks_grid_signal) - 1) / (dt_us / 1_000_000.0)

        # Correct for base time drift and divide by 2 (two zero-crossings per period)
        current_frequency = (measured_freq / base_time_seconds) / 2.0
        last_update_time = time.time()

        print(f"Frequency: {current_frequency:.3f} Hz (at {last_update_time:.3f} seconds) [{len(ticks_grid_signal)} samples ; Measured: {measured_freq:.3f} Hz ; Base time: {base_time_seconds:.3f}]")

# === GPIO Configuration ===
pi.set_mode(GPIO_GRIS_SIGNAL, pigpio.INPUT)
pi.set_pull_up_down(GPIO_GRIS_SIGNAL, pigpio.PUD_UP)
pi.set_mode(GPIO_1HZ, pigpio.INPUT)
pi.set_pull_up_down(GPIO_1HZ, pigpio.PUD_UP)

pi.callback(GPIO_GRIS_SIGNAL, pigpio.FALLING_EDGE, cb_grid_signal)
pi.callback(GPIO_1HZ, pigpio.FALLING_EDGE, cb_1Hz)

# === WebSocket Server ===
async def handler(websocket, path):
    """
    WebSocket handler for connected clients.
    - Sends the current frequency once per second in JSON format.
    - Includes both the latest frequency and the timestamp of its calculation.
    """
    client_ip = websocket.remote_address[0] if websocket.remote_address else "Unknown"
    print(f"Client connected from IP: {client_ip}")

    try:
        while True:
            data = {
                "time_stamp": time.time(),
                "last_update_time": last_update_time,
                "frequency": round(current_frequency, 3) if current_frequency is not None else None
            }
            await websocket.send(json.dumps(data))
            await asyncio.sleep(1)
    except websockets.ConnectionClosed:
        print(f"Client disconnected from IP: {client_ip}")
    except Exception as e:
        print(f"Unexpected error with client {client_ip}: {e}")


# === Main Function ===
async def main():
    try:
        server = await websockets.serve(handler, "0.0.0.0", WEBSERVER_PORT)
        print(f"WebSocket server started at ws://0.0.0.0:{WEBSERVER_PORT}")
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        print("WebSocket server interrupted by user.")
    finally:
        server.close()
        await server.wait_closed()
        print("WebSocket server stopped.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        pi.stop()
        print("Pigpio connection stopped.")
