import sys
import socket
import uvicorn
import webbrowser
import threading
import time

def find_available_port(start_port=8000, max_port=8050):
    for port in range(start_port, max_port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    return start_port

def open_browser(url):
    time.sleep(1.2)
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    port = find_available_port(8000)
    url = f"http://127.0.0.1:{port}/login"

    print("=" * 60)
    print("[DOCUSIGN PRO] Electronic Document Signature App")
    print("=" * 60)
    print(f"Local Web Server running at: http://127.0.0.1:{port}")
    print(f"Login Portal (Opening First): {url}")
    print("Features: Self-Signing, Multi-Signer Requests, Audit Trail")
    print("=" * 60)

    # Launch browser automatically in background
    threading.Thread(target=open_browser, args=(url,), daemon=True).start()

    uvicorn.run("app.main:app", host="127.0.0.1", port=port, log_level="info")
