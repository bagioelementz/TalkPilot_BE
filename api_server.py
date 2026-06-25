import json
import os
import re
import glob
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

from bland_call_agent import dispatch_call, get_call_details, save_call_data, stop_call


HOST = os.getenv("API_HOST", "0.0.0.0")
PORT = int(os.getenv("API_PORT", "8787"))
STORAGE_DIR = os.getenv("CALL_STORAGE_DIR", "storage")

DEFAULT_FIRST_SENTENCE = (
    "Hallo! Hier spricht Avira von TaskMeister. Ich hoffe, Sie haben einen "
    "schonen Tag. Ich rufe bezuglich einer Klempner-Serviceanfrage in Berlin "
    "an. Hatten Sie kurz einen Moment Zeit?"
)

DEFAULT_TASK = """You are calling about a plumbing service request. Always start in German.
If the callee responds in German, continue in German. If they respond in English,
switch to English.

German flow:
Unser Kunde Sam benotigt Hilfe bei einem undichten Rohr in seiner Kuche. Der
Service wird bis nachsten Montag um 10:00 Uhr benotigt, und das geschatzte
Budget betragt ca. 600 EUR.

English flow:
Our client, Sam, needs help with a leaking pipe in their kitchen. The service
is needed by next Monday at 10:00 AM, and the estimated budget is around
600 EUR.

Ask whether they are available and interested in taking the job. If they are
interested, ask for their availability and any requirements before their details
are shared with the client. If they are unavailable, politely thank them and end
the call."""

PHONE_RE = re.compile(r"^\+[1-9]\d{5,14}$")


class ApiHandler(BaseHTTPRequestHandler):
    server_version = "TaskMeisterCallAPI/1.0"

    def log_message(self, format, *args):
        print("%s - %s" % (self.address_string(), format % args))

    def _send_json(self, status_code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self):
        content_length = int(self.headers.get("Content-Length", "0") or "0")
        if content_length == 0:
            return {}

        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError:
            raise ValueError("Request body must be valid JSON.")

    def do_OPTIONS(self):
        self._send_json(200, {"status": "ok"})

    def do_GET(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        if path == "/":
            self._send_json(
                200,
                {
                    "status": "ok",
                    "service": "TaskMeister Call API",
                    "endpoints": {
                        "health": "GET /health",
                        "start_call": "POST /calls",
                        "call_details": "GET /calls/<call_id>",
                        "summaries": "GET /summaries",
                        "archive_call": "POST /calls/<call_id>/archive",
                        "cancel_call": "POST /calls/<call_id>/cancel",
                    },
                },
            )
            return

        if path == "/health":
            self._send_json(200, {"status": "ok"})
            return

        if path == "/summaries":
            self._list_summaries()
            return

        call_id = self._call_id_from_path(path)
        if call_id:
            details = get_call_details(call_id)
            status_code = 502 if details.get("status") == "error" else 200
            self._send_json(status_code, details)
            return

        self._send_json(404, {"status": "error", "message": "Endpoint not found."})

    def do_POST(self):
        path = urlparse(self.path).path.rstrip("/") or "/"

        try:
            payload = self._read_json()
        except ValueError as exc:
            self._send_json(400, {"status": "error", "message": str(exc)})
            return

        if path == "/calls":
            self._start_call(payload)
            return

        call_id = self._archive_call_id_from_path(path)
        if call_id:
            self._archive_call(call_id)
            return

        call_id = self._cancel_call_id_from_path(path)
        if call_id:
            self._cancel_call(call_id)
            return

        self._send_json(404, {"status": "error", "message": "Endpoint not found."})

    def _start_call(self, payload):
        phone_number = str(payload.get("phone_number", "")).strip().replace(" ", "")
        if not PHONE_RE.match(phone_number):
            self._send_json(
                400,
                {
                    "status": "error",
                    "message": "phone_number must be in E.164 format, e.g. +4915123456789.",
                },
            )
            return

        task = str(payload.get("task") or DEFAULT_TASK)
        voice = str(payload.get("voice") or "karl")
        first_sentence = str(payload.get("first_sentence") or DEFAULT_FIRST_SENTENCE)

        result = dispatch_call(
            phone_number=phone_number,
            task=task,
            voice=voice,
            first_sentence=first_sentence,
        )

        if result.get("status") == "error":
            self._send_json(502, result)
            return

        result.setdefault("status", "success")
        self._send_json(200, result)

    def _archive_call(self, call_id):
        details = get_call_details(call_id)
        if details.get("status") == "error":
            self._send_json(502, details)
            return

        json_path, transcript_path = save_call_data(
            call_id,
            details,
            storage_dir=STORAGE_DIR,
        )
        self._send_json(
            200,
            {
                "status": "success",
                "call_id": call_id,
                "json_path": json_path,
                "transcript_path": transcript_path,
            },
        )

    def _cancel_call(self, call_id):
        result = stop_call(call_id)
        if result.get("status") == "error":
            self._send_json(502, result)
            return

        result.setdefault("status", "success")
        result.setdefault("call_id", call_id)
        self._send_json(200, result)

    def _list_summaries(self):
        os.makedirs(STORAGE_DIR, exist_ok=True)
        summaries = []
        for json_path in glob.glob(os.path.join(STORAGE_DIR, "call_*.json")):
            if json_path.endswith("_transcript.json"):
                continue
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except (OSError, json.JSONDecodeError):
                continue

            call_id = (
                data.get("call_id")
                or data.get("c_id")
                or os.path.basename(json_path)[5:-5]
            )
            summaries.append(
                {
                    "call_id": call_id,
                    "phone_number": data.get("to") or data.get("phone_number") or "Unknown",
                    "created_at": data.get("created_at") or "",
                    "call_length": data.get("call_length") or 0,
                    "summary": data.get("summary") or "No summary available yet.",
                }
            )

        summaries.sort(
            key=lambda item: item.get("created_at") or "",
            reverse=True,
        )
        self._send_json(200, {"status": "success", "summaries": summaries})

    @staticmethod
    def _call_id_from_path(path):
        parts = [part for part in path.split("/") if part]
        if len(parts) == 2 and parts[0] == "calls":
            return parts[1]
        return None

    @staticmethod
    def _archive_call_id_from_path(path):
        parts = [part for part in path.split("/") if part]
        if len(parts) == 3 and parts[0] == "calls" and parts[2] == "archive":
            return parts[1]
        return None

    @staticmethod
    def _cancel_call_id_from_path(path):
        parts = [part for part in path.split("/") if part]
        if len(parts) == 3 and parts[0] == "calls" and parts[2] == "cancel":
            return parts[1]
        return None


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = ThreadingHTTPServer((HOST, PORT), ApiHandler)
    print(f"TaskMeister Call API listening on http://{HOST}:{PORT}")
    print("React Native should call POST /calls with {\"phone_number\":\"+...\"}.")
    server.serve_forever()


if __name__ == "__main__":
    main()
