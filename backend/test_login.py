import requests

URL = "http://127.0.0.1:8000/api/v1/admin/login"

def test_login():
    payload = {
        "username": "admin",
        "password": "admin",
        "grant_type": "password"
    }
    
    print(f"Testing login at {URL}...")
    try:
        response = requests.post(URL, data=payload)
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            print("Login Successful!")
            print(response.json())
        else:
            print("Login Failed!")
            print(response.text)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_login()
