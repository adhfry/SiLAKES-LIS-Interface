"""
Diagnostik minimal: isolasi apakah js_api exposure pywebview berfungsi sama
sekali di kombinasi pywebview 6.2.1 + Python 3.14 ini, di luar kompleksitas
app utama. HTML inline, tidak butuh Vite/dist sama sekali.
"""
import json
import os
import threading
import time

import webview

MARKER = os.path.join(os.path.dirname(__file__), "diag_marker.txt")
if os.path.exists(MARKER):
    os.remove(MARKER)

HTML = """
<html><body style="background:#111;color:#0f0;font-family:monospace;padding:20px">
<h1 id="status">starting...</h1>
<script>
function log(msg) {
  document.getElementById('status').innerText = msg;
}
function tryPing(attempt) {
  log('attempt ' + attempt + ': checking window.pywebview...');
  if (!window.pywebview) {
    log('attempt ' + attempt + ': window.pywebview NOT PRESENT');
    if (attempt < 50) setTimeout(() => tryPing(attempt+1), 200);
    return;
  }
  if (!window.pywebview.api) {
    log('attempt ' + attempt + ': window.pywebview.api NOT PRESENT');
    if (attempt < 50) setTimeout(() => tryPing(attempt+1), 200);
    return;
  }
  var keys = Object.keys(window.pywebview.api);
  log('attempt ' + attempt + ': api keys = [' + keys.join(',') + ']');
  if (typeof window.pywebview.api.ping !== 'function') {
    if (attempt < 50) setTimeout(() => tryPing(attempt+1), 200);
    return;
  }
  window.pywebview.api.ping('hello-from-js').then(function(res) {
    log('SUCCESS: ' + JSON.stringify(res));
  }).catch(function(err) {
    log('CALL FAILED: ' + err);
  });
}
window.addEventListener('pywebviewready', function() {
  log('pywebviewready event fired!');
  tryPing(1);
});
setTimeout(() => tryPing(1), 500); // juga coba tanpa nunggu event, sbg pembanding
</script>
</body></html>
"""


class Api:
    def ping(self, msg):
        with open(MARKER, "w", encoding="utf-8") as f:
            f.write(f"PING OK: {msg}\n")
        return {"pong": msg, "ok": True}


def poll_marker():
    for _ in range(30):
        time.sleep(1)
        if os.path.exists(MARKER):
            print(f"[diag] MARKER FILE FOUND: {open(MARKER).read()}")
            return
    print("[diag] MARKER FILE NEVER APPEARED after 30s -- js_api call never succeeded")


if __name__ == "__main__":
    api = Api()
    window = webview.create_window("Diag", html=HTML, js_api=api, width=500, height=200)
    threading.Thread(target=poll_marker, daemon=True).start()
    webview.start(debug=False)
