"""The OpenAI-compatible backend against a tiny local server that behaves like a picky API."""

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from gasp.policies.llm import OpenAICompatibleBackend


class PickyHandler(BaseHTTPRequestHandler):
    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        PickyHandler.seen.append(body)
        if "max_tokens" in body:
            self._reply(400, {"error": {"message": "Unsupported parameter: 'max_tokens' is not supported with this model. Use 'max_completion_tokens' instead."}})
            return
        if "temperature" in body and body["temperature"] != 1:
            self._reply(400, {"error": {"message": "Unsupported value: 'temperature' does not support 0.7 with this model."}})
            return
        self._reply(200, {"choices": [{"message": {"content": '{"action_type": "noop"}'}}],
                          "usage": {"prompt_tokens": 12, "completion_tokens": 5}})

    def _reply(self, code, payload):
        data = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *args):
        pass


def test_backend_adapts_parameters_to_the_server():
    server = HTTPServer(("127.0.0.1", 0), PickyHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        backend = OpenAICompatibleBackend("picky-model", base_url=f"http://127.0.0.1:{port}", api_key_env="NO_SUCH_KEY")
        text, usage = backend.complete("sys", "user", 0.7, 100)
        assert text == '{"action_type": "noop"}'
        assert usage == {"tokens_in": 12, "tokens_out": 5}
        assert "max_tokens -> max_completion_tokens" in backend.adaptations
        assert "temperature dropped (model default used)" in backend.adaptations
        assert "max_completion_tokens" in PickyHandler.seen[-1] and "temperature" not in PickyHandler.seen[-1]
        assert PickyHandler.seen[-1]["response_format"] == {"type": "json_object"}
    finally:
        server.shutdown()


class LocalReasoningHandler(BaseHTTPRequestHandler):
    """A vLLM-like local server: no key, rejects an unknown request field, answers with thinking."""

    seen = []

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        LocalReasoningHandler.seen.append((dict(self.headers), body))
        if "reasoning_effort" in body:
            self._reply(400, {"error": {"message": "Unrecognized request argument supplied: reasoning_effort"}})
            return
        self._reply(200, {"choices": [{"message": {"reasoning_content": "the road is blocked, so noop",
                                                    "content": '<think>draft {"action_type": "query_evidence"}</think>{"action_type": "noop"}'}}],
                          "usage": {"prompt_tokens": 30, "completion_tokens": 40}})

    _reply = PickyHandler._reply
    log_message = PickyHandler.log_message


def test_backend_talks_to_a_local_server_without_a_key_and_drops_rejected_fields():
    server = HTTPServer(("127.0.0.1", 0), LocalReasoningHandler)
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        backend = OpenAICompatibleBackend("glimmer", base_url=f"http://127.0.0.1:{port}/v1", api_key_env="NO_SUCH_KEY",
                                          extra_body={"reasoning_effort": "low"}, timeout=30)
        text, usage = backend.complete("sys", "user", 0.7, 800)
        assert text.endswith('{"action_type": "noop"}') and usage == {"tokens_in": 30, "tokens_out": 40}
        assert backend.adaptations == ["reasoning_effort dropped (server rejected it)"]
        headers, body = LocalReasoningHandler.seen[-1]
        assert "Authorization" not in headers and "reasoning_effort" not in body and body["max_tokens"] == 800
        assert "reasoning_effort" in LocalReasoningHandler.seen[0][1]
    finally:
        server.shutdown()
