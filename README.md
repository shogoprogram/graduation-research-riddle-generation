# Graduation Research Riddle Generation

## AIを使う場合

GeminiのAPIキーを環境変数に設定してから、プロジェクトフォルダで次を実行します。

```powershell
$env:GEMINI_API_KEY = "あなたのAPIキー"
py app.py
```

その後 `http://localhost:8000` をブラウザで開き、画面の「AIで問題を作る」を押します。APIキーはHTMLやGitHubには保存しません。単語探索・規則適用・問題生成・ヒント生成・判定を `app.py` だけで行います。
