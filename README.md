# Graduation Research Riddle Generation

## AIを使う場合

GeminiのAPIキーを環境変数に設定してから、プロジェクトフォルダで次を実行します。

```powershell
$env:GEMINI_API_KEY = "あなたのAPIキー"
python ai_server.py
```

その後 `http://localhost:8000` をブラウザで開き、画面の「AIで問題を作る」を押します。APIキーはHTMLやGitHubには保存しません。キーがない場合は、登録済みの規則による自動生成を使えます。
