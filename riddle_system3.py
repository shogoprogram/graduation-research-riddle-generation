import hinan

print(hinan.__file__)
print(dir(hinan))
import requests
from bs4 import BeautifulSoup
import re
import fugashi
import time
import wikipediaapi
import csv
import random
from hinan import API_KEY
from google import genai

# ===== 設定 =====
dic_dir = 'C:/Users/ikeza/Desktop/3年4年/研究/卒業研究を考える/unidic-cwj-202512'
tagger = fugashi.GenericTagger(f'-d "{dic_dir}" -r "{dic_dir}/dicrc"')

# ===== ① 辞書構築 =====
def build_dictionary():
    import csv
    
    lex_path = r'C:\Users\ikeza\Downloads\unidic-cwj-202512_full\lex.csv'
    
    nouns = set()
    adverbs = set()

    def is_valid(w):
        return bool(re.fullmatch(r'[ぁ-んァ-ン]{2,4}', w))

    print("読み込み中...")
    with open(lex_path, encoding='utf-8') as f:
        for row in csv.reader(f):
            if len(row) < 5:
                continue
            word = row[0]
            pos = row[4]
            if not is_valid(word):
                continue
            if pos == '名詞':
                nouns.add(word)
            elif pos == '副詞':
                adverbs.add(word)

    print(f"\n①辞書構築完了: 名詞{len(nouns)}個 副詞{len(adverbs)}個")
    return nouns, adverbs

# ===== ② 規則生成（テスト：先頭削除のみ固定） =====
def generate_rules():
    rules = [
        ('先頭削除', lambda w: w[1:]),
    ]
    return rules

# ===== ④ 探索 =====
def search_pairs(dictionary, rules):
    three_char = [w for w in dictionary if len(w) == 3]
    pairs = []
    for word in three_char:
        for rule_name, rule_func in rules:
            result = rule_func(word)
            if result in dictionary:
                pairs.append((word, result, rule_name))
    return pairs

# ===== ⑤ 問題生成 =====
def generate_problem(pairs):
    main_pair = random.choice(pairs)
    examples = [p for p in pairs if p[0] != main_pair[0]]
    example_pairs = random.sample(examples, min(2, len(examples)))
    return main_pair, example_pairs

