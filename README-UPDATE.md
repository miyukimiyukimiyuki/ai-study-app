更新版のアップロード方法
1. このフォルダ内の app.js, sw.js, generate_questions.py, daily-questions.json（後で自動生成）, .github/workflows/daily-questions.yml を GitHub リポジトリ直下の対応する場所へアップロードします。
2. GitHub Actions の workflow を手動実行してテストします。
3. APIキーは GitHub Secrets の GEMINI_API_KEY に設定してください。コードに直接書かないでください。
4. 無料枠やモデル提供条件が変わった場合、GitHub Actions が失敗する可能性があります。失敗時に有料へ自動移行する処理はありません。
5. Androidで学習アプリを再起動・更新すると新しい問題が表示されます。日付ごとの問題の過去分はGitHub履歴には残りますが、アプリの復習対象は現在の問題セットに限定されます。
