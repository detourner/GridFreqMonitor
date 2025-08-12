import pigpio
import time
from collections import deque
import json
import asyncio
import websockets

# === CONFIGURATION ===
GPIO_1HZ = 17
GPIO_100HZ = 27
WEBSERVER_PORT = 8765

# Connect to pigpio (make sure to run 'sudo pigpiod' beforehand)
pi = pigpio.pi()
if not pi.connected:
    exit("Unable to connect to pigpio. Please run 'sudo pigpiod'.")

# History for moving average
history = deque(maxlen=10)
count_100Hz = 0
last_tick_100Hz = None 
current_frequency = None  # last calculated average frequency
last_update_time = None  # Timestamp of the last frequency update


# === Callbacks ===
def cb_100Hz(gpio, level, tick):
    global count_100Hz, last_tick_100Hz
    if last_tick_100Hz is None or (tick - last_tick_100Hz) >= 8000:  # check if at least 8ms has passed
        count_100Hz += 1
        last_tick_100Hz = tick

def cb_1Hz(gpio, level, tick):
    global count_100Hz, history, current_frequency
    history.append(count_100Hz)
    count_100Hz = 0

    if len(history) == 10:
        current_frequency = sum(history) / 20.0 # compute 100Hz average and divide by 2 to get 50Hz equivalent
        last_update_time = time.time()  # Save the timestamp of the update
        print(f"Average frequency (10s): {current_frequency:.2f} Hz")

# === GPIO Configuration ===
pi.set_mode(GPIO_100HZ, pigpio.INPUT)
pi.set_pull_up_down(GPIO_100HZ, pigpio.PUD_UP)
pi.set_mode(GPIO_1HZ, pigpio.INPUT)
pi.set_pull_up_down(GPIO_1HZ, pigpio.PUD_UP)

pi.callback(GPIO_100HZ, pigpio.FALLING_EDGE, cb_100Hz)
pi.callback(GPIO_1HZ, pigpio.FALLING_EDGE, cb_1Hz)

# === WebSocket Server ===
async def handler(websocket, path):
    client_ip = websocket.remote_address[0] if websocket.remote_address else "Unknown"
    print(f"Client connected from IP: {client_ip}")
    async def send_frequency():
        try:
            while True:
                data = {
                    "timestamp": time.time(),
                    "last_update_time": last_update_time,  # Include the last update time when current_frequency was calculated
                    "frequency": round(current_frequency, 2) if current_frequency is not None else None
                }
                await websocket.send(json.dumps(data))
                await asyncio.sleep(1)  # async sleep for 1 second
        except websockets.ConnectionClosed:
            print(f"Client disconnected from IP: {client_ip}")
        except Exception as e:
            print(f"An unexpected error occurred with client {client_ip}: {e}")
    # Run the data-sending task
    await send_frequency()

# === Main Function ===
async def main():
    try:
        server = await websockets.serve(handler, "0.0.0.0", WEBSERVER_PORT)
        print(f"WebSocket server started at ws://0.0.0.0:{WEBSERVER_PORT}")
        await asyncio.Future()  # run forever
    except KeyboardInterrupt:
        print("WebSocket server interrupted by user.")
    finally:
        server.close()  # Close and wait the WebSocket server
        await server.wait_closed()  
        print("WebSocket server stopped.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        pi.stop()  # cleanly stop pigpio connection
        print("Pigpio connection stopped.")