import requests
from bs4 import BeautifulSoup
import re
import fugashi
import time

dic_dir = 'C:/Users/ikeza/Desktop/3年4年/研究/卒業研究を考える/unidic-cwj-202512'
tagger = fugashi.GenericTagger(f'-d "{dic_dir}" -r "{dic_dir}/dicrc"')

urls = [
    "https://www.aozora.gr.jp/cards/000035/files/1567_14913.html",
    "https://www.aozora.gr.jp/cards/000148/files/773_14560.html",
    "https://www.aozora.gr.jp/cards/000879/files/127_15260.html",
    "https://www.aozora.gr.jp/cards/000081/files/456_15050.html",
    "https://www.aozora.gr.jp/cards/000121/files/628_14895.html",
]

nouns = set()   # 名詞
adverbs = set() # 副詞

def is_valid(w):
    return bool(re.fullmatch(r'[ぁ-んァ-ン]{2,4}', w))

for url in urls:
    try:
        response = requests.get(url)
        response.encoding = 'shift_jis'
        soup = BeautifulSoup(response.text, 'html.parser')
        main = soup.find('div', class_='main_text')
        if main is None:
            print(f"本文取得失敗: {url}")
            continue
        text = main.get_text()
        for word in tagger(text):
            w = word.surface
            if not is_valid(w):
                continue
            feature = word.feature
            if len(feature) == 0:
                continue
            pos = feature[0]  # pos1の代わりにfeature[0]
            if pos == '名詞':
                nouns.add(w)
            elif pos == '副詞':
                adverbs.add(w)
        print(f"取得完了: {url} / 名詞{len(nouns)} 副詞{len(adverbs)}")
        time.sleep(1)
    except Exception as e:
        print(f"エラー: {url} / {e}")

print(f"\n名詞: {len(nouns)}個")
for w in sorted(nouns)[:20]:
    print(w)

print(f"\n副詞: {len(adverbs)}個")
for w in sorted(adverbs):
    print(w)