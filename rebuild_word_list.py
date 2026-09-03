"""Rebuild the embedded 12,600-word dictionary from the original UniDic CSV."""
from __future__ import annotations

import csv
import gzip
import json
import re
from pathlib import Path

ROOT = Path(__file__).parent
SOURCE = Path(r"C:\Users\ikeza\Downloads\unidic-cwj-202512_full\lex.csv")
LIMIT = 12600

# 明らかに謎解き用語として不適切な語。除外した分は頻度順の次候補で補充する。
EXCLUDED = {
    # 侮辱・卑語・性的語
    "ばか", "あほ", "まぬけ", "ぽるの", "せっくす", "わいせつ", "ちかん", "れいぷ",
    "ちんこ", "ちんぽ", "まんこ", "おっぱい", "ふたなり", "ろりこん", "しょうじょあい",
    # 薬物・自傷など、小学生向けの謎解きには使わない語
    "あへん", "まやく", "たいま", "しゃぶ", "へろいん", "ここいん", "じさつ", "しね",
    "しぬ", "ころし", "ころす", "さつじん", "やくざ",
    # UniDicでは品詞が付くが、単独の謎解き用単語として不自然な語・語の断片。
    "ちゅ", "もったい", "そぅ", "そおお",
}


def katakana_to_hiragana(text):
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in text)


MODERN_SPELLINGS = {
    "すぽおつ": "すぽーつ",
    "げえむ": "げーむ",
}


def build_words():
    best_cost = {}
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 6:
                continue
            source_word = row[0]
            pronunciation = katakana_to_hiragana(row[13]) if len(row) > 13 else source_word
            # 表記と発音が食い違う古い表記は原則除外する。
            # ただし、現代でも普通に使う外来語だけは明示的に現代表記へ直す。
            word = MODERN_SPELLINGS.get(source_word, source_word)
            if source_word != pronunciation and source_word not in MODERN_SPELLINGS:
                continue
            if any(char in source_word for char in "ぁぃぅぇぉ"):
                continue
            if source_word in EXCLUDED or not re.fullmatch(r"[ぁ-んー]{2,4}", word):
                continue
            # 普通名詞・副詞に限定し、固有名詞・人名・古い片仮名表記を除外。
            if not (row[4] == "副詞" or (row[4] == "名詞" and row[5] == "普通名詞")):
                continue
            if word in EXCLUDED:
                continue
            cost = int(row[3])
            if cost < best_cost.get(word, 10**18):
                best_cost[word] = cost
    return sorted(best_cost, key=lambda word: (best_cost[word], word))[:LIMIT]


def main():
    words = build_words()
    if len(words) != LIMIT:
        raise RuntimeError("候補が12,600語に届きません: %d語" % len(words))
    packed = gzip.compress(json.dumps(words, ensure_ascii=False, separators=(",", ":")).encode("utf-8"), compresslevel=9)
    encoded = __import__("base64").b64encode(packed).decode("ascii")

    app_path = ROOT / "app.py"
    app_text = app_path.read_text(encoding="utf-8")
    app_text = re.sub(r'WORD_LIST_DATA = ".*?"', 'WORD_LIST_DATA = "' + encoded + '"', app_text, count=1)
    literal = "WORD_LIST = " + repr(words).replace("'", '"')
    app_text = re.sub(r"WORD_LIST = \[.*?\]\n", literal + "\n", app_text, count=1, flags=re.DOTALL)
    app_path.write_text(app_text, encoding="utf-8")

    js_path = ROOT / "unidic_candidates.js"
    js_path.write_text("window.UNIDIC_CANDIDATES = " + json.dumps(words, ensure_ascii=False) + ";\n", encoding="utf-8")
    print("再構築完了: %d語" % len(words))
    print("除外語: " + ", ".join(sorted(EXCLUDED)))


if __name__ == "__main__":
    main()
