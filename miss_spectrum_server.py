#!/usr/bin/env python3
"""Receive MISS plot selections from interactive_GHOST_tool.html.

Workflow
--------
1. Terminal:  python miss_spectrum_server.py
2. Open interactive_GHOST_tool.html
3. Show a MISS plot, then for signal and background each:
   - click = single scan-angle spectrum
   - drag a box = mean spectrum over that scan-angle range
4. After both selections, a matplotlib window opens.
5. Next selection starts a new signal/background pair.

The browser POSTs JSON to http://127.0.0.1:8765/click.
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
SPECTRUM_SCRIPT = ROOT / "plot_miss_click_spectrum.py"
HOST = "127.0.0.1"
PORT = 8765

# Pending signal selection dict (includes kind point|range).
_pending_signal: dict | None = None


def _normalize_selection(data: dict) -> dict:
    """Build a point or range selection from the browser payload."""
    filename = str(data["filename"])
    natural_width = int(data.get("naturalWidth") or data.get("natural_width") or 0)
    natural_height = int(data.get("naturalHeight") or data.get("natural_height") or 0)
    kind = str(data.get("kind") or "point")

    if kind == "range":
        y0 = int(data["y0"])
        y1 = int(data["y1"])
        x0 = int(data.get("x0", data.get("x", 0)))
        x1 = int(data.get("x1", data.get("x", 0)))
        selection = {
            "filename": filename,
            "kind": "range",
            "x0": x0,
            "y0": y0,
            "x1": x1,
            "y1": y1,
            "naturalWidth": natural_width,
            "naturalHeight": natural_height,
        }
    else:
        selection = {
            "filename": filename,
            "kind": "point",
            "x": int(data["x"]),
            "y": int(data["y"]),
            "naturalWidth": natural_width,
            "naturalHeight": natural_height,
        }
    return selection


def _selection_json_for_script(selection: dict) -> str:
    if selection["kind"] == "range":
        payload = {
            "kind": "range",
            "x0": selection["x0"],
            "y0": selection["y0"],
            "x1": selection["x1"],
            "y1": selection["y1"],
        }
    else:
        payload = {"kind": "point", "x": selection["x"], "y": selection["y"]}
    return json.dumps(payload, separators=(",", ":"))


class ClickHandler(BaseHTTPRequestHandler):
    def _cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors_headers()
        self.end_headers()

    def do_POST(self):
        global _pending_signal

        if urlparse(self.path).path != "/click":
            self.send_error(404, "Not found")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            data = json.loads(raw.decode("utf-8"))
            selection = _normalize_selection(data)
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            self._send_json(400, {"ok": False, "error": f"Bad payload: {exc}"})
            return

        filename = selection["filename"]

        if _pending_signal is not None and _pending_signal.get("filename") != filename:
            print(
                f"[server] Filename changed ({_pending_signal['filename']} → {filename}); "
                "starting a new signal selection.",
                flush=True,
            )
            _pending_signal = None

        if _pending_signal is None:
            _pending_signal = selection
            print(
                f"[server] Signal {selection['kind']}: {filename} {selection}. "
                "Select background next.",
                flush=True,
            )
            self._send_json(
                200,
                {
                    "ok": True,
                    "status": "need_background",
                    "signal": selection,
                },
            )
            return

        signal = _pending_signal
        background = selection
        _pending_signal = None

        cmd = [
            sys.executable,
            str(SPECTRUM_SCRIPT),
            "--filename",
            filename,
            "--signal-json",
            _selection_json_for_script(signal),
            "--bg-json",
            _selection_json_for_script(background),
            "--natural-width",
            str(background.get("naturalWidth") or signal.get("naturalWidth") or 0),
            "--natural-height",
            str(background.get("naturalHeight") or signal.get("naturalHeight") or 0),
        ]
        print(f"\n[server] Background received. Running:\n  {' '.join(cmd)}\n", flush=True)

        def _run():
            completed = subprocess.run(cmd, cwd=ROOT)
            if completed.returncode != 0:
                print(
                    f"[server] Spectrum script exited with code {completed.returncode}",
                    flush=True,
                )

        threading.Thread(target=_run, daemon=True).start()

        self._send_json(
            200,
            {
                "ok": True,
                "status": "plotted",
                "signal": signal,
                "background": background,
            },
        )

    def log_message(self, fmt, *args):
        if self.path.startswith("/click"):
            super().log_message(fmt, *args)

    def _send_json(self, status: int, payload: dict):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self._cors_headers()
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    if not SPECTRUM_SCRIPT.is_file():
        print(f"Missing {SPECTRUM_SCRIPT}", file=sys.stderr)
        sys.exit(1)

    server = ThreadingHTTPServer((HOST, PORT), ClickHandler)
    print(f"Listening for MISS plot selections at http://{HOST}:{PORT}/click")
    print("For signal then background: click = single row, drag = mean over range.")
    print("Ctrl+C to stop.\n")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.server_close()


if __name__ == "__main__":
    main()
