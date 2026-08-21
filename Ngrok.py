"""
ngrok_start.py — gives your Flask app a public HTTPS URL
so the phone camera works from your phone browser.

Setup (one time):
  pip install pyngrok

Run:
  python ngrok_start.py
  → copies the https://xxxx.ngrok.io URL
  → open that URL on your phone
"""

import subprocess
import sys
import time

def main():
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        print("Installing pyngrok...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyngrok"])
        from pyngrok import ngrok

    print("=" * 55)
    print("  Starting Flask + ngrok HTTPS tunnel")
    print("=" * 55)

    # Start Flask in background
    flask_proc = subprocess.Popen(
        [sys.executable, "app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    time.sleep(3)  # wait for Flask to boot

    # Open ngrok tunnel
    tunnel = ngrok.connect(5000, "http")
    url    = tunnel.public_url

    print(f"\n  Flask running  : http://localhost:5000")
    print(f"  Phone HTTPS URL: {url}")
    print(f"\n  Open  {url}  on your phone")
    print(f"  Camera tab will work on the phone now")
    print(f"\n  Press Ctrl+C to stop\n")

    try:
        flask_proc.wait()
    except KeyboardInterrupt:
        flask_proc.terminate()
        ngrok.kill()
        print("\nStopped.")

if __name__ == "__main__":
    main()