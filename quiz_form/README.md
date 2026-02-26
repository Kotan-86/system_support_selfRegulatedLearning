# quiz_form — 小テスト（Google Form）→ 自 app API

Form 送信時に、回答を自 app の `POST /api/quiz-attempts` に JSON で送る GAS 用コードです。

## コピペ手順

1. **Form を GAS と紐付ける**  
   Form の「回答」タブ → 「回答と連携」→「スクリプトエディタに移動」などで、Form 用の GAS プロジェクトを開く。

2. **スクリプトプロパティ**  
   編集 → プロジェクトのプロパティ → スクリプトプロパティで `API_BASE_URL` を追加（自 app のルート URL。末尾スラッシュなし）。

3. **.gs を貼る**  
   `quizForm.gs` の内容を、コード.gs または新規 .gs に貼り付ける。

4. **トリガーを設定**  
   トリガー → トリガーを追加 → 実行する関数: `onFormSubmit`、イベント: 「フォーム送信時」、保存。

5. **Form の前提**  
   - Form を「クイズ」にする。  
   - 1 番目の項目: 「idを入力してください」（短文）。  
   - 2〜6 番目: 問 1〜5（いずれも 4 択のラジオなど、採点可能な項目）。

## payload テスト

```bash
cd quiz_form/payload && npm install && npm test
```

API 契約は pytest で担保します。

```bash
uv run pytest tests/test_api/test_quiz_attempts_gas_contract.py -v
```
