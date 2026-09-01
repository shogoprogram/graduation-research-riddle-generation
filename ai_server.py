"""ローカル実行用のGemini APIサーバー。APIキーは環境変数 GEMINI_API_KEY から読む。"""
from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def ask_gemini(payload: dict) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY が設定されていません。")
    prompt = {
        "pairs": payload.get("pairs", [])[:30],
        "request": "小学生にも分かる謎解きを1問作成してください。提示したペア群から、同じ規則の例題2つと問題1つを選び、ヒント3段階、答え、短い解説を作ってください。答えは問題のペアのanswerと一致させてください。",
        "format": {"title": "文字列", "problem": ["文字列"], "hints": ["文字列", "文字列", "文字列"], "answer": "文字列", "explanation": "文字列"},
    }
    body = json.dumps({"contents": [{"parts": [{"text": json.dumps(prompt, ensure_ascii=False)}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode()
    request = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={key}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=45) as response:
        result = json.load(response)
    text = result["candidates"][0]["content"]["parts"][0]["text"]
    generated = json.loads(text)
    required = {"title", "problem", "hints", "answer", "explanation"}
    if not required <= generated.keys() or len(generated["hints"]) != 3:
        raise ValueError("AIの返却形式が不正です。")
    return generated


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, data: dict):
        raw = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self._send(204, {})

    def do_POST(self):
        if self.path != "/api/generate":
            self._send(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length))
            self._send(200, {"puzzle": ask_gemini(data)})
        except Exception as error:
            self._send(400, {"error": str(error)})

    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            raw = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(raw)
        else:
            self._send(404, {"error": "Not found"})


if __name__ == "__main__":
    print("http://localhost:8000 で起動しました")
    ThreadingHTTPServer(("localhost", 8000), Handler).serve_forever()
