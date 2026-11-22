
import json
import os
import datetime
import urllib.request
import urllib.error
import pathlib
import sys
import time

ROOT = pathlib.Path(__file__).resolve().parent
KEY = os.environ.get("GEMINI_API_KEY")

if not KEY:
    sys.exit("GEMINI_API_KEY が設定されていません")

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
TODAY = (
    datetime.datetime.now(datetime.timezone.utc)
    + datetime.timedelta(hours=9)
).date().isoformat()

TARGET = ROOT / "daily-questions.json"
MAX_ATTEMPTS = 3
REQUIRED_COUNT = 20

if TARGET.exists():
    try:
        existing = json.loads(TARGET.read_text(encoding="utf-8"))
        if existing.get("date") == TODAY:
            print("本日分は生成済みです")
            sys.exit(0)
    except (ValueError, OSError, AttributeError):
        pass

TOPICS = [
    "基礎理論",
    "LLM",
    "プロンプト",
    "RAG",
    "著作権",
    "個人情報",
    "プロンプトインジェクション",
    "業務導入",
    "エージェント",
    "評価",
]


def validate_question(q):
    if not isinstance(q, dict):
        return False

    for field in ("q", "e", "topic"):
        if not isinstance(q.get(field), str):
            return False
        if not q[field].strip():
            return False

    answers = q.get("a")
    if not isinstance(answers, list) or len(answers) != 4:
        return False

    if not all(
        isinstance(a, str) and a.strip()
        for a in answers
    ):
        return False

    correct = q.get("c")
    if type(correct) is not int:
        return False

    if not 0 <= correct <= 3:
        return False

    return True


def create_prompt(count, existing_questions):
    used = [
        q["q"] for q in existing_questions
    ]

    return f"""
日本の「生成AIアドバイザー1級」学習用の
オリジナル4択問題を日本語で作成してください。

日付: {TODAY}
必要な問題数: {count}問

対象分野:
{", ".join(TOPICS)}

全体で10分野をできるだけバランス良く含める。
実在する公式過去問だと主張しない。
未確認の試験制度情報や時事的な断定は避ける。

各問題の条件:
- 問題文は空欄にしない
- 選択肢は必ず4つ
- 正解は必ず0、1、2、3の整数
- 正解は一意に定める
- 解説には正解の根拠を簡潔に記載
- topicは文字列
- HTMLを含めない
- 既存問題と重複させない

既存問題:
{json.dumps(used, ensure_ascii=False)}

JSONオブジェクトのみ出力してください。

出力形式:
{{
  "questions": [
    {{
      "q": "問題文",
      "a": [
        "選択肢1",
        "選択肢2",
        "選択肢3",
        "選択肢4"
      ],
      "c": 0,
      "e": "正解の解説",
      "topic": "基礎理論"
    }}
  ]
}}

必ず{count}問生成してください。
"""


def request_gemini(prompt):
    url = (
        "https://generativelanguage.googleapis.com/"
        f"v1beta/models/{MODEL}:generateContent"
    )

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.65,
        },
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": KEY,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=100) as res:
            response = json.load(res)

    except urllib.error.HTTPError as exc:
        print(
            "Gemini APIエラー:",
            exc.code,
            exc.read().decode("utf-8", errors="replace")[:500],
        )
        return None

    except (urllib.error.URLError, TimeoutError) as exc:
        print("通信エラー:", str(exc))
        return None

    try:
        text = response["candidates"][0]["content"]["parts"][0]["text"]
        data = json.loads(text)

        if isinstance(data, dict):
            return data.get("questions", [])

        if isinstance(data, list):
            return data

        return []

    except (
        KeyError,
        IndexError,
        TypeError,
        ValueError,
    ) as exc:
        print("JSON解析エラー:", str(exc))
        return []


questions = []
seen = set()

for attempt in range(1, MAX_ATTEMPTS + 1):
    remaining = REQUIRED_COUNT - len(questions)

    if remaining <= 0:
        break

    print(
        f"生成試行 {attempt}/{MAX_ATTEMPTS}: "
        f"残り{remaining}問"
    )

    prompt = create_prompt(remaining, questions)
    generated = request_gemini(prompt)

    if generated is None:
        print("APIへのリクエストに失敗しました")

    elif not isinstance(generated, list):
        print("問題データがリスト形式ではありません")

    else:
        valid_count = 0

        for q in generated:
            if len(questions) >= REQUIRED_COUNT:
                break

            if not validate_question(q):
                print("形式不正の問題を除外しました")
                continue

            question_text = q["q"].strip()

            if question_text in seen:
                print("重複問題を除外しました")
                continue

            seen.add(question_text)
            questions.append(q)
            valid_count += 1

        print(
            f"今回採用: {valid_count}問 / "
            f"累計: {len(questions)}問"
        )

    if len(questions) < REQUIRED_COUNT and attempt < MAX_ATTEMPTS:
        time.sleep(3)

if len(questions) != REQUIRED_COUNT:
    print(
        f"生成失敗: {len(questions)}/{REQUIRED_COUNT}問"
    )
    print("既存の問題ファイルは変更しません")
    sys.exit(1)

output = {
    "date": TODAY,
    "questions": questions,
}

temporary = TARGET.with_suffix(".json.tmp")

try:
    temporary.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(TARGET)

except OSError as exc:
    print("ファイル保存エラー:", str(exc))
    sys.exit(1)

print("生成完了:", TODAY, len(questions))
