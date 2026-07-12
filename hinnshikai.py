import csv
import re

lex_path = r'C:\Users\ikeza\Downloads\unidic-cwj-202512_full\lex.csv'

nouns = {}
adverbs = {}

def is_valid(w):
    # 1. 2文字以上4文字以内であること
    if not re.fullmatch(r'[ぁ-んァ-ン]{2,4}', w):
        return False
    
    # 2. 3文字以上の同じ文字の繰り返しを除外する（例：あああ、いいいい）
    # (.) は任意の1文字、\1{2,} はその文字が2回以上続くこと（合計3回以上）
    if re.search(r'(.)\1{2,}', w):
        return False
    
    return True

with open(lex_path, encoding='utf-8') as f:
    for row in csv.reader(f):
        if len(row) < 5:
            continue
        word = row[0]
        pos = row[4]
        pos2 = row[5] if len(row) > 5 else ''
        
        # 除外ルールの適用
        if not is_valid(word):
            continue
            
        freq = int(row[-1]) if row[-1].isdigit() else 0
        
        if pos == '名詞' and pos2 == '普通名詞':
            nouns[word] = nouns.get(word, 0) + freq
        elif pos == '副詞':
            adverbs[word] = adverbs.get(word, 0) + freq

# 頻度上位のみ表示
threshold = 500000
filtered_nouns = {w for w, f in nouns.items() if f >= threshold}
filtered_adverbs = {w for w, f in adverbs.items() if f >= threshold}

print(f"名詞: {len(filtered_nouns)}個")
print(f"副詞: {len(filtered_adverbs)}個")

# 結果を表示
print("--- 名詞（上位） ---")
for w in sorted(filtered_nouns)[:30]:
    print(w)