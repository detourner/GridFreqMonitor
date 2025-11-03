import pigpio
import time
from collections import deque
import json
import paho.mqtt.client as mqtt

# === CONFIGURATION ===
GPIO_1HZ = 21               # GPIO pin for 1 Hz reference signal
GPIO_INPUT_SIGNAL = 24      # GPIO pin signal to measure (e.g., from a grid frequency sensor)
MQTT_BROKER = "localhost"   # MQTT broker address (local Mosquitto broker)
MQTT_PORT = 1883            # MQTT broker port
MQTT_TOPIC = "grid/frequency"  # MQTT topic to publish frequency data
NUMBER_OF_SAMPLES = 1000    # Number of samples to keep in the buffer for frequency calculation
DEBOUNCE_TIME_MS = 8000     # Debounce time in microseconds for the input signal

# Connect to pigpio (make sure to run 'sudo pigpiod' before starting this script)
pi = pigpio.pi()
if not pi.connected:
    exit("Unable to connect to pigpio. Please run 'sudo pigpiod'.")

# === Measurement state ===
ticks_grid_signal = deque(maxlen=NUMBER_OF_SAMPLES)  # Stores tick times for all last samples of the input grid signal
last_tick_grid_signal = None                        # Last tick recorded for the 100 Hz signal
last_tick_1Hz = None                                # Last tick recorded for the 1 Hz signal
current_frequency = None                            # Most recent calculated average frequency (Hz)
last_update_time = None                             # Timestamp (seconds) when current_frequency was last updated

# === MQTT Client Setup ===
mqtt_client = mqtt.Client()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected to MQTT broker.")
    else:
        print(f"Failed to connect to MQTT broker. Return code: {rc}")

mqtt_client.on_connect = on_connect
mqtt_client.connect(MQTT_BROKER, MQTT_PORT, 60)
mqtt_client.loop_start()

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

    print(f"Base time: {base_time_seconds:.6f} seconds (from 1 Hz signal)")

    # Only compute if there is data in the buffer
    if len(ticks_grid_signal) >= 2:
        tick_old = ticks_grid_signal[0]
        tick_new = ticks_grid_signal[-1]
        dt_us = pigpio.tickDiff(tick_old, tick_new)

        # Measured frequency over n cycles (there is one sample per cycle) and convert to Hz
        measured_freq = (len(ticks_grid_signal) - 1) / (dt_us / 1_000_000.0)

        # Correct for base time drift and divide by 2 (two zero-crossings per period)
        current_frequency = (measured_freq / base_time_seconds) / 2.0
        last_update_time = time.time()

        print(f"Frequency: {current_frequency:.6f} Hz (at {last_update_time:.6f} seconds) [{len(ticks_grid_signal)} samples ; Measured: {measured_freq:.6f} Hz]")

        # Publish the frequency data to the MQTT broker
        data = {
            "time_stamp": time.time(),
            "last_update_time": last_update_time,
            "frequency": round(current_frequency, 3)
        }
        mqtt_client.publish(MQTT_TOPIC, json.dumps(data))


# === GPIO Configuration ===
pi.set_mode(GPIO_INPUT_SIGNAL, pigpio.INPUT)
pi.set_pull_up_down(GPIO_INPUT_SIGNAL, pigpio.PUD_UP)
pi.set_mode(GPIO_1HZ, pigpio.INPUT)
pi.set_pull_up_down(GPIO_1HZ, pigpio.PUD_UP)

pi.callback(GPIO_INPUT_SIGNAL, pigpio.FALLING_EDGE, cb_grid_signal)
pi.callback(GPIO_1HZ, pigpio.FALLING_EDGE, cb_1Hz)

# === Main Function ===
if __name__ == "__main__":
    try:
        print(f"Publishing frequency data to MQTT broker at {MQTT_BROKER}:{MQTT_PORT}, topic: {MQTT_TOPIC}")
        while True:
            time.sleep(1)  # Keep the script running
    except KeyboardInterrupt:
        print("Script interrupted by user.")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        pi.stop()
        print("Pigpio connection stopped.")
