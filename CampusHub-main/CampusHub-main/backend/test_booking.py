import requests

def test():
    # Login
    resp = requests.post("http://127.0.0.1:8000/api/auth/login", json={"email": "alex@campus.edu", "password": "Demo@1234"})
    token = resp.json()["data"]["access_token"]
    
    # Try booking
    headers = {"Authorization": f"Bearer {token}"}
    payload = {
        "seat_id": "F1-A6",
        "date": "2026-04-05", # Same date as F1-A5!!
        "start_time": "09:00",
        "end_time": "12:00",
        "floor": 1,
        "zone": "General"
    }
    booking_resp = requests.post("http://127.0.0.1:8000/api/library/book-seat", json=payload, headers=headers)
    print("BOOKING:", booking_resp.status_code, booking_resp.text)

test()
