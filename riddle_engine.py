"""UniDicのlex.csvから、先頭1文字削除型の謎解きを生成する実行エンジン。"""
from __future__ import annotations

import argparse
import csv
import json
import random
import re
from pathlib import Path

KANA_WORD = re.compile(r"^[ぁ-んァ-ン]{2,4}$")


def build_dictionary(lex_csv: Path) -> set[str]:
    """UniDic lex.csvから2〜4文字の名詞・副詞を抽出する。"""
    words: set[str] = set()
    with lex_csv.open(encoding="utf-8", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 5:
                continue
            word, pos = row[0].strip(), row[4].strip()
            if pos in {"名詞", "副詞"} and KANA_WORD.fullmatch(word):
                if not re.search(r"(.)\1{2,}", word):
                    words.add(word)
    return words


def build_curated_dictionary(word_list: Path) -> set[str]:
    return {
        word.strip() for word in word_list.read_text(encoding="utf-8").splitlines()
        if word.strip() and not word.lstrip().startswith("#") and KANA_WORD.fullmatch(word.strip())
    }


def search_pairs(dictionary: set[str]) -> list[dict[str, str]]:
    """辞書内の全単語へ固定規則を適用し、成立したペアだけ返す。"""
    return [
        {"source": word, "answer": word[1:], "rule": "先頭1文字削除"}
        for word in sorted(dictionary)
        if len(word) >= 3 and word[1:] in dictionary
    ]


def edit_distance(left: str, right: str) -> int:
    row = list(range(len(right) + 1))
    for i, left_char in enumerate(left, 1):
        previous = row[0]
        row[0] = i
        for j, right_char in enumerate(right, 1):
            saved = row[j]
            row[j] = min(row[j] + 1, row[j - 1] + 1, previous + (left_char != right_char))
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
    examples = rng.sample([pair for pair in pairs if pair["source"] != main["source"]], 2)
    judged = judge(main["source"], main["answer"])
    return {
        "problem": [f"{item['source']} → {item['answer']}" for item in examples] + [f"{main['source']} → ？"],
        "answer": main["answer"],
        "hints": [
            "矢印の前と後で、文字の位置を比べてみよう。",
            f"元の単語は{len(main['source'])}文字、答えは{len(main['answer'])}文字です。",
            f"例題の「{examples[0]['source']}」も、先頭の1文字を削除すると「{examples[0]['answer']}」になります。",
        ],
        "explanation": f"例題は先頭の1文字を削除する規則です。「{main['source']}」から先頭の「{main['source'][0]}」を削除すると「{main['answer']}」になります。",
        "judgement": judged,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="UniDicから謎解き問題を生成します")
    parser.add_argument("--lex-csv", type=Path, required=True, help="UniDicのlex.csv")
    parser.add_argument("--word-list", type=Path, help="事前確認済みの採用単語一覧（指定時はこちらを優先）")
    parser.add_argument("--output", type=Path, default=Path("generated_puzzle.json"))
    parser.add_argument("--pairs-js", type=Path, default=Path("generated_pairs.js"))
    parser.add_argument("--seed", type=int, default=None)
    args = parser.parse_args()
    dictionary = build_curated_dictionary(args.word_list) if args.word_list else build_dictionary(args.lex_csv)
    pairs = search_pairs(dictionary)
    puzzle = make_puzzle(pairs, random.Random(args.seed))
    payload = {"dictionary_count": len(dictionary), "pair_count": len(pairs), "puzzle": puzzle}
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    args.pairs_js.write_text("window.generatedPairs = " + json.dumps(pairs, ensure_ascii=False) + ";\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
