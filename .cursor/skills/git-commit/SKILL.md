---
name: git-commit
description: Creates git commits only when explicitly requested, with conventional message format and safety checks. Use when the user asks to commit, create a commit, or stage and commit changes.
disable-model-invocation: true
---

# Git コミット

ユーザーがコミット作成を明示的に依頼したときのみ適用する。依頼が無い限りコミットしない。

## コミット前

1. git status / git diff で変更内容を確認する
2. 秘密情報（.env, 認証情報など）が含まれていないか確認する

## メッセージ形式

<タイプ>: <簡潔な説明（What）>

<任意: 変更理由（Why）を1〜2文>
**タイプ:** `feat` / `fix` / `docs` / `refactor` / `test` / `chore`

**例:**
docs: ユーザー認証の受入基準を追加した。

- ログイン失敗時の挙動が未定義だったため、仕様を明文化した。

Issue 参照: 本文末尾に `Fixes #123` または `Refs #123`

## 安全

- git config を変更しない
- フックをスキップしない（ユーザー明示時を除く）
- force push 等の破壊的操作はユーザー明示がない限り行わない

## 作業手順

```
Task Progress:
- [ ] git status で未追跡・変更ファイルを確認
- [ ] git diff でステージ済み・未ステージの差分を確認
- [ ] 秘密情報が含まれていないか確認
- [ ] メッセージを起草（What 重視、必要なら Why）
- [ ] 関連ファイルのみ git add
- [ ] HEREDOC で git commit
- [ ] git status でコミット成功を確認
```

## コミット実行

メッセージは HEREDOC で渡す:

```bash
git commit -m "$(cat <<'EOF'
<タイプ>: <簡潔な説明>

- <変更理由（任意）>

Refs #123
EOF
)"
```

## 追加ルール

- `git commit --amend` はユーザー明示時のみ。HEAD が未 push かつ直前コミットが自分の作業である場合に限る
- フック失敗時は amend せず、修正して新規コミットする
- push はユーザー明示時のみ
- `secrets/`、`.env.local`、`*credentials*.json` はコミットしない
