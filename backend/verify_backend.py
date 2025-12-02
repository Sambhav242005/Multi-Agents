import requests
import sys
import time

BASE_URL = "http://localhost:8000"

def test_health():
    try:
        response = requests.get(f"{BASE_URL}/")
        if response.status_code == 200:
            print("✅ Health check passed")
            return True
        else:
            print(f"❌ Health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Health check failed: {e}")
        return False

def test_classify():
    try:
        payload = {"idea": "A fitness app for lazy developers"}
        response = requests.post(f"{BASE_URL}/classify", json=payload)
        if response.status_code == 200:
            data = response.json()
            if "classification" in data:
                print("✅ Classify endpoint passed")
                print(f"   Response: {data['classification']}")
                return True
            else:
                print(f"❌ Classify endpoint returned unexpected format: {data}")
                return False
        else:
            print(f"❌ Classify endpoint failed: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Classify endpoint failed: {e}")
        return False

if __name__ == "__main__":
    print("Waiting for API to start...")
    # Simple retry logic to wait for API
    for _ in range(5):
        if test_health():
            break
        time.sleep(2)
    else:
        print("Could not connect to API after retries.")
        sys.exit(1)

    if test_classify():
        print("\nAll tests passed!")
    else:
        print("\nSome tests failed.")
        sys.exit(1)