# ===== ⑥ ヒント生成（AI使用） =====
def generate_hints(word, answer, rule_name, example_pairs):
    import google.genai as genai
    import json

    ex1_word, ex1_answer, _ = example_pairs[0]
    ex2_word, ex2_answer, _ = example_pairs[1]

    client = genai.Client(api_key=API_KEY)

    prompt = f"""謎解き問題のヒントを3段階で作ってください。また、解説文も作ってください。

例題1：「{ex1_word}」→「{ex1_answer}」
例題2：「{ex2_word}」→「{ex2_answer}」
問題の単語：「{word}」
答え：「{answer}」
規則：先頭の1文字が消える

以下のJSON形式のみで返してください。他の文字は一切含めないでください。
ヒント3では答えの単語や消えた文字を絶対に言わないでください。例題を使って説明してください。
explanationは「上は〇〇から〇〇、下は〇〇から〇〇になっており、〇〇という法則になっていることが考えられます。そのため、〇〇は〇〇になるので、答えは〇〇です。」という形式で書いてください。
{{"hint1": "変換について考えさせるヒント", "hint2": "文字数や位置についてのヒント", "hint3": "例題を使って規則を説明するヒント", "explanation": "解説文"}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        text = response.text.strip().replace('```json', '').replace('```', '')
        hints_data = json.loads(text)
        return [hints_data['hint1'], hints_data['hint2'], hints_data['hint3']], hints_data['explanation']
    except Exception as e:
        print(f"AI生成エラー: {e}")
        hints = [
            f"矢印の前と後でどう変わっているか考えてみよう",
            f"文字数は{len(word)}文字から{len(answer)}文字に変わっています",
            f"例えば「{ex1_word}」は先頭の「{ex1_word[0]}」が消えて「{ex1_answer}」になっていますね",
        ]
        explanation = f"上は「{ex1_word}」から「{ex1_answer}」、下は「{ex2_word}」から「{ex2_answer}」になっており、先頭の1文字が消えるという法則になっていることが考えられます。そのため、「{word}」は先頭の文字が消えるので、答えは「{answer}」です。"
        return hints, explanation

# ===== ⑦ 判定 =====
def judge(word, answer):
    a, b = word, answer
    dp = [[0]*(len(b)+1) for _ in range(len(a)+1)]
    for i in range(len(a)+1):
        dp[i][0] = i
    for j in range(len(b)+1):
        dp[0][j] = j
    for i in range(1, len(a)+1):
        for j in range(1, len(b)+1):
            if a[i-1] == b[j-1]:
                dp[i][j] = dp[i-1][j-1]
            else:
                dp[i][j] = 1 + min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    dist = dp[len(a)][len(b)]
    if dist == 0:
        return 0
    score = max(0, 100 - dist * 20)
    return score

# ===== ⑧ HTML出力 =====
def generate_html(main_pair, example_pairs, hints):
    word, answer, rule_name = main_pair
    score = judge(word, answer)

    ex_html = ""
    for ew, ea, _ in example_pairs:
        ex_html += f'<div class="example">{ew} → {ea}</div>\n'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<title>謎解き</title>
<style>
  body {{ font-family: sans-serif; max-width: 600px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
  .card {{ background: white; border-radius: 12px; padding: 30px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
  h1 {{ color: #4a7c4e; text-align: center; }}
  h2 {{ color: #4a7c4e; }}
  .example {{ font-size: 1.3em; margin: 8px 0; color: #555; }}
  .question {{ font-size: 1.6em; font-weight: bold; margin: 20px 0; color: #222; text-align: center; }}
  .hint-box {{ background: #e8f5e9; border-radius: 8px; padding: 15px; margin: 10px 0; display: none; }}
  .hint-box.show {{ display: block; }}
  button {{ background: #4a7c4e; color: white; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 1em; margin: 8px 4px; }}
  button:hover {{ background: #3a6a3e; }}
  .answer-box {{ background: #fff3e0; border-radius: 8px; padding: 20px; margin: 10px 0; display: none; font-size: 1.4em; text-align: center; }}
  .answer-box.show {{ display: block; }}
  .score {{ color: #4a7c4e; font-weight: bold; font-size: 0.9em; }}
</style>
</head>
<body>
<h1>🔤 謎解き</h1>

<div class="card">
  <div class="example">{example_pairs[0][0]} → {example_pairs[0][1]}</div>
  <div class="example">{example_pairs[1][0]} → {example_pairs[1][1]}</div>
  <div class="example">{word} → ？</div>
</div>

<div class="card">
  <h2>ヒント</h2>
  <button onclick="showHint(0)">ヒント①</button>
  <button onclick="showHint(1)">ヒント②</button>
  <button onclick="showHint(2)">ヒント③</button>
  <div id="hint0" class="hint-box">💡 {hints[0]}</div>
  <div id="hint1" class="hint-box">💡 {hints[1]}</div>
  <div id="hint2" class="hint-box">💡 {hints[2]}</div>
</div>

<div class="card">
  <h2>答え</h2>
  <button onclick="showAnswer()">答えを見る</button>
  <div id="answer" class="answer-box">
    <strong>{word} → {answer}</strong><br><br>
    <span class="score">編集距離スコア：{score}点</span>
  </div>
</div>

<script>
let currentAnswer = "{answer}";
function generateNew() {{
  const keys = Object.keys(pairsAB);
  const randomword = keys[Math.floor(Math.random() * keys.length)];
  const ans = pairsAB[randomword];
  currentAnswer = ans;
  document.getElementById('main-q').textContent = randomword + ' → ？';
  document.getElementById('auto-result').innerHTML = '';
  document.getElementById('auto-input').value = '';
}}
function checkAuto() {{
  const input = document.getElementById('auto-input').value.trim();
  const div = document.getElementById('auto-result');
  if (!input) {{ div.innerHTML = '<p style="color:red;">答えを入力してください</p>'; return; }}
  if (input === currentAnswer) {{
    div.innerHTML = '<p style="color:#4a7c4e;font-weight:bold;">✅ 正解！</p>';
  }} else {{
    div.innerHTML = '<p style="color:red;font-weight:bold;">❌ 不正解。もう一度考えてみよう</p>';
  }}
}}
function showHint(n) {{
  document.getElementById('hint' + n).classList.add('show');
}}
function showAnswer() {{
  document.getElementById('answer').classList.add('show');
}}
</script>
</body>
</html>"""

    with open('c:/Users/ikeza/source/repos/riddle maker/riddle_v2.html', 'w', encoding='utf-8') as f:
        f.write(html)
    print("riddle_v2.html を生成しました！")

