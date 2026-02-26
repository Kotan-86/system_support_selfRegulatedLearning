# gas/payload — 視聴ログ payload の組み立てとテスト

`gas/lectureVideoPlatform.gs` の `buildViewingLogPayload` と **同一仕様**の純粋関数と、その Jest テストを置いています。

- **buildViewingLogPayload.js** … payload 組み立て（GAS 側と同じロジック）
- **buildViewingLogPayload.test.js** … ユニットテスト

## 実行

```bash
cd gas/payload
npm install   # 初回のみ
npm test      # Jest 実行
```

API との契約は pytest で担保します。

```bash
uv run pytest tests/test_api/test_viewing_log_gas_contract.py -v
```
