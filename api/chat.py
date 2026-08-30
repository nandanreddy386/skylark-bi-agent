from http.server import BaseHTTPRequestHandler
import json
import sys
import os
import asyncio

# Ensure sys.path contains workspace root and backend directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

from backend.agent.agent import BIAgent

# Initialize agent singleton
_agent = None

def get_agent():
    global _agent
    if _agent is None:
        _agent = BIAgent()
    return _agent

class handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.end_headers()

    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b'{}'
            data = json.loads(body.decode('utf-8')) if body else {}
            message = data.get("message", "leadership update")

            # Execute async agent pipeline
            agent = get_agent()
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(agent.process_question(message))
            loop.close()

            response_data = {
                "answer": result.get("answer", ""),
                "metrics": result.get("metrics"),
                "data_quality_notes": result.get("data_quality_notes", []),
                "assumptions": result.get("assumptions", [])
            }

            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response_data).encode('utf-8'))

        except Exception as e:
            self.send_response(500)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps({"detail": str(e)}).encode('utf-8'))

    def do_GET(self):
        self.do_POST()