# ===== メイン =====
if __name__ == '__main__':
    print("=== ①辞書構築中... ===")
    nouns, adverbs = build_dictionary()
    dictionary = nouns | adverbs

    print("=== ②規則生成 ===")
    rules = generate_rules()

    print("=== ④探索中... ===")
    pairs = search_pairs(dictionary, rules)
    print(f"生成可能な謎: {len(pairs)}個")

    if not pairs:
        print("謎を生成できませんでした")
    else:
        print("=== ⑤問題生成 ===")
        main_pair, example_pairs = generate_problem(pairs)

        print("=== ⑥ヒント生成（AI）===")
        hints, explanation = generate_hints(main_pair[0], main_pair[1], main_pair[2], example_pairs)
        def generate_html(pairs, dictionary):
            # pairsからランダムに1つ選ぶ（パターン3用）
            main_pair = random.choice(pairs)
            word, answer, rule_name = main_pair
            examples = [p for p in pairs if p[0] != word]
            example_pairs = random.sample(examples, min(2, len(examples)))
            hints, explanation = generate_hints(word, answer, rule_name, example_pairs)
            score = judge(word, answer)

            ex_html = ""
            for ew, ea, _ in example_pairs:
                ex_html += f'<div class="example">{ew} → {ea}</div>\n'

            # pairsを辞書としてJSに渡す
            pairs_a_to_b = {w: a for w, a, _ in pairs}  # 元単語→答え
            pairs_b_to_a = {a: w for w, a, _ in pairs}  # 答え→元単語

            import json
            pairs_ab_json = json.dumps(pairs_a_to_b, ensure_ascii=False)
            pairs_ba_json = json.dumps(pairs_b_to_a, ensure_ascii=False)

            html = f"""<!DOCTYPE html>
        <html lang="ja">
        <head>
        <meta charset="UTF-8">
        <title>謎解き</title>
        <style>
        body {{ font-family: sans-serif; max-width: 620px; margin: 40px auto; padding: 20px; background: #f5f5f5; }}
        .card {{ background: white; border-radius: 12px; padding: 30px; margin: 20px 0; box-shadow: 0 2px 8px rgba(0,0,0,0.1); }}
        h1 {{ color: #4a7c4e; text-align: center; }}
        h2 {{ color: #4a7c4e; }}
        .example {{ font-size: 1.3em; margin: 8px 0; color: #444; }}
        .example.main {{ font-weight: bold; color: #222; }}
        .hint-box {{ background: #e8f5e9; border-radius: 8px; padding: 15px; margin: 10px 0; display: none; }}
        .hint-box.show {{ display: block; }}
        button {{ background: #4a7c4e; color: white; border: none; padding: 10px 24px; border-radius: 8px; cursor: pointer; font-size: 1em; margin: 8px 4px; }}
        button:hover {{ background: #3a6a3e; }}
        .answer-box {{ background: #fff3e0; border-radius: 8px; padding: 20px; margin: 10px 0; display: none; font-size: 1.4em; text-align: center; }}
        .answer-box.show {{ display: block; }}
        .score {{ color: #4a7c4e; font-weight: bold; font-size: 0.9em; }}
        .tab-buttons {{ display: flex; gap: 8px; margin-bottom: 20px; }}
        .tab-btn {{ background: #ccc; color: #333; }}
        .tab-btn.active {{ background: #4a7c4e; color: white; }}
        .tab {{ display: none; }}
        .tab.active {{ display: block; }}
        input[type=text] {{ padding: 10px; font-size: 1.1em; border: 2px solid #4a7c4e; border-radius: 8px; width: 60%; margin-right: 8px; }}
        .error {{ color: red; margin-top: 10px; }}
        .result {{ margin-top: 20px; }}
        </style>
        </head>
        <body>
        <h1>🔤 謎解き</h1>

        <div class="card">
        <div class="tab-buttons">
            <button class="tab-btn active" onclick="switchTab('auto')">自動生成</button>
            <button class="tab-btn" onclick="switchTab('pattern1')">A → ？</button>
            <button class="tab-btn" onclick="switchTab('pattern2')">？ → B</button>
        </div>

        <!-- パターン3：自動生成 -->
        <div id="tab-auto" class="tab active">
            <div id="ex1-display" class="example">{example_pairs[0][0]} → {example_pairs[0][1]}</div>
            <div id="ex2-display" class="example">{example_pairs[1][0]} → {example_pairs[1][1]}</div>
            <div id="main-q" class="example main">{word} → ？</div>
            <br>
            <button onclick="generateNew()">新しい問題を生成</button>
            <br><br>
            <input type="text" id="auto-input" placeholder="答えを入力">
            <button onclick="checkAuto()">回答する</button>
            <div id="auto-result"></div>
            </div>

        <!-- パターン1：答えを入力してAを当てる -->
        <div id="tab-pattern1" class="tab">
            <p>答えの単語（B）を入力すると、元の単語（A）を当てる問題が出ます</p>
            <input type="text" id="input1" placeholder="例：かげ">
            <button onclick="searchPattern1()">生成</button>
            <div id="result1" class="result"></div>
        </div>

        <!-- パターン2：元単語を入力してBを当てる -->
        <div id="tab-pattern2" class="tab">
            <p>元の単語（A）を入力すると、答えの単語（B）を当てる問題が出ます</p>
            <input type="text" id="input2" placeholder="例：おかげ">
            <button onclick="searchPattern2()">生成</button>
            <div id="result2" class="result"></div>
        </div>
        </div>

        <!-- ヒント（自動生成のみ） -->
        <div id="hint-card" class="card">
        <h2>ヒント</h2>
        <button onclick="showHint(0)">ヒント①</button>
        <button onclick="showHint(1)">ヒント②</button>
        <button onclick="showHint(2)">ヒント③</button>
        <div id="hint0" class="hint-box">💡 {hints[0]}</div>
        <div id="hint1" class="hint-box">💡 {hints[1]}</div>
        <div id="hint2" class="hint-box">💡 {hints[2]}</div>
        </div>

        <!-- 答え（自動生成のみ） -->
        <div id="answer-card" class="card">
        <h2>答え</h2>
        <button onclick="showAnswer()">答えを見る</button>
        <div id="answer" class="answer-box">
            <strong>{word} → {answer}</strong><br><br>
            <div style="background:#e8f5e9;border-radius:8px;padding:15px;margin:10px 0;font-size:0.85em;">{explanation}</div>
            <span class="score">編集距離スコア：{score}点</span>
        </div>
        </div>

        <script>
        const pairsAB = {pairs_ab_json};
        const pairsBA = {pairs_ba_json};
        let currentAnswer = "{answer}";
        function generateNew() {{
          const keys = Object.keys(pairsAB);
          const randomWord = keys[Math.floor(Math.random() * keys.length)];
          const ans = pairsAB[randomWord];
          currentAnswer = ans;
          document.getElementById('main-q').textContent = randomWord + ' → ？';
          document.getElementById('auto-result').innerHTML = '';
          document.getElementById('auto-input').value = '';
        }}
        function checkAuto() {{
          const input = document.getElementById('auto-input').value.trim();
          const div = document.getElementById('auto-result');
          if (!input) {{ div.innerHTML = '<p style="color:red;">答えを入力してください</p>'; return; }}
          if (input === currentAnswer) {{
            div.innerHTML = '<p style="color:#4a7c4e;font-weight:bold;">✅ 正解！</p>';
          }} else {{
            div.innerHTML = '<p style="color:red;font-weight:bold;">❌ 不正解。もう一度考えてみよう</p>';
          }}
        }}

        function switchTab(name) {{
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.getElementById('tab-' + name).classList.add('active');
        event.target.classList.add('active');

        // ヒントと答えカードは自動生成のみ表示
        const show = name === 'auto';
        document.getElementById('hint-card').style.display = show ? '' : 'none';
        document.getElementById('answer-card').style.display = show ? '' : 'none';
        }}

        function showHint(n) {{
        document.getElementById('hint' + n).classList.add('show');
        }}

        function showAnswer() {{
        document.getElementById('answer').classList.add('show');
        }}

        function searchPattern1() {{
        const input = document.getElementById('input1').value.trim();
        const div = document.getElementById('result1');
        if (!input) {{ div.innerHTML = '<p class="error">単語を入力してください</p>'; return; }}
        const original = pairsBA[input];
        if (!original) {{
            div.innerHTML = '<p class="error">「' + input + '」は辞書に見つかりませんでした</p>';
        }} else {{
            div.innerHTML = `
            <div class="example">${{original}} → ${{input}}</div>
            <div class="example main">${{original}} → ？</div>
            <p style="color:#4a7c4e; margin-top:10px;">答え：<strong>${{input}}</strong></p>
            `;
        }}
        }}

        function searchPattern2() {{
  const input = document.getElementById('input2').value.trim();
  const div = document.getElementById('result2');
  if (!input) {{ div.innerHTML = '<p class="error">単語を入力してください</p>'; return; }}
  // 先頭削除して答えを作る
  const ans = input.slice(1);
  if (ans.length < 2) {{
    div.innerHTML = '<p class="error">2文字以上の答えになる単語を入力してください</p>';
    return;
  }}
  // 答えが辞書にあるか確認
  if (!Object.values(pairsAB).includes(ans) && !Object.keys(pairsAB).includes(ans)) {{
    div.innerHTML = '<p class="error">「' + ans + '」は辞書に見つかりませんでした</p>';
  }} else {{
    div.innerHTML = `
      <div class="example main">${{input}} → ？</div>
      <p style="color:#4a7c4e; margin-top:10px;">答え：<strong>${{ans}}</strong></p>
    `;
  }}
}}
        </script>
        </body>
        </html>"""

            with open('c:/Users/ikeza/source/repos/riddle maker/riddle_unidic.html', 'w', encoding='utf-8') as f:
                f.write(html)
            print("riddle_unidic.html を生成しました！")
        generate_html(pairs, dictionary)