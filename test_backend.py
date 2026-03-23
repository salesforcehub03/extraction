import requests
import json
import time

BASE_URL = "http://localhost:8123"

def test_extraction():
    # 1. Health check
    try:
        res = requests.get(f"{BASE_URL}/api/health")
        print(f"Health check: {res.status_code} {res.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return

    # 2. Upload file
    pdffile = r"d:\AViiD\Data Extraction\belino-ib.pdf"
    print(f"Uploading {pdffile}...")
    try:
        with open(pdffile, "rb") as f:
            files = {"ib_pdf": ("belino-ib.pdf", f, "application/pdf")}
            res = requests.post(f"{BASE_URL}/api/extract", files=files)
    except Exception as e:
        print(f"Upload request failed: {e}")
        return
    
    if res.status_code != 200:
        print(f"Upload failed: {res.status_code} {res.text}")
        return
    
    data = res.json()
    session_id = data["session_id"]
    print(f"Session ID: {session_id}")

    # 3. Listen to SSE stream
    print("Listening to SSE stream...")
    stream_url = f"{BASE_URL}/api/extract/stream/{session_id}"
    res = requests.get(stream_url, stream=True)
    
    for line in res.iter_lines():
        if line:
            decoded_line = line.decode('utf-8')
            print(decoded_line)
            if "event: pipeline_error" in decoded_line or "event: complete" in decoded_line:
                # Read the next lines for data
                print(decoded_line)

if __name__ == "__main__":
    test_extraction()
