---
name: create-pull-request
description: Creates GitHub pull requests with structured descriptions for small teams, only when explicitly requested. Use when the user asks to create a PR, push and open a pull request, or generate a PR description.
disable-model-invocation: true
---

# Pull Request（小規模チーム）

ユーザーが PR 作成・PR 説明文生成を依頼したときのみ適用する。

## 前提

- 承認: 1 名で OK
- 品質確認: GitHub の PR レビュー・ブランチ保護に委ねる

## PR 作成前

1. git status / git diff / git log でブランチ状態を確認する
2. 仕様変更を含む場合、関連仕様も更新済みか確認する

## 説明文テンプレート

```markdown
## 変更内容

<!-- 何を変更したか（1〜2文） -->

## 変更の理由

<!-- なぜ変更が必要か（Why） -->

## 関連Issue

Closes #<!-- 番号 -->

## 関連する仕様

<!-- docs/spec/xxx.md または README.md へのリンク -->

## チェックリスト

- [ ] テストが通る
- [ ] 仕様を更新した（必要な場合）
- [ ] 動作確認した
```

## 手順

必要なら git push -u origin HEAD
gh pr create で PR 作成（body は HEREDOC で渡す）
PR URL をユーザーに返す

## 注意

ユーザー明示がない限り push しない
git config を変更しない

---

## GitHub テンプレ（任意・推奨）

各リポジトリの `.github/PULL_REQUEST_TEMPLATE.md` に置くと、Rule 6 と UI 上も揃います。

```markdown
## 変更内容

<!-- 何を変更したか（1〜2文） -->

## 変更の理由

<!-- なぜ変更が必要か（Why） -->

## 関連Issue

Closes #

## 関連する仕様

<!-- docs/spec/xxx.md または README.md へのリンク -->

## チェックリスト

- [ ] テストが通る
- [ ] 仕様を更新した（必要な場合）
- [ ] 動作確認した
```

## 作業手順

```
Task Progress:
- [ ] git status / git diff / git log でブランチ状態を確認
- [ ] 仕様変更があれば docs/spec/ または README.md が更新済みか確認
- [ ] 説明文を起草（変更内容・理由・Issue・仕様リンク）
- [ ] 必要なら git push -u origin HEAD（ユーザー明示時のみ）
- [ ] gh pr create（body は HEREDOC）
- [ ] PR URL をユーザーに返す
```

## PR 作成コマンド

```bash
gh pr create --title "<タイトル>" --body "$(cat <<'EOF'
## 変更内容

<1〜2文>

## 変更の理由

<Why>

## 関連Issue

Closes #123

## 関連する仕様

- docs/spec/xxx.md

## チェックリスト

- [ ] テストが通る
- [ ] 仕様を更新した（必要な場合）
- [ ] 動作確認した
EOF
)"
```

## 関連スキル

- コミット作成: [git-commit](../git-commit/SKILL.md)
- 仕様の作成・更新: [spec-writing](../spec-writing/SKILL.md)
