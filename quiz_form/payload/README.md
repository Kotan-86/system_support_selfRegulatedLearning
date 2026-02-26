# quiz_form/payload — 小テスト payload の組み立てとテスト

`quiz_form/quizForm.gs` の onFormSubmit が送る payload と **同一仕様**の組み立て関数と Jest テスト。

## 実行

```bash
cd quiz_form/payload
npm install   # 初回のみ
npm test      # Jest 実行
```

API 契約は pytest で担保します。

```bash
uv run pytest tests/test_api/test_quiz_attempts_gas_contract.py -v
```
