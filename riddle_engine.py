"""UniDic辞書から、資料に定義した文字・音・配置規則の謎解きを生成する。"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from itertools import permutations
from pathlib import Path
from typing import Callable

KANA_WORD = re.compile(r"^[ぁ-んァ-ン]{2,4}$")
TOP_WORD_LIMIT = 12600
KANA = "あいうえおかきくけこさしすせそたちつてとなにぬねのはひふへほまみむめもやゆよらりるれろわをん"
DAKUTEN = dict(zip("かきくけこさしすせそたちつてとはひふへほ", "がぎぐげござじずぜぞだぢづでどばびぶべぼ"))
DAKUTEN.update({v: k for k, v in list(DAKUTEN.items())})
HANDAKUTEN = dict(zip("はひふへほ", "ぱぴぷぺぽ"))
HANDAKUTEN.update({v: k for k, v in list(HANDAKUTEN.items())})
VOWELS = "あいうえお"
ROWS = ["かきくけこ", "がぎぐげご", "さしすせそ", "ざじずぜぞ", "たちつてと", "だぢづでど", "なにぬねの", "はひふへほ", "ばびぶべぼ", "ぱぴぷぺぽ", "まみむめも", "らりるれろ"]


def build_dictionary(lex_csv: Path, limit: int = TOP_WORD_LIMIT) -> set[str]:
    frequencies: dict[str, int] = {}
    with lex_csv.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 5:
                continue
            word, pos = row[0].strip(), row[4].strip()
            frequency = int(row[-1]) if row[-1].isdigit() else 999999999
            if pos in {"名詞", "副詞"} and KANA_WORD.fullmatch(word) and not re.search(r"(.)\1{2,}", word):
                frequencies[word] = min(frequencies.get(word, 999999999), frequency)
    return {word for word, _ in sorted(frequencies.items(), key=lambda item: (item[1], item[0]))[:limit]}


def build_curated_dictionary(word_list: Path) -> set[str]:
    return {w.strip() for w in word_list.read_text(encoding="utf-8").splitlines()
            if w.strip() and not w.lstrip().startswith("#") and KANA_WORD.fullmatch(w.strip())}


def replace_at(word: str, index: int, table: dict[str, str]) -> str | None:
    return word[:index] + table[word[index]] + word[index + 1:] if word[index] in table else None


def generate_rules() -> list[tuple[str, Callable[[str], list[str]]]]:
    rules: list[tuple[str, Callable[[str], list[str]]]] = []
    rules += [("先頭1文字削除", lambda w: [w[1:]] if len(w) >= 3 else []),
              ("末尾1文字削除", lambda w: [w[:-1]] if len(w) >= 3 else []),
              ("中間1文字削除", lambda w: [w[:i] + w[i + 1:] for i in range(1, len(w) - 1)] if len(w) >= 3 else [])]
    rules += [("先頭1文字追加", lambda w: [c + w for c in KANA] if len(w) < 4 else []),
              ("末尾1文字追加", lambda w: [w + c for c in KANA] if len(w) < 4 else []),
              ("中間1文字追加", lambda w: [w[:i] + c + w[i:] for i in range(1, len(w)) for c in KANA] if len(w) < 4 else [])]
    rules += [("先頭文字置換", lambda w: [c + w[1:] for c in KANA] if w else []),
              ("末尾文字置換", lambda w: [w[:-1] + c for c in KANA] if w else []),
              ("中間文字置換", lambda w: [w[:i] + c + w[i + 1:] for i in range(1, len(w) - 1) for c in KANA] if len(w) >= 3 else [])]
    rules.append(("濁点・清音変換", lambda w: [x for i in range(len(w)) if (x := replace_at(w, i, DAKUTEN))]))
    rules.append(("半濁点変換", lambda w: [x for i in range(len(w)) if (x := replace_at(w, i, HANDAKUTEN))]))
    rules.append(("母音変換", lambda w: [w[:i] + v + w[i + 1:] for i, ch in enumerate(w) if ch in VOWELS for v in VOWELS if v != ch]))
    rules.append(("子音スライド", lambda w: [w[:i] + c + w[i + 1:] for i, ch in enumerate(w) for row in ROWS if ch in row for c in row if c != ch]))
    rules.append(("逆読み", lambda w: [w[::-1]] if len(w) >= 2 else []))
    rules.append(("並び替え", lambda w: ["".join(p) for p in permutations(w) if "".join(p) not in {w, w[::-1]}]))
    return rules


def search_pairs(dictionary: set[str]) -> list[dict[str, str]]:
    pairs, seen = [], set()
    for word in sorted(dictionary):
        for rule_name, transform in generate_rules():
            for result in transform(word):
                key = (word, result, rule_name)
                if result in dictionary and result != word and key not in seen:
                    seen.add(key)
                    pairs.append({"source": word, "answer": result, "rule": rule_name})
    return pairs


def edit_distance(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        previous, row[0] = row[0], i
        for j, target in enumerate(right, 1):
            saved = row[j]
            row[j] = min(row[j] + 1, row[j - 1] + 1, previous + (char != target))
            previous = saved
    return row[-1]


def judge(source: str, answer: str) -> dict[str, int | str]:
    distance = edit_distance(source, answer)
    score = max(0, round((1 - distance / max(len(source), len(answer))) * 100))
    return {"score": score, "distance": distance, "result": "採用" if score >= 50 else "除外"}


def make_puzzle(pairs: list[dict[str, str]], rng: random.Random) -> dict:
    if len(pairs) < 3:
        raise ValueError("問題生成には、成立する単語ペアが3組以上必要です。")
    main = rng.choice(pairs)
    examples = rng.sample([p for p in pairs if p["source"] != main["source"]], 2)
    return {"problem": [f"{p['source']} → {p['answer']}" for p in examples] + [f"{main['source']} → ？"],
            "answer": main["answer"], "rule": main["rule"],
            "hints": ["矢印の前後で、文字の位置・数・音の変化を比べてみよう。", f"元の単語は{len(main['source'])}文字、答えは{len(main['answer'])}文字です。", f"例題の「{examples[0]['source']}」にも「{examples[0]['rule']}」が使われています。"],
            "explanation": f"「{main['source']}」に「{main['rule']}」を適用すると「{main['answer']}」になります。", "judgement": judge(main["source"], main["answer"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lex-csv", type=Path)
    parser.add_argument("--word-list", type=Path)
    parser.add_argument("--output", type=Path, default=Path("generated_puzzle.json"))
    parser.add_argument("--pairs-js", type=Path, default=Path("generated_pairs.js"))
    parser.add_argument("--words-js", type=Path, default=Path("unidic_candidates.js"))
    parser.add_argument("--limit", type=int, default=TOP_WORD_LIMIT)
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    if not args.word_list and not args.lex_csv:
        parser.error("--lex-csv または --word-list が必要です")
    dictionary = build_curated_dictionary(args.word_list) if args.word_list else build_dictionary(args.lex_csv, args.limit)
    pairs = search_pairs(dictionary)
    payload = {"dictionary_count": len(dictionary), "pair_count": len(pairs), "puzzle": make_puzzle(pairs, random.Random(args.seed))}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.pairs_js.write_text("window.generatedPairs = " + json.dumps(pairs, ensure_ascii=False) + ";\n", encoding="utf-8")
    if not args.word_list:
        args.words_js.write_text("window.unidicCandidates = " + json.dumps(sorted(dictionary), ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
