import requests
import random
import time

# Server URL
# SERVER_URL = "https://ece198-performance-monitoring-game.onrender.com/device/"
SERVER_URL = "http://localhost:8000/device/"

# Yiran's device ID
DEVICE_ID = "78:1C:3C:2B:96:A4"

def generate_gameplay():
    """Generate random gameplay data"""
    # Random level between 5 and 20
    level = random.randint(5, 20)

    # Generate response times for each level
    # Simulate realistic response times with some variance
    response_times = []
    for i in range(level):
        # Base time increases slightly with level (cognitive fatigue)
        base_time = 0.3 + (i * 0.02)
        # Add random variance
        variance = random.uniform(-0.15, 0.3)
        # Occasionally add a slower response (simulating hesitation)
        if random.random() < 0.15:
            variance += random.uniform(0.5, 1.5)

        response_time = max(0.1, base_time + variance)
        response_times.append(round(response_time, 3))

    return level, response_times

def send_data(level_reached, response_times):
    """Send data to server"""
    data = {
        "device_id": DEVICE_ID,
        "timestamp": int(time.time() * 1000),
        "level_reached": level_reached,
        "response_times": response_times,
    }

    try:
        response = requests.post(SERVER_URL, json=data, timeout=10)
        if response.status_code == 200:
            print(f"  Level {level_reached:2d} | Avg: {sum(response_times)/len(response_times):.3f}s")
            return True
        else:
            print(f"  Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"  Error: {e}")
        return False

def main():
    print("Generating test data for Yiran (ID: 1)")
    print("=" * 50)

    num_sessions = 20
    successful = 0

    for i in range(num_sessions):
        level, response_times = generate_gameplay()
        print(f"Session {i+1:2d}:", end="")
        if send_data(level, response_times):
            successful += 1
        # Small delay between requests
        time.sleep(0.1)

    print("=" * 50)
    print(f"Generated {successful}/{num_sessions} gameplay sessions")
    print(f"View at: http://localhost:8000/user/1")

if __name__ == "__main__":
    main()
