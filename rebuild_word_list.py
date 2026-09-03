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
    "ちゅ", "もったい", "そぅ", "そおお", "かっかっ",
    # スラング・意味が不明瞭なカタカナ語（表記揺れも含めて除外）。
    "まんさん", "マンさん", "てりぶる", "テリブル", "なみんぐ", "ナミング",
}


def katakana_to_hiragana(text):
    return "".join(chr(ord(char) - 0x60) if "ァ" <= char <= "ヶ" else char for char in text)


def build_words():
    source_best = {}
    with SOURCE.open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.reader(stream):
            if len(row) < 6:
                continue
            source_word = row[0]
            if source_word in EXCLUDED:
                continue
            # 元データ側の読みも2〜4文字に限定する。見出し語だけで判定すると、別語形が大量に混ざる。
            if not re.fullmatch(r"[ぁ-んァ-ヶー]{2,4}", source_word):
                continue
            # 読み（とーてー）ではなく、UniDicの語彙見出し（トウテイ）を使う。
            # 和語はひらがな、外来語は一般的なカタカナ表記にする。
            lexical_form = row[10] if len(row) > 10 else source_word
            word = lexical_form if (len(row) > 16 and row[16] == "外") else katakana_to_hiragana(lexical_form)
            if not re.fullmatch(r"[ぁ-んァ-ヶー]{2,4}", word):
                continue
            if any(char in source_word for char in "ぁぃぅぇぉ"):
                continue
            if source_word in EXCLUDED or not re.fullmatch(r"[ぁ-んァ-ヶー]{2,4}", word):
                continue
            # 普通名詞・副詞に限定し、固有名詞・人名・古い片仮名表記を除外。
            if not (row[4] == "副詞" or (row[4] == "名詞" and row[5] == "普通名詞")):
                continue
            if word in EXCLUDED:
                continue
            cost = int(row[3])
            if cost < source_best.get(source_word, (10**18, ""))[0]:
                source_best[source_word] = (cost, word)
    # 頻度順位は元の候補語で決め、標準表記への変換後に重複だけを除く。
    words = []
    seen = set()
    for source_word in sorted(source_best, key=lambda source: (source_best[source][0], source)):
        word = source_best[source_word][1]
        if word in seen:
            continue
        seen.add(word)
        words.append(word)
        if len(words) == LIMIT:
            break
    return words


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
