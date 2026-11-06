import json, os, datetime, urllib.request, urllib.error, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
KEY = os.environ.get('GEMINI_API_KEY')
if not KEY:
    sys.exit('GEMINI_API_KEY が設定されていません')
MODEL = os.environ.get('GEMINI_MODEL', 'gemini-2.5-flash-lite')
TODAY = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=9)).date().isoformat()
TARGET = ROOT / 'daily-questions.json'
if TARGET.exists():
    try:
        if json.loads(TARGET.read_text(encoding='utf-8')).get('date') == TODAY:
            print('本日分は生成済みです')
            sys.exit(0)
    except (ValueError, OSError):
        pass

prompt = f'''日本の「生成AIアドバイザー1級」学習用のオリジナル4択問題を、日本語でちょうど20問作成してください。日付: {TODAY}。
基礎理論、LLM、プロンプト、RAG、著作権、個人情報、プロンプトインジェクション、業務導入、エージェント、評価の10分野をバランス良く含める。
実在する公式過去問だと主張しない。時事的な断定や未確認の試験制度情報は避ける。
各問題は一意の正解を持ち、選択肢は4つ、正解は0～3の整数、解説は根拠を簡潔に記載する。
問題文・選択肢・解説にHTMLを入れない。
JSONオブジェクトのみ出力。構造: {{"questions":[{{"q":"問題","a":["選択肢1","選択肢2","選択肢3","選択肢4"],"c":0,"e":"解説","topic":"基礎"}}]}}。'''
url = f'https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent'
payload = {'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'responseMimeType': 'application/json', 'temperature': 0.65}}
req = urllib.request.Request(url, data=json.dumps(payload).encode(), headers={'Content-Type':'application/json','x-goog-api-key':KEY}, method='POST')
try:
    with urllib.request.urlopen(req, timeout=100) as res:
        response = json.load(res)
except urllib.error.HTTPError as exc:
    print('Gemini APIエラー（課金は行いません）:', exc.code, exc.read().decode()[:500])
    sys.exit(1)
text = response['candidates'][0]['content']['parts'][0]['text']
items = json.loads(text)['questions']
if len(items) != 20:
    sys.exit(f'問題数が20問ではありません: {len(items)}')
for i, q in enumerate(items):
    if not (isinstance(q, dict) and all(isinstance(q.get(k),str) and q[k].strip() for k in ('q','e','topic')) and isinstance(q.get('a'),list) and len(q['a']) == 4 and all(isinstance(a,str) and a.strip() for a in q['a']) and type(q.get('c')) is int and 0 <= q['c'] <= 3):
        sys.exit(f'問題形式が不正です: {i+1}')
# 形式検証であり、AIが生成した正答の事実確認を保証するものではありません。
TARGET.write_text(json.dumps({'date':TODAY,'questions':items}, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print('生成完了:', TODAY, len(items))
