# ローカル秘密情報の配置

GCP サービスアカウント JSON や API キーなど、**リポジトリにコミットしてはいけないファイル**をこのディレクトリに置きます。

仕様: [docs/spec/framework-drivers-layer.md](../docs/spec/framework-drivers-layer.md#ローカル秘密情報what)

## 配置手順

1. GCP コンソールからサービスアカウント JSON をダウンロードする（ユーザー操作）
2. プロジェクト内に配置する（ファイル名は固定推奨）:

```bash
mkdir -p secrets
cp /path/to/downloaded-key.json secrets/gcp-service-account.json
chmod 600 secrets/gcp-service-account.json
```

3. リポジトリ直下の `.env.local`（gitignore 済み）に**パスのみ**記載する:

```bash
GOOGLE_APPLICATION_CREDENTIALS=secrets/gcp-service-account.json
VERTEX_PROJECT_ID=your-project-id
VERTEX_LOCATION=us-east4
YOUTUBE_API_KEY=your-youtube-api-key
```

4. 誤コミット防止の確認:

```bash
git check-ignore -v secrets/gcp-service-account.json   # .gitignore にヒットすること
git status -- secrets/                                 # untracked にも出ない（ignore 済み）
```

## ファイル名の例

| 用途 | 推奨ファイル名 |
|------|----------------|
| GCP サービスアカウント | `gcp-service-account.json` |
| YouTube Data API キー（テキスト分離する場合） | `youtube-api-key.txt` |

## 注意

- このディレクトリ配下のファイルは **Git / Docker イメージ / CI アーティファクトに含めない**
- アプリは **環境変数でパスのみ**参照する（JSON 内容をコード・仕様に書かない）
- Cursor で `@secrets/...` を手動添付すると AI コンテキストに載るため、添付しない
- 過去に JSON をコミットした履歴がある場合は、キーをローテーションし履歴除去を検討する
