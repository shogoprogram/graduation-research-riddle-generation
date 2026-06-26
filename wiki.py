import wikipediaapi
import re
import fugashi

dic_dir = 'C:/Users/ikeza/Desktop/3年4年/研究/卒業研究を考える/unidic-cwj-202512'
tagger = fugashi.GenericTagger(f'-d "{dic_dir}" -r "{dic_dir}/dicrc"')

wiki = wikipediaapi.Wikipedia('ResearchBot (test@example.com)', 'ja')

# 取得するカテゴリ・記事
pages = [
    '動物', '植物', '食べ物', '日本の地名', 'スポーツ', '乗り物', '天気', '自然'
]

nouns = set()
adverbs = set()

def is_valid(w):
    return bool(re.fullmatch(r'[ぁ-んァ-ン]{2,4}', w))

for title in pages:
    page = wiki.page(title)
    if not page.exists():
        print(f"取得失敗: {title}")
        continue
    text = page.text[:5000]  # 最初の5000文字だけ
    for word in tagger(text):
        w = word.surface
        if not is_valid(w):
            continue
        pos = word.feature[0]
        if pos == '名詞':
            nouns.add(w)
        elif pos == '副詞':
            adverbs.add(w)
    print(f"取得完了: {title} / 名詞{len(nouns)} 副詞{len(adverbs)}")

print(f"\n名詞: {len(nouns)}個")
for w in sorted(nouns)[:30]:
    print(w)

print(f"\n副詞: {len(adverbs)}個")
for w in sorted(adverbs)[:30]:
    print(w)