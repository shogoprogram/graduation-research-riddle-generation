"""謎解きシステム本体。単語探索、規則適用、AI生成、Webサーバーを1本で行う。"""
from __future__ import annotations

import csv
import json
import os
import random
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import permutations
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent
KANA_WORD = re.compile(r"^[ぁ-んァ-ン]{2,4}$")
KANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
VOWELS = "あいうえお"
ROWS = ["かきくけこ", "がぎぐげご", "さしすせそ", "ざじずぜぞ", "たちつてと", "だぢづでど", "なにぬねの", "はひふへほ", "ばびぶべぼ", "ぱぴぷぺぽ", "まみむめも", "らりるれろ"]
DAKUTEN = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
DAKUTEN.update({v: k for k, v in list(DAKUTEN.items())})
HANDAKUTEN = dict(zip("はひふへほ", "ぱぴぷぺぽ"))
HANDAKUTEN.update({v: k for k, v in list(HANDAKUTEN.items())})


def build_dictionary(words):
    return {w.strip() for w in words if isinstance(w, str) and KANA_WORD.fullmatch(w.strip())}


def replace_at(word, index, table):
    return word[:index] + table[word[index]] + word[index + 1:] if word[index] in table else None


def replacements(word, table):
    result = []
    for i in range(len(word)):
        value = replace_at(word, i, table)
        if value:
            result.append(value)
    return result


def rules():
    return [
        ("先頭1文字削除", lambda w: [w[1:]] if len(w) >= 3 else []),
        ("末尾1文字削除", lambda w: [w[:-1]] if len(w) >= 3 else []),
        ("中間1文字削除", lambda w: [w[:i] + w[i + 1:] for i in range(1, len(w) - 1)] if len(w) >= 3 else []),
        ("先頭1文字追加", lambda w: [c + w for c in KANA] if len(w) < 4 else []),
        ("末尾1文字追加", lambda w: [w + c for c in KANA] if len(w) < 4 else []),
        ("中間1文字追加", lambda w: [w[:i] + c + w[i:] for i in range(1, len(w)) for c in KANA] if len(w) < 4 else []),
        ("先頭文字置換", lambda w: [c + w[1:] for c in KANA]),
        ("末尾文字置換", lambda w: [w[:-1] + c for c in KANA]),
        ("中間文字置換", lambda w: [w[:i] + c + w[i + 1:] for i in range(1, len(w) - 1) for c in KANA] if len(w) >= 3 else []),
        ("濁点・清音変換", lambda w: replacements(w, DAKUTEN)),
        ("半濁点変換", lambda w: replacements(w, HANDAKUTEN)),
        ("母音変換", lambda w: [w[:i] + v + w[i + 1:] for i, ch in enumerate(w) if ch in VOWELS for v in VOWELS if v != ch]),
        ("子音スライド", lambda w: [w[:i] + c + w[i + 1:] for i, ch in enumerate(w) for row in ROWS if ch in row for c in row if c != ch]),
        ("逆読み", lambda w: [w[::-1]]),
        ("並び替え", lambda w: ["".join(p) for p in permutations(w) if "".join(p) not in {w, w[::-1]}]),
    ]


def search_pairs(dictionary):
    found, seen = [], set()
    for word in sorted(dictionary):
        for name, transform in rules():
            for answer in transform(word):
                key = (word, answer, name)
                if answer in dictionary and answer != word and key not in seen:
                    seen.add(key)
                    found.append({"source": word, "answer": answer, "rule": name})
    return found


def edit_distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        previous, row[0] = row[0], i
        for j, y in enumerate(b, 1):
            saved = row[j]
            row[j] = min(row[j] + 1, row[j - 1] + 1, previous + (x != y))
            previous = saved
    return row[-1]


def judge(source, answer):
    distance = edit_distance(source, answer)
    score = max(0, round((1 - distance / max(len(source), len(answer))) * 100))
    return {"score": score, "distance": distance, "result": "採用" if score >= 50 else "除外"}


def fallback(pairs):
    main = random.choice(pairs)
    examples = random.sample([p for p in pairs if p["source"] != main["source"]], 2)
    return {"title": "生成された謎", "problem": [f"{p['source']} → {p['answer']}" for p in examples] + [f"{main['source']} → ？"], "answer": main["answer"], "rule": main["rule"], "hints": ["矢印の前後で、文字の位置・数・音の変化を比べてみよう。", f"元の単語は{len(main['source'])}文字、答えは{len(main['answer'])}文字です。", f"例題の「{examples[0]['source']}」にも同じ規則が使われています。"], "explanation": f"「{main['source']}」に「{main['rule']}」を適用すると「{main['answer']}」になります。", "judgement": judge(main["source"], main["answer"])}


def ai_generate(pairs):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return fallback(pairs), False
    prompt = {"pairs": pairs[:60], "request": "同じruleの単語ペアを3つ選び、小学生向けの謎解きを作成してください。JSONのみで返してください。", "format": {"title": "文字列", "problem": ["文字列"], "hints": ["文字列", "文字列", "文字列"], "answer": "文字列", "explanation": "文字列"}}
    body = json.dumps({"contents": [{"parts": [{"text": json.dumps(prompt, ensure_ascii=False)}]}], "generationConfig": {"responseMimeType": "application/json"}}).encode()
    request = Request(f"https://generativelanguage.googleapis.com/v1beta/models/{os.environ.get('GEMINI_MODEL', 'gemini-2.0-flash')}:generateContent?key={key}", data=body, headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=45) as response:
        data = json.load(response)
    puzzle = json.loads(data["candidates"][0]["content"]["parts"][0]["text"])
    selected = next((p for p in pairs if p["answer"] == puzzle.get("answer")), None)
    if selected is None or len(puzzle.get("hints", [])) != 3:
        raise ValueError("AIの返却内容を検証できませんでした")
    puzzle["judgement"] = judge(selected["source"], selected["answer"])
    puzzle["rule"] = selected["rule"]
    return puzzle, True


class Handler(BaseHTTPRequestHandler):
    def send_json(self, status, value):
        raw = json.dumps(value, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self):
        self.send_json(204, {})

    def do_GET(self):
        if self.path in {"/", "/index.html"}:
            raw = (ROOT / "index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(raw)
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        if self.path != "/api/generate":
            self.send_json(404, {"error": "Not found"})
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            words = build_dictionary(payload.get("words", []))
            pairs = search_pairs(words)
            if len(pairs) < 3:
                raise ValueError("成立する単語ペアが3組未満です")
            puzzle, used = ai_generate(pairs)
            self.send_json(200, {"puzzle": puzzle, "wordCount": len(words), "pairCount": len(pairs), "aiUsed": used})
        except Exception as error:
            self.send_json(400, {"error": str(error)})


if __name__ == "__main__":
    print("http://localhost:8000 で起動しました")
    ThreadingHTTPServer(("localhost", 8000), Handler).serve_forever()
