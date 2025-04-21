import time
import requests

# ——— CONFIG ———
ACCESS_TOKEN = "act.LWcEO4dJCIadYv2cAL2iP8nhF7op8BIjgQCPegiKDzDhRFBGdCag8pc1ulWT!4465.e1"
PUBLISH_ID   = "v_inbox_file~v2.7495799457653655584"
CHECK_INTERVAL = 5  # seconds between polls

# ——— FUNCTION TO POLL STATUS ———
def check_upload_status(access_token: str, publish_id: str) -> dict:
    """
    Calls the TikTok Fetch Status endpoint and returns the `data` object.
    """
    url = "https://open.tiktokapis.com/v2/post/publish/status/fetch/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type":  "application/json; charset=UTF-8"
    }
    payload = { "publish_id": publish_id }
    resp = requests.post(url, headers=headers, json=payload)
    resp.raise_for_status()
    return resp.json()["data"]  # contains status, uploaded_bytes, etc.

# ——— MAIN LOOP ———
if __name__ == "__main__":
    print(f"Polling upload status for publish_id={PUBLISH_ID}…")
    while True:
        info = check_upload_status(ACCESS_TOKEN, PUBLISH_ID)
        status = info.get("status")
        uploaded = info.get("uploaded_bytes")
        downloaded = info.get("downloaded_bytes")
        fail_reason = info.get("fail_reason") or "–"

        print(f"[{time.strftime('%H:%M:%S')}] status={status}, "
              f"uploaded_bytes={uploaded}, downloaded_bytes={downloaded}, "
              f"fail_reason={fail_reason}")

        # Terminal states as per API spec: PUBLISH_COMPLETE or FAILED :contentReference[oaicite:1]{index=1}
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            print("▶️ Finished polling.")
            break

        time.sleep(CHECK_INTERVAL)