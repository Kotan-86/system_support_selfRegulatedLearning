# Cloud Run デプロイ手順書（はじめて作業する人向け）

対象 Issue: [#39 研究者が研究室のCloud Runにデプロイし、協力者が利用を始められるようにする](https://github.com/Kotan-86/system_support_selfRegulatedLearning/issues/39)
要件: NFR-50(研究室アカウントの Cloud Run)、NFR-02(資格情報を環境変数・Secret Manager で渡す)、NFR-06(HTTPS)

このドキュメントは、**インストールが何もされていない Windows の PC** から始めて、研究室(watalab)の Google アカウントの Cloud Run にこのシステムを公開し、協力者が使い始められる状態にするまでの全手順です。コマンドはコピーして貼り付ければ動くように書いてあります。分からない言葉は「[付録A 用語集](#付録a-用語集)」を見てください。

> **Windows と Mac のどちらでも作業できます。**
> - **Windows**: 本文のとおり(PowerShell)に進めてください。
> - **MacBook**: 本文の **2章を読む代わりに [付録C-1](#c-1-mac-のインストール2章の代わり)** で準備し、**3章・4章は本文のとおり**(コマンドは同じ)に進み、**5章以降のコマンドは、各章に書いた案内に従って [付録C](#付録c-mac-版のコマンド) の Mac 版を使ってください**。「PowerShell」とある箇所は「ターミナル」に読み替えます。
> - Mac では、PowerShell 用の `` ` ``(行末の継続記号)が `\` に、変数が `$PROJECT_ID` の書き方に変わります。**PowerShell 用のコマンドを Mac のターミナルに貼ると動きません。**

> **重要な前提(必ず読む)**
> - デプロイするブランチは **`develop`** です。`main` ブランチは初期状態(README のみ)で、システムは入っていません。
> - 「Gemini API の料金が研究室に請求される」仕組みは、**API キーではなく、Google Cloud のプロジェクトに紐づけた「請求先アカウント」で実現します**。このシステムは Google Cloud の Vertex AI 経由で Gemini を呼びます。研究室のプロジェクトに研究室の請求先アカウントを紐づければ、料金は研究室に請求されます(手順 4-4)。
> - **パスワードや API キーを、チャット・メール・Issue・AI(Claude など)に貼らないでください。** 貼ってしまったら、その値は作り直します(「[困ったとき](#12-困ったとき)」)。

---

## 目次

0. [全体像と所要時間](#0-全体像と所要時間)
1. [作業を始める前に決めること・用意するもの](#1-作業を始める前に決めることと用意するもの)
2. [手元の PC の準備(ソフトのインストール)](#2-手元の-pc-の準備ソフトのインストール)
3. [プログラムを手元に取得する](#3-プログラムを手元に取得する)
4. [Google Cloud の認証と初期設定](#4-google-cloud-の認証と初期設定)
5. [作業用の変数を決める](#5-作業用の変数を決める)
6. [秘密情報を Secret Manager に登録する](#6-秘密情報を-secret-manager-に登録する)
7. [実行用サービスアカウントに権限を付ける](#7-実行用サービスアカウントに権限を付ける)
8. [データ保存用の GCS バケットを作る](#8-データ保存用の-gcs-バケットを作る)
9. [デプロイ前の確認(任意だが推奨)](#9-デプロイ前の確認任意だが推奨)
10. [デプロイする](#10-デプロイする)
11. [動作確認(受入の確認)](#11-動作確認受入の確認)
12. [困ったとき](#12-困ったとき)
13. [協力者の ID・パスワードの発行と配布](#13-協力者の-idパスワードの発行と配布)
14. [運用: 再デプロイ・ログ確認・費用](#14-運用再デプロイログ確認費用)
15. [当日(10/26 9:00-10:00)の進行表](#15-当日1026-900-1000の進行表)
- [付録A 用語集](#付録a-用語集) / [付録B 未確認事項](#付録b-この手順書で未確認の事項) / [**付録C Mac 版のコマンド**](#付録c-mac-版のコマンド)

---

## 0. 全体像と所要時間

### 何をするのか

```
あなたの PC                     Google Cloud(研究室のプロジェクト)
-----------                     -----------------------------------
プログラム(develop) --デプロイ-->  Cloud Run (サービス: sssrl-backend)  <--HTTPS-- 協力者のブラウザ
                                    |  |   |
                                    |  |   +--> Vertex AI (Gemini)      料金は研究室の請求先アカウントへ
                                    |  +------> Secret Manager         パスワード等を安全に保管
                                    +---------> GCS バケット           データベース(SQLite)の複製を保存
                                                                         → 再デプロイしてもデータが残る
```

- **Cloud Run**: プログラムを動かし、`https://…run.app` の URL で公開してくれるサービス。HTTPS は自動で付く。
- **Secret Manager**: パスワードや API キーの金庫。プログラムにも Git にも書かない。
- **GCS バケット**: Google のファイル置き場。Cloud Run の中のデータは再デプロイで消えるため、データベースを自動でここへコピーし、起動時に戻す(Litestream という部品が行う)。

### 所要時間の目安

| 作業 | 目安 |
|---|---|
| 2〜3章(インストール、取得) | 30〜40分 |
| 4〜8章(認証、設定、金庫、バケット) | 30〜40分 |
| 10章(デプロイ。初回のビルド) | 10〜20分(**初回は SQLite をソースからビルドするため長い**。見込みで、実測ではない) |
| 11章(動作確認) | 15分 |

**当日 10/26 9:00-10:00 の枠に収めるため、2〜9章は前日までに済ませておくことを強く勧めます。** 当日は 10〜11章だけで済みます(15章)。

---

## 1. 作業を始める前に決めること・用意するもの

### 1-1. 用意するもの

| 項目 | 内容 | 確認 |
|---|---|---|
| PC | Windows 10/11。インターネットに接続でき、ソフトをインストールできること(管理者権限が要ることがある) | ☐ |
| 研究室の Google アカウント | watalab のアカウント。**そのアカウントでブラウザにログインできる**こと | ☐ |
| Google Cloud のプロジェクト | 研究室のアカウントで作成済み、または作成する(4-3)。**プロジェクト ID** を控える | ☐ |
| 請求先アカウント | 研究室のクレジットカード等が登録された Google Cloud の請求先アカウント(4-4) | ☐ |
| 作業者の権限 | そのプロジェクトで **オーナー(Owner)** ロール(ほぼ全作業ができる)。大学・組織の Google Workspace の場合は組織管理者への相談が要ることがある | ☐ |
| YouTube Data API キー | 学習行動ダッシュボード(LAD)の動画の長さの取得に使う(6-3) | ☐ |
| 研究者用 Basic 認証の ID/パスワード | 対話ログをダウンロードする研究者用。研究者で共有する1組。**自分で決める**(6-4) | ☐ |
| 倫理審査の条件(#38) | データの保存期間・収集項目などの条件を確認済みであること | ☐ |

### 1-2. 共有してはいけないもの

次のものは、**研究者以外に渡さない・Git に入れない・チャットに貼らない**ものです。

- 協力者のパスワード(作ったときに1回だけ画面に表示される。一括発行 `bulk-add` は画面に出さず、配布用 CSV に書く)
- `secrets/` フォルダの中身すべて
- Secret Manager に入れる値すべて
- 研究者用 Basic 認証のパスワード

> `secrets/` フォルダは `.gitignore`(Git に入れない)と `.dockerignore`(デプロイするイメージに入れない)で除外済みです。

---

## 2. 手元の PC の準備(ソフトのインストール)

> **Mac の方はこの章を飛ばして [付録C-1](#c-1-mac-のインストール2章の代わり) へ進んでください。**(以降、3・4章は Mac でも同じコマンドです。)

**PowerShell** を使います。スタートメニューで「PowerShell」と入力して開いてください(「Windows PowerShell」でも「PowerShell 7」でも動きます)。以下のコマンドは、すべて PowerShell に貼り付けて実行します。

### 2-1. winget が使えるか確認する

```powershell
winget --version
```

バージョンが表示されれば OK です。「認識されません」と出る場合は、Microsoft Store で「アプリ インストーラー」を更新してください。それも難しければ、各ソフトを公式サイトからインストーラーでインストールしても構いません(下の表に URL の入口を書きました)。

### 2-2. 必要なソフトをインストールする

| ソフト | 何のため | インストールコマンド |
|---|---|---|
| **Git** | プログラムを取得する | `winget install --id Git.Git -e` |
| **uv** | Python とライブラリを自動で用意する | `winget install --id astral-sh.uv -e` |
| **Google Cloud CLI(gcloud)** | Google Cloud を操作する | `winget install --id Google.CloudSDK -e` |
| Docker Desktop(**任意**) | 手元でコンテナの動作確認をする | `winget install --id Docker.DockerDesktop -e` |

- **Python は別にインストールしなくて構いません。** uv が、このシステムに必要な Python を自動で用意します。
- **Docker は必須ではありません。** 本番のビルドは Google の Cloud Build が行います(10章)。手元で確認したい場合だけ入れます。
- インストール後は、**PowerShell をいったん閉じて、開き直してください**(新しいソフトを認識させるため)。

### 2-3. インストールを確認する

開き直した PowerShell で:

```powershell
git --version
uv --version
gcloud --version
```

3つともバージョンが表示されれば OK です。「認識されません」が出たら、PowerShell を開き直す、それでもだめなら PC を再起動してください。

> `gcloud --version` が初回に少し時間がかかることがあります。

---

## 3. プログラムを手元に取得する

### 3-1. 取得する(初回のみ)

作業用のフォルダ(例: `C:\work`)を作って移動し、取得します。

```powershell
New-Item -ItemType Directory -Force C:\work | Out-Null
cd C:\work
git clone https://github.com/Kotan-86/system_support_selfRegulatedLearning.git
cd system_support_selfRegulatedLearning
git checkout develop
git pull
```

- GitHub のログインを求められたら、画面の指示に従ってください(ブラウザが開きます)。
- すでに取得済みなら、`cd` でそのフォルダに入り `git checkout develop` と `git pull` だけ実行します。

**以降のコマンドは、すべてこのフォルダ(`system_support_selfRegulatedLearning`)の中で実行します。** 今どこにいるかは `pwd` で確認できます。

### 3-2. ライブラリをインストールする

```powershell
uv sync
```

`pyproject.toml` に書かれたライブラリ(Flask、gunicorn、google-genai など)と Python が自動でインストールされます。初回は数分かかることがあります。最後にエラーが出なければ OK です。

> デプロイ自体には、この手元のインストールは必要ありません(Google 側で別にビルドします)。ただし、9章の事前確認と、13章の ID 発行(`uv run python scripts/manage_participants.py`)で使います。

### 3-3. 自動テストを動かして、手元の環境が正しいか確認する(任意)

```powershell
uv run pytest tests/ -q
```

外部サービスに接続しないテストだけが動きます(Google の認証は不要)。失敗が出た場合は、デプロイを進める前に研究者(開発担当)に伝えてください。

---

## 4. Google Cloud の認証と初期設定

### 4-1. gcloud にログインする(「人」の認証)

```powershell
gcloud auth login
```

ブラウザが開くので、**研究室(watalab)の Google アカウント**でログインして「許可」を押します。ログインできたか確認:

```powershell
gcloud auth list
```

`ACTIVE` の印が付いたアカウントが、研究室のアカウントであることを確認してください。違うアカウントの場合は `gcloud config set account <研究室のメールアドレス>` で切り替えます。

### 4-2. もう1つの認証: アプリ用のデフォルト認証(ADC)

```powershell
gcloud auth application-default login
```

もう一度ブラウザが開くので、同じアカウントでログインします。

> **なぜ2回ログインするのか**: `gcloud auth login` は「gcloud コマンドが使う認証」、`gcloud auth application-default login` は「手元で動かす Python のプログラム(9章の確認スクリプト、手元でのデータ復元など)が使う認証(ADC)」です。別々に保存されます。**Cloud Run の本番では、これらは使いません**(Cloud Run に付属するサービスアカウントが自動で認証されます)。デプロイ自体は 4-1 だけで足ります。

### 4-3. プロジェクトを決める

**すでに研究室のプロジェクトがある場合**は、その ID を確認して選びます:

```powershell
gcloud projects list
gcloud config set project <プロジェクトID>
```

**新しく作る場合**(プロジェクト ID は世界で一意。小文字・数字・ハイフン。例: `watalab-sssrl`):

```powershell
gcloud projects create watalab-sssrl --name="watalab SSSRL"
gcloud config set project watalab-sssrl
```

> 組織(大学の Google Workspace)の中に作る場合は、`--organization` や `--folder` の指定が必要なことがあります。エラーが出たら組織の管理者に相談してください。

確認:

```powershell
gcloud config get-value project
```

### 4-4. 請求先アカウントを紐づける(**ここが「料金が研究室に請求される」設定**)

1. 請求先アカウントの ID を調べる:

   ```powershell
   gcloud billing accounts list
   ```

   `ACCOUNT_ID`(`XXXXXX-XXXXXX-XXXXXX` の形)のうち、**研究室のもの**を控えます。表示されない場合は、そのアカウントに請求先アカウントへの権限がありません。ブラウザの [お支払い](https://console.cloud.google.com/billing) で、請求先アカウントの管理者に「請求先アカウント管理者(Billing Account Administrator)または請求先アカウント ユーザー」の権限を頼んでください。

2. プロジェクトに紐づける:

   ```powershell
   gcloud billing projects link (gcloud config get-value project) --billing-account=<請求先アカウントID>
   ```

3. 紐づいたか確認する(`billingEnabled: true` になれば OK):

   ```powershell
   gcloud billing projects describe (gcloud config get-value project)
   ```

> コンソールで行う場合: [お支払い](https://console.cloud.google.com/billing) → 対象の請求先アカウント →「アカウント管理」/「プロジェクトをリンク」。

**予算アラート(強く推奨)**: 想定外の高額請求に気づけるよう、[予算とアラート](https://console.cloud.google.com/billing/budgets) で月額の予算(例: 1万円)を作り、50%/90%/100% でメール通知するようにしてください。コマンドでも作れますが、画面のほうが分かりやすいです。

### 4-5. 必要な API を有効にする

```powershell
gcloud services enable `
  run.googleapis.com `
  cloudbuild.googleapis.com `
  artifactregistry.googleapis.com `
  secretmanager.googleapis.com `
  aiplatform.googleapis.com `
  storage.googleapis.com `
  youtube.googleapis.com
```

数分かかることがあります。「Operation finished successfully」と出れば OK です。

| API | 用途 |
|---|---|
| Cloud Run Admin API | プログラムを動かす |
| Cloud Build API | デプロイ時にビルドする |
| Artifact Registry API | ビルドしたイメージを保管する |
| Secret Manager API | 秘密情報の金庫 |
| Vertex AI API(`aiplatform`) | Gemini の呼び出し(**請求の対象**) |
| Cloud Storage API | データベースの複製の保存 |
| YouTube Data API v3 | 動画の長さの取得 |

---

## 5. 作業用の変数を決める

> **Mac の方**: この章のコマンドは [付録C-2](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

これ以降のコマンドで使う値を、変数に入れます。**PowerShell を開き直すたびに、この章をもう一度実行してください**(変数は閉じると消えます)。

```powershell
$PROJECT_ID     = (gcloud config get-value project)
$REGION         = "asia-northeast1"          # 東京。変えない(Cloud Run・GCS・Vertex AI を揃える)
$SERVICE_NAME   = "sssrl-backend"
$REPLICA_BUCKET = "$PROJECT_ID-sssrl-db"     # GCS バケット名(世界で一意。gs:// は付けない)
$PROJECT_NUMBER = (gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
$RUN_SA         = "$PROJECT_NUMBER-compute@developer.gserviceaccount.com"   # Cloud Run の実行サービスアカウント(既定)

"PROJECT_ID=$PROJECT_ID  REGION=$REGION  BUCKET=$REPLICA_BUCKET  RUN_SA=$RUN_SA"
```

表示された内容に間違いがないか確認します(`PROJECT_ID` が空なら 4-3 をやり直し)。

> **リージョンは `asia-northeast1` で固定です。** Cloud Run、GCS バケット、Vertex AI(`VERTEX_LOCATION`)を同じにします。Gemini のモデルが東京で使えることは確認済みです(仕様 db-persistence)。

---

## 6. 秘密情報を Secret Manager に登録する

> **Mac の方**: この章のコマンドは [付録C-3](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

Secret Manager に登録する秘密情報は4種類です。

| シークレット名 | 中身 | 使い道 |
|---|---|---|
| `session-secret-key` | ランダムな文字列 | ログイン状態(Cookie)の署名 |
| `participant-credentials` | 協力者の ID と、パスワードの**ハッシュ** | 協力者のログイン |
| `youtube-api-key` | YouTube Data API キー | 動画の長さの取得 |
| `researcher-basic-user` / `researcher-basic-password` | 研究者用の ID/パスワード | 対話ログのダウンロード |

### 6-0. 入力用の道具(関数)を用意する

秘密の値を、画面に出さず・履歴に残さず・余計な改行や BOM を付けずに登録するための関数です。5章の後、毎回の PowerShell で1回実行してください。

```powershell
New-Item -ItemType Directory -Force secrets | Out-Null

function Add-SecretFromPrompt([string]$Name, [string]$Prompt) {
    $secure = Read-Host $Prompt -AsSecureString
    $plain  = [System.Net.NetworkCredential]::new("", $secure).Password
    if ([string]::IsNullOrWhiteSpace($plain)) { throw "空の値は登録できません" }
    $file = Join-Path $PWD "secrets\$Name.tmp"
    [System.IO.File]::WriteAllText($file, $plain.Trim(), (New-Object System.Text.UTF8Encoding($false)))
    try {
        gcloud secrets describe $Name *> $null
        if ($LASTEXITCODE -eq 0) { gcloud secrets versions add $Name --data-file=$file }
        else                     { gcloud secrets create $Name --data-file=$file }
    } finally { Remove-Item $file -Force }
}
```

> 初回に「Secret Manager API を有効にしますか」と聞かれたら `y` を入力します。

### 6-1. SECRET_KEY(ログインの署名鍵)

自動で作ります。表示も記録もしません。

```powershell
$key = uv run python -c "import secrets; print(secrets.token_hex(32), end='')"
$file = Join-Path $PWD "secrets\session-secret-key.tmp"
[System.IO.File]::WriteAllText($file, $key, (New-Object System.Text.UTF8Encoding($false)))
gcloud secrets create session-secret-key --data-file=$file
Remove-Item $file -Force; Remove-Variable key
```

> **この値を後で変えると、全員が強制ログアウトされます。** 変えない運用にしてください。

### 6-2. 協力者の ID・パスワード(ハッシュ入りの設定ファイル)

詳しい発行の方法は [13章](#13-協力者の-idパスワードの発行と配布) です。**デプロイ前に、最低1人分(動作確認用)を作ってください。**

```powershell
uv run python scripts/manage_participants.py add --note "動作確認用"
```

画面に `ID: P01` と `パスワード: …` が表示されます。**パスワードが表示されるのはこの1回だけです**(ファイルにはハッシュしか残りません。例外として、一括発行 `bulk-add` は端末に出さず、配布用 CSV に書きます)。必ず控えてください。`secrets\participants.json` ができます。

Secret Manager に登録します:

```powershell
gcloud secrets create participant-credentials --data-file=secrets\participants.json
```

### 6-3. YouTube Data API キー

1. ブラウザで [認証情報](https://console.cloud.google.com/apis/credentials) を開き、**プロジェクトが研究室のものであること**を確認する。
2. 「認証情報を作成」→「API キー」。表示されたキーをコピーする。
3. 作成したキーの「キーを制限」→「API の制限」→「キーを制限」→ **YouTube Data API v3** だけにチェックして保存する(漏れても悪用されにくくするため)。
4. 登録する(貼り付けた文字は画面に表示されません):

   ```powershell
   Add-SecretFromPrompt "youtube-api-key" "YouTube APIキーを貼り付けて Enter"
   ```

### 6-4. 研究者用 Basic 認証(対話ログのダウンロード用)

研究者で共有する1組の ID とパスワードを、**自分たちで決めて**登録します(パスワードは長く推測されにくいもの)。**どちらかが未設定だと、ダウンロード機能は常に 401(拒否)になります**(安全側の動作)。

```powershell
Add-SecretFromPrompt "researcher-basic-user"     "研究者用のユーザー名を入力して Enter"
Add-SecretFromPrompt "researcher-basic-password" "研究者用のパスワードを入力して Enter"
```

決めた ID とパスワードは、研究室のパスワード管理の方法(共有パスワードマネージャなど)で保管してください。

### 6-5. 登録を確認する

```powershell
gcloud secrets list
```

次の5つが並んでいれば OK です: `session-secret-key`、`participant-credentials`、`youtube-api-key`、`researcher-basic-user`、`researcher-basic-password`。

---

## 7. 実行用サービスアカウントに権限を付ける

> **Mac の方**: この章のコマンドは [付録C-4](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

**サービスアカウント**は「プログラム用の Google アカウント」です。Cloud Run で動くプログラムは、このアカウントとして Vertex AI・GCS・Secret Manager を使います。**ここで、プログラムに必要な最小限の権限だけを付けます。**(「認証情報の連携」はこの章と 4-4 で完了します。)

5章で `$RUN_SA` を設定済みであることを確認してください(`echo $RUN_SA`)。

### 7-1. Gemini(Vertex AI)を使う権限

```powershell
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member "serviceAccount:$RUN_SA" --role roles/aiplatform.user
```

### 7-2. 各シークレットを読む権限(シークレットごとに付ける。プロジェクト全体には付けない)

```powershell
foreach ($s in "session-secret-key","participant-credentials","youtube-api-key","researcher-basic-user","researcher-basic-password") {
    gcloud secrets add-iam-policy-binding $s `
      --member "serviceAccount:$RUN_SA" --role roles/secretmanager.secretAccessor
}
```

### 7-3. GCS バケットの権限

バケットを作った後に付けます(次の8章のコマンドに含まれています)。

### 7-4. ビルドの権限(デプロイで「ビルド権限」のエラーが出たとき)

最近の Google Cloud では、ソースからのデプロイ時に、ビルドを行うアカウントに権限が足りずエラーになることがあります。**10章でエラーが出たときだけ**、次を実行して再デプロイしてください。

```powershell
gcloud projects add-iam-policy-binding $PROJECT_ID `
  --member "serviceAccount:$RUN_SA" --role roles/cloudbuild.builds.builder
```

(エラーの出方と対処は [12章](#12-困ったとき))

---

## 8. データ保存用の GCS バケットを作る

> **Mac の方**: この章のコマンドは [付録C-5](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

協力者の視聴・小テスト・対話のデータ(SQLite)の複製を置く場所です。**このバケットがあるから、再デプロイしてもデータが残ります。** 次を順に実行します。

```powershell
# 1. 東京にバケットを作る
gcloud storage buckets create "gs://$REPLICA_BUCKET" `
  --project $PROJECT_ID --location asia-northeast1 --uniform-bucket-level-access

# 2. バージョニング(古い版も残す)を有効にする
gcloud storage buckets update "gs://$REPLICA_BUCKET" --versioning

# 3. 古い世代を30日後に削除する設定(BOMなしUTF-8で書くことが必須)
$json = '{"rule": [{"action": {"type": "Delete"}, "condition": {"daysSinceNoncurrentTime": 30}}]}'
[System.IO.File]::WriteAllText("$PWD\lifecycle.json", $json, (New-Object System.Text.UTF8Encoding($false)))
gcloud storage buckets update "gs://$REPLICA_BUCKET" --lifecycle-file=lifecycle.json
Remove-Item lifecycle.json

# 4. 実行サービスアカウントに「このバケットだけ」の権限を付ける
gcloud storage buckets add-iam-policy-binding "gs://$REPLICA_BUCKET" `
  --member "serviceAccount:$RUN_SA" --role roles/storage.objectAdmin

# 5. 設定を確認する
gcloud storage buckets describe "gs://$REPLICA_BUCKET"
```

5 の結果で、次を確認します: ①`location: ASIA-NORTHEAST1` ②`versioning` が有効 ③`lifecycle` の設定がある ④**`retention_policy`(保持ポリシー)がない**(Litestream と干渉するため設定しない)。

> バケット名が既に使われている(`409` エラー)ときは、5章の `$REPLICA_BUCKET` を別の名前(例: 末尾に `-2`)にして、5章からやり直してください。

---

## 9. デプロイ前の確認(任意だが推奨)

> **Mac の方**: この章のコマンドは [付録C-6](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

デプロイ後に原因を探すより、手元で先に確認するほうが早く済みます。

### 9-1. Google Cloud の設定の確認スクリプト

プロジェクトの API・請求・権限と、Gemini の呼び出しを確認します。リポジトリ直下に `.env.local`(ローカル用の設定ファイル)を作ります。

```powershell
@"
VERTEX_PROJECT_ID=$PROJECT_ID
VERTEX_LOCATION=asia-northeast1
"@ | Set-Content -Encoding ascii .env.local
```

(`.env.local` は Git に入りません。)読み込んで実行します:

```powershell
Get-Content .env.local | ForEach-Object { if ($_ -match '^\s*([^#=\s]+)\s*=\s*(.*)$') { Set-Item -Path "Env:$($Matches[1])" -Value $Matches[2].Trim('"') } }
uv run python scripts/verify_gcp_agent_platform.py
```

- 最後の **Generate content probe が OK**(終了コード 0)なら、API の有効化・請求・権限・Gemini の呼び出しは問題ありません。
- 手元では「人」の認証(4-2 の ADC)で動くため、サービスアカウントの権限の項目は `UNKNOWN`/`INFO` になることがあります。probe が OK なら気にしなくて構いません。
- `API ... DISABLED` と出たら 4-5 をやり直す。`billing ... NOT LINKED` なら 4-4 をやり直す。

### 9-2. Docker で手元ビルドする(任意。Docker Desktop が必要)

通常は省略して構いません。やる場合は [README の「ローカルで Docker ビルド確認」](../../README.md) に従ってください。

---

## 10. デプロイする

> **Mac の方**: この章のコマンドは [付録C-7](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

### 10-1. コマンド

5章の変数が設定されていること、リポジトリ直下にいること、`develop` ブランチで最新(`git pull` 済み)であることを確認して実行します。

```powershell
gcloud run deploy $SERVICE_NAME `
  --source . `
  --region $REGION `
  --max-instances=1 `
  --min-instances=1 `
  --no-cpu-throttling `
  --allow-unauthenticated `
  --set-env-vars "VERTEX_PROJECT_ID=$PROJECT_ID,VERTEX_LOCATION=$REGION,DB_REPLICA_BUCKET=$REPLICA_BUCKET,PARTICIPANT_CREDENTIALS_FILE=/secrets/participant-credentials/participants.json" `
  --set-secrets "SECRET_KEY=session-secret-key:latest,YOUTUBE_API_KEY=youtube-api-key:latest,RESEARCHER_BASIC_AUTH_USER=researcher-basic-user:latest,RESEARCHER_BASIC_AUTH_PASSWORD=researcher-basic-password:latest,/secrets/participant-credentials/participants.json=participant-credentials:latest"
```

途中で聞かれること:

- 「Artifact Registry のリポジトリ `cloud-run-source-deploy` を作成しますか」→ **`Y`**(初回のみ)。
- 「API を有効にしますか」→ 4-5 を済ませていれば出ません。出たら `y`。

成功すると、最後に次のように表示されます:

```
Service [sssrl-backend] revision [sssrl-backend-00001-xxx] has been deployed and is serving 100 percent of traffic.
Service URL: https://sssrl-backend-xxxxxxxx-an.a.run.app
```

**この `Service URL` が、協力者に伝える URL です。** 控えておきます。あとでも確認できます:

```powershell
gcloud run services describe $SERVICE_NAME --region $REGION --format="value(status.url)"
```

### 10-2. 各指定の意味(変えないでください)

| 指定 | 理由 |
|---|---|
| `--max-instances=1` | 複数のインスタンスが同じ複製先に書くと、データが壊れる・失われるため |
| `--min-instances=1` `--no-cpu-throttling` | アクセスがなくてもデータの複製を続け、インスタンスが落ちる機会を減らすため |
| `--allow-unauthenticated` | 協力者が Google アカウントなしで URL を開けるようにする(守るのはアプリのログインと Basic 認証) |
| `DB_REPLICA_BUCKET` | 未設定だと**起動に失敗する**(データが保存されない状態で稼働するのを防ぐため) |
| `--set-secrets` | 秘密情報は Secret Manager から渡す。コマンドや Git に値を書かない |
| `SESSION_COOKIE_SECURE_DISABLED` は**設定しない** | 本番は HTTPS。これを設定するとログインの安全性が下がる(ローカル専用) |
| `DB_REPLICA_DISABLED` は**設定しない** | 設定すると、データが再デプロイで消える状態になる(ローカル専用) |
| `GOOGLE_APPLICATION_CREDENTIALS` は**設定しない** | Cloud Run では実行サービスアカウントが自動で使われる。鍵ファイルは不要 |

---

## 11. 動作確認(受入の確認)

> **Mac の方**: この章のコマンドは [付録C-8](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

Issue #39 の受入の観点を、次の順で確認します。`<URL>` は 10-1 の Service URL です。

### 11-1. 起動と HTTPS

```powershell
curl.exe -i "<URL>/login"
```

`HTTP/2 200` が返れば起動しています。URL が `https://` で始まることも確認します(**NFR-06**)。

起動しないときは、ログを見ます([12章](#12-困ったとき))。

### 11-2. ブラウザで通しの確認(**UI の確認は人が行います**)

ブラウザで `<URL>/login` を開き、6-2 で作った動作確認用の ID(`P01`)とパスワードで:

| # | 確認すること | OK |
|---|---|---|
| 1 | ログインできる(ログイン後 `/lecture` 画面が出る) | ☐ |
| 2 | 動画が再生できる。字幕の表示/非表示を切り替えられる | ☐ |
| 3 | 小テストに答えられ、結果が出る | ☐ |
| 4 | AI チューターとの対話(`/reflect` 画面)で、メッセージを送ると **AI から返答が来る**(Gemini の疎通) | ☐ |
| 5 | 学習行動ダッシュボード(LAD)が表示される(YouTube API の確認) | ☐ |
| 6 | ログアウトできる。ログアウト後は、`/lecture` を開くとログイン画面に戻る | ☐ |
| 7 | 間違ったパスワードではログインできない | ☐ |

### 11-3. 研究者用ダウンロード

```powershell
curl.exe -u "<研究者のユーザー名>:<研究者のパスワード>" "<URL>/research/dialog-logs" -o dialog-logs.json
```

11-2 の対話が JSON で取得できれば OK です(`[]` の場合は、対話の保存が済んでいない可能性があります。対話画面の「終了」ボタンを押してから再度試してください)。認証なしでは 401 になることも確認できます。取得した `dialog-logs.json` は研究データなので、保管場所に注意してください。

### 11-4. 再デプロイ後もデータが残ること(**必須の受入**)

1. 11-2 の対話と小テストの記録が、11-3 で取得できる(または LAD に出る)ことを確認する。
2. 同じ 10-1 のコマンドをもう一度実行して再デプロイする(コードは変わらなくて構いません)。
3. 完了後、再び 11-3 を実行して、**再デプロイ前のデータが残っている**ことを確認する。

> 再デプロイの間は、新旧のインスタンスが一時的に並びます。**協力者が使っていない時間帯に行い、直前に 11-3 でバックアップ(ダウンロード)を取る**のが決まりです(14章)。

### 11-5. 確認が済んだら、動作確認用の ID を止める

`P01` は研究者の確認専用の ID です(PO決定 2026-10-28)。本番の通し確認が済んだら、`P01` を止めます(13章 `suspend`)。**ID は最大31個(停止も数える)で、停止した番号は再利用されません。** 協力者に配るのは `P02`〜`P31` の30件までです。

---

## 12. 困ったとき

### 12-1. まずログを見る

```powershell
gcloud run services logs read $SERVICE_NAME --region $REGION --limit 100
```

ブラウザなら [Cloud Run のコンソール](https://console.cloud.google.com/run) → サービス → 「ログ」。

### 12-2. 症状別

| 症状 | 原因 | 対処 |
|---|---|---|
| コマンドが「認識されません」 | PowerShell を開き直していない | 開き直す。それでもだめなら PC を再起動 |
| `gcloud` で「権限がありません」(`PERMISSION_DENIED`)/ 403 | ログインしているアカウントが違う、またはオーナー権限がない | `gcloud auth list` で研究室のアカウントか確認。オーナー権限を持つ人に依頼 |
| `Billing account ... not found` / 請求が無効という趣旨のエラー | 請求先アカウントが紐づいていない | 4-4 |
| デプロイ中に Cloud Build の権限エラー(例: `does not have permission to access ... build`) | ビルドの実行アカウントの権限不足 | 7-4 を実行して、10-1 を再実行 |
| デプロイで「`allUsers` を付けられない」/ `--allow-unauthenticated` が失敗 | 組織のポリシー(ドメイン制限共有)が公開を禁止している | 組織の管理者に、この**プロジェクトだけ**で「ドメイン制限共有」を緩める(`iam.allowedPolicyMemberDomains`)ことを依頼。研究室のアカウントが個人の Google アカウントなら発生しない |
| ログに「複製先の設定がない」 | `DB_REPLICA_BUCKET` が未設定 | 10-1 の `--set-env-vars` を確認して再デプロイ |
| ログに「復元に失敗した」で起動しない | バケットの権限不足、バケット名の誤り | 8章の 4(権限)と `$REPLICA_BUCKET` を確認。**空のデータベースでは起動しない設計**なので、安全。原因を直して再デプロイ |
| ログに `SECRET_KEY` のエラーで起動しない | シークレットが未登録、または権限がない | 6-1、7-2 を確認 |
| ログに参加者の設定ファイルが「読めない」「壊れている」 | `participant-credentials` が未登録/空、マウントの指定ミス | 6-2、10-1 の `PARTICIPANT_CREDENTIALS_FILE` と `--set-secrets` の末尾を確認 |
| 503 や起動タイムアウト | 起動に失敗している | 12-1 のログで原因を確認 |
| ログイン画面は出るが、ログインしても戻される | Cookie が付かない(HTTP で開いている等) | URL が `https://` か確認。`SESSION_COOKIE_SECURE_DISABLED` を本番に設定していないか確認 |
| AI の返答が `502`/エラーになる | Vertex AI の API 無効、請求なし、権限不足、リージョン | 9-1 のスクリプトで確認。4-5(API)、4-4(請求)、7-1(権限)を見直す |
| LAD の動画の長さが出ない | YouTube API キーの未登録/制限の誤り | 6-3 を確認(API の制限に YouTube Data API v3 が含まれているか) |
| 研究者ダウンロードが常に 401 | Basic 認証の2つのシークレットの片方が未登録、ID/パスワードの誤り | 6-4、7-2 を確認 |
| 秘密の値(パスワード等)をうっかり貼って/漏らしてしまった | — | **値を作り直す**。`session-secret-key` を変える(全員がログアウトされる)、協力者パスワードは `reissue`(13章)、Basic 認証は 6-4 で新しいバージョンを登録 → いずれも 14-1 の手順で再デプロイして反映 |

### 12-3. 元に戻す(ロールバック)

新しい版で問題が出たとき、前の版に切り替えます。

```powershell
gcloud run revisions list --service $SERVICE_NAME --region $REGION
gcloud run services update-traffic $SERVICE_NAME --region $REGION --to-revisions=<戻したいリビジョン名>=100
```

> データは GCS の複製から復元されるので、版を戻してもデータは残ります。ただし**スキーマ(DB の構造)を変えた版の後で戻すとき**は、開発担当に相談してください。

---

## 13. 協力者の ID・パスワードの発行と配布

> **Mac の方**: この章のコマンドは [付録C-9](#付録c-mac-版のコマンド) の Mac 版を使ってください(説明文は共通です)。

協力者は `P02`〜`P31`(最大30人)の ID と、研究者が発行したパスワードでログインします(`P01` は研究者の確認専用)。**パスワードは発行時に1回だけ表示**され(一括発行 `bulk-add` は端末に出さず、配布用 CSV に書きます)、ファイルにはハッシュ(元に戻せない形)だけが残ります。

### 13-1. 発行(作成スクリプト)

リポジトリ直下で:

```powershell
# 新規: 次の未使用の ID を払い出す(--note は任意のメモ。個人を特定する情報は書かない)
uv run python scripts/manage_participants.py add --note "メモ"
# パスワードの再発行(忘れたとき):
uv run python scripts/manage_participants.py reissue P05
# 停止(以後ログイン不可。停止した番号は再利用されない。解除はできない):
uv run python scripts/manage_participants.py suspend P05
```

- 表示された「ID」と「パスワード」を、**他の人に見られない形**でその協力者に渡します。画面を共有したままコマンドを実行しないでください。
- 表示後は確認できません。控え忘れたら `reissue` で作り直します。
- 実行のたびに `secrets\participants.json` が更新されます。**このファイルはパスワードの平文を含みませんが、研究者以外に渡さないでください。**

### 13-2. 本番へ反映する(**反映しないと、協力者はログインできません**)

ID を追加・再発行・停止したら、Secret Manager に新しいバージョンを追加し、**再デプロイ**します。

```powershell
gcloud secrets versions add participant-credentials --data-file=secrets\participants.json
```

続けて 10-1 の `gcloud run deploy …` を再実行します(再デプロイの注意は 14-1)。

> 効率的な進め方: 協力者の人数が決まっているなら、**デプロイの前に全員分を `add` で作ってから** 6-2 で登録すると、デプロイ回数が減ります。初日までに追加の人が出たら、その都度 13-2 を行います。

### 13-3. 配布の例(文面のひな形)

> 〇〇さん、研究へのご協力ありがとうございます。次の URL を開いて、ID とパスワードでログインしてください。
> URL: `https://…run.app/login`
> ID: `P07`
> パスワード: `(別の連絡手段で送る)`
> パスワードは他の人に教えないでください。ログインは12時間有効です。

**URL と ID、パスワードは、別々の連絡手段で送る**と安全です。

---

## 14. 運用: 再デプロイ・ログ確認・費用

### 14-1. 計画された再デプロイの手順

(ID の追加、プログラムの修正の反映など)

1. **協力者が使っていない時間帯**に行う(新旧のインスタンスが一時的に並ぶため)。
2. **直前に**、11-3 のコマンドで対話ログをダウンロードして保存する(バックアップ)。
3. `git pull`(`develop`)で最新にして、10-1 のコマンドを実行する。
4. 11-1 と 11-3 で、再デプロイ前のデータが残っていることを確認する。

### 14-2. データのバックアップ・復元

- **自動**: GCS バケットに継続してコピーされ、30日分の世代が残ります。
- **手動**: 11-3 の対話ログのダウンロード(JSON)。
- **手元への復元**: [README「手元への復元手順」](../../README.md)。

### 14-3. 費用について

- **Cloud Run**: `--min-instances=1` のため、アクセスがなくても1台が常に動きます(常時課金)。実験期間中のみで足りるなら、終了後にサービスを止めます(14-4)。
- **Gemini(Vertex AI)**: 使った分だけ。研究室の請求先アカウントへ請求されます。
- **GCS・Secret Manager**: 小さい。
- 実際の金額は [請求のレポート](https://console.cloud.google.com/billing) で確認し、4-4 の予算アラートを設定してください。

### 14-4. 実験終了後

- サービスを止める/削除する: `gcloud run services delete $SERVICE_NAME --region $REGION`
- **GCS バケットのデータ(研究データ)をどうするかは、倫理審査の条件(#38)を見て、研究室が手動で判断します**(削除・保管の仕組みは用意していません)。判断するまでは、バケットを消さないでください。
- 使い終わったシークレット・API キーも整理します。

---

## 15. 当日(10/26 9:00-10:00)の進行表

**前日までに終えておく**(2〜9章):

- [ ] 2章 ソフトのインストール(git / uv / gcloud)
- [ ] 3章 `develop` の取得と `uv sync`
- [ ] 4章 gcloud ログイン(2種類)・プロジェクト・**請求先アカウントの紐づけ**・API の有効化
- [ ] 6章 シークレット5つの登録(協力者の ID は、最低1人分)
- [ ] 7章 権限の付与
- [ ] 8章 GCS バケット
- [ ] 9-1 確認スクリプトで Generate content probe が OK
- [ ] 倫理審査の条件(#38)の確認

**当日**:

| 時刻(目安) | 作業 |
|---|---|
| 9:00 | PowerShell を開く。5章の変数を設定。`gcloud auth list` で研究室のアカウントを確認。`git pull`(develop) |
| 9:05 | 10-1 のデプロイを実行(初回は 10〜20分) |
| 9:25 | 11-1(起動)→ 11-2(通しの確認) |
| 9:40 | 11-3(ダウンロード)→ 11-4(再デプロイしてデータが残ることを確認。時間が足りなければ、**デプロイ前日までの別の日**に、先に練習として行う) |
| 9:55 | URL を控える。13章で、協力者全員分の ID を発行して Secret Manager に反映(13-2。再デプロイが1回要る) |
| 10:00 | 完了。10/27 に協力者へ URL・ID・パスワードを配布 |

> **余裕を持たせる工夫**: 13章で全員分の ID を作ってから 6-2 で登録して初回デプロイすれば、当日の再デプロイは 11-4 の確認の1回で済みます。

---

## 付録A 用語集

| 用語 | 意味 |
|---|---|
| Google Cloud(GCP) | Google のクラウド。Cloud Run や Secret Manager はこの一部 |
| プロジェクト | Google Cloud の作業単位。課金・権限・API の有効化はプロジェクトごと |
| プロジェクト ID | プロジェクトの識別名(世界で一意) |
| 請求先アカウント | 料金の支払い元。プロジェクトに紐づけて使う |
| Cloud Run | プログラムを動かして URL で公開するサービス |
| Cloud Build | プログラムを実行できる形(コンテナイメージ)に組み立てるサービス |
| コンテナ / イメージ | プログラムと必要なソフトを1つにまとめた、動かすための荷姿 |
| Secret Manager | パスワード等の金庫 |
| サービスアカウント | プログラム用の Google アカウント |
| IAM / ロール | 誰に何を許すかの設定 / 許可のひとまとまり(例: `roles/aiplatform.user`) |
| ADC | Application Default Credentials。手元のプログラムが Google に認証するための標準の仕組み |
| Vertex AI | Google Cloud 上で Gemini などを使うサービス(コンソールでは Agent Platform と表示されることがある) |
| GCS(Cloud Storage)/ バケット | ファイルを置く場所 / そのフォルダ相当 |
| Litestream | データベース(SQLite)を GCS に自動でコピーし、起動時に戻す部品 |
| SQLite | このシステムのデータベース(`learning.db`、`tutor.db` の2つ) |
| リビジョン | Cloud Run のデプロイのたびに作られる版 |
| uv | Python の環境とライブラリを管理する道具 |
| PowerShell | Windows のコマンド入力画面(以降の手順で使う) |

## 付録B この手順書で未確認の事項

この手順書は、リポジトリの README・仕様(`develop` ブランチ)をもとに、はじめての人向けに整理したものです。次は、**実機での確認が済んでいない**ので、最初の作業のときに確かめ、結果をこの文書に反映してください。

| # | 内容 |
|---|---|
| 1 | 研究室の Google アカウントでの通し(4〜10章)の実行。特に、組織のポリシー(`--allow-unauthenticated`)と、ビルド権限(7-4)が出るかどうか |
| 2 | 6章の `Add-SecretFromPrompt` 関数、4-4 の `gcloud billing projects link`、9-1 の `.env.local` の作り方は、手順書の作成時に実行していない(README には無い、このドキュメントでの追記) |
| 3 | ファイルマウントの書式(`PATH=SECRET_NAME:VERSION`)とシークレットの大きさの上限(1バージョン 64 KiB)は、README が 2026-10-28 に公式ドキュメントで確認済み(出典: [Cloud Run のシークレット](https://cloud.google.com/run/docs/configuring/services/secrets)、[Secret Manager の割り当て](https://cloud.google.com/secret-manager/quotas))。**未確認なのは、`--set-secrets` でファイルのパス(`/secrets/participant-credentials/participants.json`)を指定する形**。公式ページがファイルマウントの例に使っているのは `--update-secrets` で、`--set-secrets` の例は環境変数の形だけのため。デプロイ時に確かめ、起動に失敗する場合は上記のドキュメントを参照 |
| 4 | 研究者用 Basic 認証のシークレット2つを `--set-secrets` で渡す書式は、README の指定(「パスワードは Secret Manager で渡すことを推奨」)に沿った追記で、通しの実行は未確認 |
| 5 | 初回ビルドの所要時間(10〜20分)は見込み |
| 6 | P01 は研究者の確認専用で、通し確認の後に止める運用(11-5)は PO 決定(2026-10-28) |
| 7 | 実験終了後の GCS データの扱いは、倫理審査の条件(#38)による。仕組みは未整備 |

詳しい根拠・仕様: [README(develop)](../../README.md)、`docs/spec/db-persistence.md`、`docs/spec/participant-login.md`、`docs/spec/framework-drivers-layer.md`(いずれも `develop` ブランチ)。

---

## 付録C Mac 版のコマンド

MacBook(Apple シリコン / Intel どちらも)で作業する人向けです。**説明文は本文と共通で、PowerShell のコマンドだけを Mac 用に置き換えたもの**です。**「ターミナル」アプリ**(Launchpad か Spotlight で「ターミナル」と入力)で実行します。標準のシェルは zsh で、そのまま動きます。

> この付録のコマンドは、Mac での実機確認はしていません(本文の Windows 版の内容を置き換えたもの)。最初の作業のとき、うまく動かない箇所があれば研究者に伝え、この文書を直してください。

### C-1. Mac のインストール(2章の代わり)

**手順1: Homebrew(Mac のソフト管理ツール)を入れる。** すでに入っているか確認します:

```bash
brew --version
```

バージョンが出れば手順2へ。「command not found」なら、[brew.sh](https://brew.sh/) のトップに載っているインストールのコマンドを貼って実行します。途中で Mac のログインパスワードを聞かれ(入力しても画面に出ません)、「Xcode Command Line Tools」のインストールも自動で始まります(数分かかります)。**終了時に画面に表示される「Next steps」のコマンド(`brew` に PATH を通す2行)を、必ず実行してください。** その後、ターミナルを開き直します。

**手順2: 必要なソフトを入れる。**

```bash
brew install git uv
brew install --cask gcloud-cli
```

- `gcloud-cli` が「見つからない」と出る場合は、古い名前の `brew install --cask google-cloud-sdk` を試してください(Homebrew 側の名前が変わったため。どちらが有効かは未確認)。
- Python は別に入れなくて構いません(uv が自動で用意します)。
- Docker Desktop は任意です(本番のビルドは Google の Cloud Build が行います)。入れる場合は `brew install --cask docker`。**Apple シリコンの Mac で手元の `docker build` をする場合は、`docker build --platform linux/amd64 -t sssrl-backend .` のように指定が必要です**(Dockerfile が x86_64 用の部品を取得するため)。`gcloud run deploy --source .` は Google 側でビルドするので、この指定は要りません。

**手順3: 確認する。**

```bash
git --version
uv --version
gcloud --version
```

3つともバージョンが出れば OK です。出ないときは、ターミナルを開き直してください。

**以降、3章(取得: `git clone`…、`uv sync`)と4章(gcloud のログイン、プロジェクト、請求、API の有効化)は、本文のコマンドをそのまま使えます。** ただし 4-4 の次の1行だけ、書き方が違います:

```bash
gcloud billing projects link "$(gcloud config get-value project)" --billing-account=<請求先アカウントID>
gcloud billing projects describe "$(gcloud config get-value project)"
```

4-5 の `gcloud services enable` は、行末の `` ` `` を `\` に変えます:

```bash
gcloud services enable \
  run.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  secretmanager.googleapis.com \
  aiplatform.googleapis.com \
  storage.googleapis.com \
  youtube.googleapis.com
```

### C-2. 作業用の変数(5章の代わり)

**ターミナルを開き直すたびに、もう一度実行してください。**

```bash
PROJECT_ID="$(gcloud config get-value project)"
REGION="asia-northeast1"
SERVICE_NAME="sssrl-backend"
REPLICA_BUCKET="${PROJECT_ID}-sssrl-db"
PROJECT_NUMBER="$(gcloud projects describe "$PROJECT_ID" --format='value(projectNumber)')"
RUN_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

echo "PROJECT_ID=$PROJECT_ID REGION=$REGION BUCKET=$REPLICA_BUCKET RUN_SA=$RUN_SA"
```

### C-3. 秘密情報の登録(6章の代わり)

**入力用の関数**(ターミナルごとに1回実行)。貼り付けた文字は画面に出ません。ファイルも作りません。

```bash
add_secret() {  # 使い方: add_secret シークレット名 "入力の案内"
  local name="$1" prompt="$2" value
  printf '%s: ' "$prompt"; read -rs value; echo
  [ -n "$value" ] || { echo "空の値は登録できません" >&2; return 1; }
  if gcloud secrets describe "$name" >/dev/null 2>&1; then
    printf '%s' "$value" | gcloud secrets versions add "$name" --data-file=-
  else
    printf '%s' "$value" | gcloud secrets create "$name" --data-file=-
  fi
}
```

**6-1 SECRET_KEY**(自動生成。表示も保存もしません):

```bash
uv run python -c "import secrets; print(secrets.token_hex(32), end='')" \
  | gcloud secrets create session-secret-key --data-file=-
```

**6-2 協力者の ID・パスワード**(`uv run` と `gcloud` は本文と同じ。パスの区切りだけ `/`):

```bash
uv run python scripts/manage_participants.py add --note "動作確認用"
gcloud secrets create participant-credentials --data-file=secrets/participants.json
```

**6-3 YouTube API キー / 6-4 研究者用 Basic 認証**:

```bash
add_secret youtube-api-key "YouTube APIキーを貼り付けて Enter"
add_secret researcher-basic-user "研究者用のユーザー名を入力して Enter"
add_secret researcher-basic-password "研究者用のパスワードを入力して Enter"
```

**6-5 確認**: `gcloud secrets list`(本文と同じ)

### C-4. 権限(7章の代わり)

```bash
# 7-1 Gemini(Vertex AI)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:$RUN_SA" --role roles/aiplatform.user

# 7-2 各シークレットを読む権限
for s in session-secret-key participant-credentials youtube-api-key researcher-basic-user researcher-basic-password; do
  gcloud secrets add-iam-policy-binding "$s" \
    --member "serviceAccount:$RUN_SA" --role roles/secretmanager.secretAccessor
done

# 7-4 (10章でビルド権限のエラーが出たときだけ)
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
  --member "serviceAccount:$RUN_SA" --role roles/cloudbuild.builds.builder
```

### C-5. GCS バケット(8章の代わり)

```bash
gcloud storage buckets create "gs://$REPLICA_BUCKET" \
  --project "$PROJECT_ID" --location asia-northeast1 --uniform-bucket-level-access

gcloud storage buckets update "gs://$REPLICA_BUCKET" --versioning

cat > lifecycle.json <<'JSON'
{"rule": [{"action": {"type": "Delete"}, "condition": {"daysSinceNoncurrentTime": 30}}]}
JSON
gcloud storage buckets update "gs://$REPLICA_BUCKET" --lifecycle-file=lifecycle.json
rm lifecycle.json

gcloud storage buckets add-iam-policy-binding "gs://$REPLICA_BUCKET" \
  --member "serviceAccount:$RUN_SA" --role roles/storage.objectAdmin

gcloud storage buckets describe "gs://$REPLICA_BUCKET"
```

確認する点(location が ASIA-NORTHEAST1、versioning 有効、lifecycle あり、**retention policy がない**)は本文 8章と同じです。Mac の `cat` で書いたファイルは BOM が付かないので、BOM の注意は不要です。

### C-6. デプロイ前の確認(9章の代わり)

```bash
cat > .env.local <<ENVEOF
VERTEX_PROJECT_ID=$PROJECT_ID
VERTEX_LOCATION=asia-northeast1
ENVEOF

set -a; source .env.local; set +a
uv run python scripts/verify_gcp_agent_platform.py
```

(`.env.local` は Git に入りません。見方は本文 9-1 と同じです。)

### C-7. デプロイ(10章の代わり)

```bash
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$REGION" \
  --max-instances=1 \
  --min-instances=1 \
  --no-cpu-throttling \
  --allow-unauthenticated \
  --set-env-vars "VERTEX_PROJECT_ID=$PROJECT_ID,VERTEX_LOCATION=$REGION,DB_REPLICA_BUCKET=$REPLICA_BUCKET,PARTICIPANT_CREDENTIALS_FILE=/secrets/participant-credentials/participants.json" \
  --set-secrets "SECRET_KEY=session-secret-key:latest,YOUTUBE_API_KEY=youtube-api-key:latest,RESEARCHER_BASIC_AUTH_USER=researcher-basic-user:latest,RESEARCHER_BASIC_AUTH_PASSWORD=researcher-basic-password:latest,/secrets/participant-credentials/participants.json=participant-credentials:latest"
```

URL の再確認:

```bash
gcloud run services describe "$SERVICE_NAME" --region "$REGION" --format='value(status.url)'
```

各指定の意味、聞かれる質問(`Y`)は本文 10章と同じです。

### C-8. 動作確認(11章の代わり)

`curl.exe` は Mac では `curl` です。

```bash
curl -i "<URL>/login"
curl -u "<研究者のユーザー名>:<研究者のパスワード>" "<URL>/research/dialog-logs" -o dialog-logs.json
```

ブラウザでの確認(11-2)と、再デプロイ後のデータの確認(11-4: C-7 のコマンドを再実行)は本文と同じです。

### C-9. 協力者の ID の発行・反映(13章の代わり)

```bash
uv run python scripts/manage_participants.py add --note "メモ"
uv run python scripts/manage_participants.py reissue P05
uv run python scripts/manage_participants.py suspend P05

# 本番へ反映(その後 C-7 で再デプロイ)
gcloud secrets versions add participant-credentials --data-file=secrets/participants.json
```

### C-10. ログ・ロールバック(12章・14章)

```bash
gcloud run services logs read "$SERVICE_NAME" --region "$REGION" --limit 100
gcloud run revisions list --service "$SERVICE_NAME" --region "$REGION"
gcloud run services update-traffic "$SERVICE_NAME" --region "$REGION" --to-revisions=<戻したいリビジョン名>=100
```

### C-11. Mac で困ったとき

| 症状 | 対処 |
|---|---|
| `command not found: brew` / `gcloud` / `uv` | ターミナルを開き直す。それでもだめなら、Homebrew の「Next steps」(PATH を通す2行)を実行したか確認 |
| コマンドが途中で切れる、`command not found` が連続する | 行末の `\` の後ろに空白を入れていないか確認(`\` は行の最後の文字にする) |
| `permission denied`(スクリプトなど) | `uv run python scripts/…` のように `python` を付けて実行する |
| 変数が空(`gs://-sssrl-db` のようになる) | ターミナルを開き直した後に C-2 を実行していない。C-2 をもう一度実行 |
| 上記以外 | 本文 [12章](#12-困ったとき) の症状別の表は、Mac でも共通 |
