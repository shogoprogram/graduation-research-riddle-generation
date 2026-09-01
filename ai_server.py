"""ローカル実行用のGemini APIサーバー。APIキーは環境変数 GEMINI_API_KEY から読む。"""
from __future__ import annotations

import json
import os
import random
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
from riddle_engine import judge, make_puzzle, search_pairs

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")


def ask_gemini(payload: dict) -> dict:
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY が設定されていません。")
    prompt = {
        "pairs": payload.get("pairs", [])[:60],
        "request": "提示した単語ペア群を探索結果として確認し、同じruleのペアを3つ選んで、小学生にも分かる謎解きを1問作成してください。例題2つと問題1つ、ヒント3段階、答え、短い解説を作ってください。",
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
    selected = next((p for p in payload.get("pairs", []) if p.get("source") == generated.get("answer_source") and p.get("answer") == generated.get("answer")), None)
    if selected is None:
        selected = next((p for p in payload.get("pairs", []) if p.get("answer") == generated.get("answer")), None)
    if selected is None:
        raise ValueError("AIが辞書内にない答えを返しました。")
    generated["judgement"] = judge(selected["source"], selected["answer"])
    generated["rule"] = selected["rule"]
    return generated


def generate(payload: dict) -> tuple[dict, int, int]:
    """単語探索→規則ペア作成→AI生成。AIが使えない場合は固定生成へ退避する。"""
    words = {str(word).strip() for word in payload.get("words", []) if isinstance(word, str)}
    pairs = search_pairs(words)
    if len(pairs) < 3:
        raise ValueError("成立する単語ペアが3組未満です。単語を追加してください。")
    try:
        puzzle = ask_gemini({"pairs": pairs})
        return puzzle, len(words), len(pairs)
    except Exception as error:
        if os.environ.get("AI_REQUIRED") == "1":
            raise
        puzzle = make_puzzle(pairs, random.Random())
        puzzle["aiFallback"] = str(error)
        return puzzle, len(words), len(pairs)


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
            puzzle, word_count, pair_count = generate(data)
            self._send(200, {"puzzle": puzzle, "wordCount": word_count, "pairCount": pair_count, "aiUsed": "aiFallback" not in puzzle})
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
