# HTTPS の強制 — 本番で http の要求を受け付けず、ログイン情報とデータを平文で流さない

## Issue

#32(関連要件: NFR-06。関連: FR-51、FR-52、FR-53、NFR-05、NFR-08。元の受入3観点は #30 で実装・承認済み: [participant-login.md](./participant-login.md) の AC7〜16)

## 目的(Why)

#30 で、未ログインの要求の拒否(FR-51)と、他人の ID を指定した要求の拒否(FR-52)は入った。しかし、要求が平文の http で届くと、その途中で、参加者のパスワード(ログインの送信)、セッション Cookie、研究者の Basic 認証の資格情報、学習ログ・対話ログが読まれうる。Cookie には `Secure` が付くが、ログインの送信そのもの(ID/パスワード)と、Basic 認証のヘッダは、http で送られれば守られない。

本番(Cloud Run)では、http の要求をアプリが処理しないようにし、利用者を https に導く。これで、URL を `http://` で開いた・打ち間違えたときにも、ログイン情報とデータが平文で返らない・受け付けられないようにする。

## 前提

### 実装の現状(コードの観測事実)

- アプリは、要求の方式(http / https)を確かめていない。http の要求を拒否・転送する処理はない。`framework_drivers/platform/` に `ProxyFix` の利用、`X-Forwarded-Proto` の参照、`Strict-Transport-Security` の付与はない。〔確認: 読み取りのみ(`main.py`、`participant_auth.py`、`research_auth.py`、リポジトリ全体の `.py`・`.sh`・`.toml`・`.yml` の検索)〕
- 要求の前処理の順序は、研究者の Basic 認証 → 参加者のログインの確認 → DB の接続(`create_app` の `before_request` の登録順)。〔確認: 読み取りのみ(`main.py`)(未確認: コードを読んだ推測)〕
- セッション Cookie は既定で `Secure` が付き、`SESSION_COOKIE_SECURE_DISABLED=1` のときだけ外れる(#30 AC21)。〔確認: 読み取りのみ(`participant_auth.py`)。#30 のテストで検証済み〕
- 本番は gunicorn 26.0.0 が `framework_drivers.platform.main:app` を配信する(`deploy/entrypoint.sh`)。gunicorn の既定では、`X-Forwarded-Proto: https` を要求の方式として採用するのは、接続元が `127.0.0.1` または `::1` のときだけ(`forwarded_allow_ips` の既定。環境変数 `FORWARDED_ALLOW_IPS` で変えられる)。起動の手順は、この設定を変えていない。〔確認: 読み取りのみ(`.venv` の gunicorn の `config.py`、`http/message.py`、`deploy/entrypoint.sh`)(未確認: コードを読んだ推測。gunicorn は Windows で `grp` がなく読み込めず、実行できなかった)〕
- Flask 3.1.3 / Werkzeug 3.1.6 で、何もしなければ、要求の方式は WSGI の方式だけで決まり、`X-Forwarded-Proto: https` を付けても `http` のまま。Werkzeug の `ProxyFix(x_proto=1)` を挟むと、`X-Forwarded-Proto` の値で方式が決まる(`https` → https、`http` → http、ヘッダなし → http、`http, https` のように複数のときは最後の値 → https)。テストクライアントは、既定で http、`base_url="https://..."` で https になる。〔確認: 実行(一時の Python で Flask アプリを作り、テストクライアントで表示)〕
- 既存のテストは、テストクライアントの既定(http)で要求を送る。`tests/conftest.py`・`tests/login_helpers.py` が、モジュールの読み込み前と各テストで、`SECRET_KEY`、`PARTICIPANT_CREDENTIALS_FILE`、`SESSION_COOKIE_SECURE_DISABLED=1` を環境に与えている。〔確認: 読み取りのみ〕
- ローカルの開発(`scripts/run_dev_server.sh`)は `http://127.0.0.1:5001` で起動し、`SESSION_COOKIE_SECURE_DISABLED` を既定で `1` にする。README のローカルの `docker run` も http(`-p 8080:8080`)で確認する手順。〔確認: 読み取りのみ〕
- README のデプロイは `--allow-unauthenticated` で、研究者の `/research/` を守るのは Basic 認証だけ、と書いている。疎通確認の例は `https://<service-url>/login`。HTTP の起動確認用の probe(ヘルスチェック)の設定は、README・Dockerfile・`deploy/` にない。〔確認: 読み取りのみ〕
- docs/requirements.md の NFR-06 は「本番では HTTPS を前提とする(Cloud Run は標準で HTTPS)」で、根拠は README。〔確認: 読み取りのみ〕

### Cloud Run の挙動(未確認: 公式ドキュメントを参照していない。ネットワークに接続していない)

- Cloud Run は https を終端し、コンテナには http で届ける。元の方式は `X-Forwarded-Proto` で渡す。(未確認)
- Cloud Run の既定の URL(`*.run.app`)で、`http://` の要求を Cloud Run 自身が https へ転送するか、そのままコンテナへ届けるか。(未確認。転送するなら、アプリ側の強制は多重の防御になる。届けるなら、アプリ側の強制が唯一の防御になる)
- コンテナから見た接続元のアドレスが `127.0.0.1` になるか。(未確認。ならないなら、gunicorn の既定のままでは、本番のすべての要求が http と判定される。下の「制約」の D1)
- Cloud Run の前段が、利用者の送った `X-Forwarded-Proto` を上書きするか、後ろに追記するか。(未確認)

### POの意図(確認済み)

- #32 の元の受入3観点(未ログインの拒否、他人の ID 指定の拒否、Basic 認証との関係)は、#30 で実装・承認済み。#32 で追加するのは「HTTPS の強制」だけ(本番で http の要求を https に限定し、ログイン情報・データが平文で流れないようにする)。〔出典: PO の決定(main 経由の依頼、2026-10-26)〕
- 試行回数の制限、セッション固定の対策、Basic 認証の強化は範囲外。〔出典: 同上〕
- 研究者用の Basic 認証は現状維持で、参加者のログインとは別系統(FR-53)。〔出典: docs/requirements.md、PO決定 2026-10-26〕

## 実現内容(What)

### 1. 本番の既定: http の要求を処理しない

- アプリは、要求が元は http で届いたか https で届いたかを、Cloud Run の前段が付ける `X-Forwarded-Proto` で判定する。
- 元の方式が https でない要求(`X-Forwarded-Proto` が `http`、またはヘッダがない)は、どのパスでも、アプリの処理(認証の照合、DB の読み書き、AI の呼び出し、画面の生成)の前に、次のとおり扱う(値は論点1で決まる)。
  - `GET`・`HEAD`: 同じホスト・パス・クエリの `https://` の URL へ、恒久的なリダイレクト(301)で移す。応答の本文に、学習データ・対話データ・画面を含めない。
  - それ以外(`POST` など): 処理せず、HTTP 400 で拒否する。DB に書き込まず、AI を呼ばず、ログインを成立させず、セッション Cookie を発行しない。
- 対象は、ログイン画面とログインの送信、参加者の画面と API、画面の静的ファイル、研究者向けの `/research/` 配下を含む、すべてのパス(論点2)。`/research/` 配下では、http の判定を Basic 認証の照合より前に行う(http の要求には、資格情報が正しくてもデータを返さない)。
- 元の方式が https の要求は、従来どおり処理する(#30 の挙動を変えない)。

### 2. https の応答に HSTS を付ける(論点3)

- 元の方式が https の要求への応答に、`Strict-Transport-Security: max-age=31536000` を付ける(`includeSubDomains`、`preload` は付けない)。ブラウザは、以後このサイトを http で開こうとしても、送る前に https に切り替える。
- http の要求への応答(リダイレクト・拒否)には付けない。

### 3. ローカルの開発とテストでの解除

- 環境変数の指定(名前は論点4。推奨: `HTTPS_ENFORCEMENT_DISABLED=1`)があるときだけ、1節と2節を行わず、http の要求を従来どおり処理する。値が `1` 以外、または未設定なら、強制する(本番の既定)。
- ローカルの開発の起動手順(`scripts/run_dev_server.sh`)は、この指定を既定で与える(Cookie の `Secure` を外す指定と同じ扱い)。README のローカルの `docker run` の手順にも、http で確認するときの指定を書く。
- 本番(Cloud Run)では設定しない。README に明記する。

### ドキュメントの更新(範囲に含める)

| ドキュメント | 現状 | 更新後 |
|---|---|---|
| README(Cloud Run 環境変数の表) | 解除の環境変数がない | 解除の環境変数の行(ローカルの HTTP のみ。本番では設定しない) |
| README(ローカルでの実行、ローカルで Docker ビルド確認) | http で確認するときは `SESSION_COOKIE_SECURE_DISABLED=1` を加える | 解除の環境変数も加えること。`run_dev_server.sh` は既定で与えること |
| README(デプロイ、研究用の対話ログのダウンロード) | 「本番は HTTPS のため…」「HTTP(ローカル起動)では資格情報は暗号化されない」 | 本番では http の要求はアプリが https へ移す・拒否すること、HSTS を付けること |
| `.env.example` | 解除の環境変数の項目がない | 項目がある(コメントアウトの例。本番では設定しない旨) |
| `scripts/run_dev_server.sh` | `SESSION_COOKIE_SECURE_DISABLED` だけを既定で `1` にする | 解除の環境変数も既定で `1` にする(`.env.local` の値を優先) |
| docs/requirements.md(NFR-06) | 「本番では HTTPS を前提とする(Cloud Run は標準で HTTPS)」、根拠は README | 「本番では、http の要求をアプリが https へ移す(GET・HEAD)か拒否し、https の応答に HSTS を付ける。ローカルの開発だけ環境変数で解除できる」、根拠に本仕様(本仕様の起草では触らない) |
| docs/spec/framework-drivers-layer.md(HTTP 契約、環境変数の表) | http の要求の扱い・HSTS・解除の環境変数の記述がない | HTTP 契約に「HTTPS の強制」の節(http の `GET`・`HEAD` は 301、それ以外は 400、認証・ログインの確認・DB より前に判定、https の応答に HSTS、解除の指定)、環境変数の表に `HTTPS_ENFORCEMENT_DISABLED` の行(PO決定 2026-10-26 で追加) |
| docs/spec/participant-login.md(制約の NFR-06 の行) | 「本番は HTTPS(Cloud Run)を前提とする」 | 本仕様への参照を1行足す(任意。AC には含めない) |

## 受入基準

テストの前提: 「http の要求」は、テストクライアントで `X-Forwarded-Proto: http` を付けた要求、または `X-Forwarded-Proto` を付けない要求を指す。「https の要求」は、`X-Forwarded-Proto: https` を付けた要求を指す。どちらも、解除の環境変数を未設定にして作ったアプリで検証する(AC8 を除く)。

### A. http の要求を処理しない

1. **画面の GET**: http の要求で `GET /lecture?lecture_id=lecture-2`、`GET /login`、`GET /`、`GET /static/js/common/api_client.js` を送ると、4つとも HTTP 301 で、`Location` が同じホスト・パス・クエリの `https://` の URL(例: `https://localhost/lecture?lecture_id=lecture-2`)である。ログインした状態で送っても同じで、応答の本文に、参加者の ID、学習データ、画面の HTML を含まない。`HEAD /lecture` も同じく 301 である。〔検証: 自動テスト〕
2. **ヘッダがない要求**: `X-Forwarded-Proto` を付けない `GET /lecture` は、AC1 と同じく 301 で `https://` へ移る(元の方式が分からない要求を https とみなさない)。〔検証: 自動テスト〕
3. **http の書き込み・ログインの送信**: http の要求で、正しい ID/パスワードの `POST /login`、ログインした状態の `POST /api/viewing-log`、`POST /api/quiz-attempts`、`POST /api/dialog-log`、`POST /chat` を送ると、5つとも HTTP 400 になる。2つの DB の行数は、送る前と変わらない。`POST /chat` では、AI(LLM)の呼び出しが起きない。`POST /login` の応答に `Set-Cookie`(セッション Cookie)がなく、続けて https の要求で `GET /lecture` を開くと、ログイン画面へのリダイレクト(302)になる(ログインが成立していない)。〔検証: 自動テスト(LLM は偽物に差し替える)〕
4. **研究者の経路**: http の要求で、正しい Basic 認証の資格情報を付けた `GET /research/dialog-logs` と `GET /research/participants/1/dialog-logs`、資格情報なしの `GET /research/dialog-logs` を送ると、3つとも HTTP 301 で `https://` の同じ URL へ移り、401 にならない(Basic 認証の照合より前に判定される)。応答の本文に、対話ログの内容(登録した対話の本文)を含まない。〔検証: 自動テスト〕

### B. https の要求は従来どおり

5. **https の通し**: https の要求で、ログイン(`POST /login`)→ `GET /lecture` → `POST /api/viewing-log` → `GET /api/participants/<本人>/lad` を行うと、#30 と同じ結果(ログインの成立、200、記録、200)になり、どの応答も 301 にならない(リダイレクトの繰り返しが起きない)。未ログインの `GET /lecture` は、ログイン画面への 302 で、その `Location` が `http://` で始まらない。https の要求で正しい Basic 認証を付けた `GET /research/dialog-logs` は 200、資格情報なしは 401 になる。〔検証: 自動テスト〕
6. **複数の値**: `X-Forwarded-Proto: http, https`(前段が後ろに追記した形)の要求は、最後の値の https として扱われ、`GET /login` は 200 になる。〔検証: 自動テスト〕

### C. HSTS(論点3)

7. **HSTS の付与**: https の要求への応答(`GET /login` の 200、未ログインの `GET /lecture` の 302、`GET /research/dialog-logs` の 401)に、`Strict-Transport-Security: max-age=31536000` が付く。http の要求への応答(AC1 の 301、AC3 の 400)には付かない。〔検証: 自動テスト〕

### D. ローカルの開発とテストでの解除

8. **解除の指定**: 解除の環境変数(論点4)を `1` にして作ったアプリでは、http の要求の `GET /login` が 200、正しい ID/パスワードの `POST /login` でログインが成立し、`Strict-Transport-Security` が付かない。解除の環境変数が未設定、空、`0`、`true` のときは、AC1 のとおり 301 になる(`1` のときだけ解除する)。〔検証: 自動テスト〕
9. **既存のテストの回帰**: 解除の環境変数をテストの共通設定で与えた状態で、`uv run pytest tests/ -v`(Windows は `PYTHONUTF8=1`)の既存のテスト(#30 の AC1〜30 のテスト、`tests/test_api/`、`tests/test_chat_lad/`、`tests/test_deploy/` を含む)が、すべて成功する。〔検証: 自動テスト〕
10. **Cookie の Secure と独立**: 解除の環境変数を `1` にしても、`SESSION_COOKIE_SECURE_DISABLED` を指定しなければ、ログインの成功の応答のセッション Cookie に `Secure` が付く(#30 AC21 の挙動を変えない)。〔検証: 自動テスト〕

### E. ドキュメントと本番

11. **ドキュメント**: README の環境変数の表に解除の環境変数の行があり、「ローカルの HTTP のみ」「本番では設定しない」と書かれている。README のローカルでの実行・ローカルの `docker run` の手順に、http で確認するときの解除の指定がある。README のデプロイの節に、本番では http の要求が https へ移る・拒否されることと、HSTS が付くことがある。`.env.example` に解除の環境変数の項目(コメントアウトの例)があり、`scripts/run_dev_server.sh` は、`.env.local` に値がなければ解除の環境変数を `1` にする。docs/requirements.md の NFR-06 が、本仕様を根拠として、上の「ドキュメントの更新」の内容になっている。〔検証: AI実行〕
12. **本番での確認**: 本番(Cloud Run)へデプロイした後、`curl.exe -i "http://<service-url>/login"` の応答が、301 または 302 で `Location` が `https://` で始まるか、Cloud Run 自身の転送になり、ログイン画面の HTML を返さない。`curl.exe -i "https://<service-url>/login"` は 200 で、`Strict-Transport-Security` が付く。`curl.exe -i -u "<user>:<password>" "http://<service-url>/research/dialog-logs"` は、対話ログを返さない。〔検証: PO確認(デプロイとコマンドの実行は PO が行う。UI 操作は含まない)〕

## 範囲外

- ログインの試行回数の制限、セッション固定の対策、Basic 認証の強化(PO の決定)。
- 独自ドメインの設定、TLS 証明書の管理(Cloud Run の既定の URL を使う前提)。
- HSTS の `preload` リストへの登録、`includeSubDomains`。
- Cloud Run の設定(ingress、IAM)の変更。
- ローカルの開発を https で動かす仕組み(ローカルは解除の指定で http のまま)。

## 制約・関連機能

- 関連: [participant-login.md](./participant-login.md)(#30。未ログインの拒否、Cookie の `Secure` と `SESSION_COOKIE_SECURE_DISABLED`、制約の NFR-06 の行)、[research-dialog-download.md](./research-dialog-download.md)(`/research/` の Basic 認証。本仕様は Basic 認証の照合を変えず、その前に http を判定する)、[db-persistence.md](./db-persistence.md)(`deploy/entrypoint.sh` の gunicorn の起動コマンド)、[framework-drivers-layer.md](./framework-drivers-layer.md)(HTTP 契約、デプロイ・運用)。
- 既存の依存だけで実現する(Werkzeug の `ProxyFix` は既存の依存に含まれる。実行で確認)。新しい依存を追加しない。
- 共有IF: 解除の環境変数の名前(論点4)。アプリ、`tests/conftest.py`・`tests/login_helpers.py`(読み込み前と各テストの環境)、`scripts/run_dev_server.sh`、`.env.example`、README が共有する。
- 設計上の注意(実装者への申し送り。方式は implementer が決める):
  - **D1(元の方式の判定)**: gunicorn の既定では、接続元が `127.0.0.1`・`::1` でないと `X-Forwarded-Proto` を採用しない(前提の観測)。Cloud Run での接続元は未確認のため、アプリ側で `X-Forwarded-Proto` を信頼する(例: Werkzeug の `ProxyFix(x_proto=1)`)か、gunicorn の `FORWARDED_ALLOW_IPS` を設定するかを決める。後者は `deploy/entrypoint.sh`(#29 の所有)を変え、ローカルの `flask run` とテストクライアントでは効かないため、AC1〜8 の自動テストでは前者の形が検証しやすい。どちらにしても、本番で https の要求が http と誤判定されると、AC5 の「リダイレクトの繰り返しが起きない」に反し、本番のすべての画面が使えなくなる。AC12(PO確認)で本番の判定を確かめる。
  - **D2(ヘッダの偽装)**: 利用者が http の接続で `X-Forwarded-Proto: https` を送って判定をすり抜けても、平文になるのはその利用者自身の通信だけで、第三者のデータは漏れない(前段が値を後ろに追記する場合は、AC6 のとおり最後の値が前段の値になる)。偽装への対策は本仕様で求めない。
  - **D3(リダイレクト先のホスト)**: リダイレクト先の `https://` の URL のホストは、要求の `Host` を使う。`X-Forwarded-Host` は判定に使わない(Cloud Run が `Host` に元のホストを渡すかは未確認。AC12 で確かめる)。
  - **D4(前処理の順序)**: http の判定は、研究者の Basic 認証・参加者のログインの確認・DB の接続より前に行う(AC3・4)。
  - **D5(既存のリダイレクト)**: ログイン画面へのリダイレクトなど、既存の `Location` はパスだけ(相対)で、https の要求では https のまま移る見込み(未確認: コードを読んだ推測。AC5 で確かめる)。

### 実現性の点検

- 影響ファイルの見込み:
  - 実装: 新規の HTTPS の強制のモジュール(`framework_drivers/platform/` 配下。`research_auth.py` と並ぶ)、`framework_drivers/platform/main.py`(登録の1〜数行。Basic 認証の登録より前)、`scripts/run_dev_server.sh`(解除の指定の既定)、`.env.example`(項目)。D1 で gunicorn 側を選ぶ場合のみ `deploy/entrypoint.sh`(非推奨)。
  - テスト: 新規 `tests/test_api/test_https_enforcement.py`(AC1〜8、10)。変更 `tests/login_helpers.py`(`apply_default_env` に解除の指定)、`tests/conftest.py`(各テストの環境に解除の指定。AC9)。`tests/test_deploy/` は gunicorn 側を選ばない限り変更なし。
  - ドキュメント: README(環境変数の表、ローカルでの実行、ローカルの Docker、デプロイ、研究用ダウンロードの注意)、docs/requirements.md(NFR-06)。
- 実装コード(src)の変更行数の見込み: 新規モジュール 40〜70 行、`main.py` 2〜5 行、`run_dev_server.sh` 2〜3 行。合計 45〜80 行(PBI の大きさの基準 300 行に対し、十分小さい)。
- 衝突・矛盾・依存の不足:
  - 既存のテストはすべて http で送るため、解除の指定をテストの共通設定に入れないと、ほぼすべてのテストが 301・400 で失敗する(AC9)。テストの共通設定の変更は、本 PBI の範囲に含める。
  - `deploy/entrypoint.sh`・`Dockerfile` は #29 の所有。D1 でアプリ側を選べば変更しない。
  - 依存の不足: なし(`ProxyFix` は Werkzeug 3.1.6 にあり、実行で確認)。
- テスト不能・曖昧なAC: AC12 は本番へのデプロイが要るため PO確認(UI 操作はない)。Cloud Run の http の扱い(前提の「Cloud Run の挙動」)が未確認のため、AC12 の http の応答は「アプリの 301 か、Cloud Run 自身の転送」のどちらでも合格にした。AC1〜11 は、テストクライアントとヘッダで自動テストにできる。
- 規模: 影響する実装ファイル 4(新規1)、テスト 3(新規1)。1 PBI・標準経路(タスク1つ)で足りる。分割は不要。
- 未解決の論点: なし(下記の論点1〜5は、PO が 2026-10-26 に決定済み)。

### 論点と PO の決定(2026-10-26 決定済み)

PO の決定(記録: `.work/sprint-001-https-enforcement/sprint-backlog.md` の「PO決定」)は、各論点の推奨案のとおり:

- 論点1: `GET`・`HEAD` は 301 で `https://` へ、それ以外は 400 で拒否し、何も記録しない。
- 論点2: `/research/*` にも適用する(Basic 認証の照合より前に判定。照合そのものは変えない)。
- 論点3: HSTS を付ける(`max-age=31536000`、`includeSubDomains`・`preload` なし)。
- 論点4: 新しい環境変数 `HTTPS_ENFORCEMENT_DISABLED`(`1` のときだけ解除)。
- 論点5: `X-Forwarded-Proto` がない要求は http とみなす(デプロイ直後に PO が curl で確認する = AC12。異常時は `HTTPS_ENFORCEMENT_DISABLED=1` で解除する)。

以下は、決定前に示した選択肢の記録。

1. **http の要求への応答の値**: (推奨)`GET`・`HEAD` は 301 で `https://` へ、それ以外は 400 で拒否。(代案A)全メソッドを 308 で `https://` へ(POST が本文ごと https に送り直されるが、パスワードはすでに平文で送られた後で、アプリが受け付けたことになる)。(代案B)全メソッドを 403 などで拒否し、リダイレクトしない(URL を `http://` で開いた利用者が画面に辿り着けない)。推奨の理由: 画面は利用者を https に導き、書き込み・ログインは平文で受け付けない(平文で送ってしまった送信を、成功させない)。AC1・3・4 の値がこれで決まる。
2. **研究者の `/research/` への適用**: (推奨)適用する(Basic 認証の資格情報と全参加者の対話ログが、最も守るべきデータのため。判定は Basic 認証の照合より前)。(代案)適用しない(FR-53 の「現状維持」を、経路の挙動も含めて変えないと読む)。FR-53 の「Basic 認証の強化は範囲外」との関係: 推奨案は、Basic 認証の照合そのもの(資格情報、401 の応答、no-store)を変えない。AC4 がこれで決まる。
3. **HSTS を付けるか**: (推奨)付ける。`max-age=31536000`(1年)、`includeSubDomains`・`preload` なし。理由: リダイレクトだけでは、利用者が `http://` で開いた最初の要求(とその Cookie)が平文で出る。HSTS があれば、2回目以降はブラウザが送る前に https にする。(代案)付けない(「HTTPS の強制」をサーバ側のリダイレクト・拒否に限る)。(代案)付けるが期間を短くする(例: 1日 `max-age=86400`。実験期間中に http へ戻す必要が出たときの影響が小さい)。AC7・8 がこれで決まる。
4. **解除の環境変数**: (推奨)新しい環境変数 `HTTPS_ENFORCEMENT_DISABLED`(`1` のときだけ解除)を設ける。理由: 承認済みの `SESSION_COOKIE_SECURE_DISABLED` の意味(#30 AC21)を変えない。指定が2つになるが、`run_dev_server.sh` とテストの共通設定が両方を既定で与えるため、手間は増えない。(代案)既存の `SESSION_COOKIE_SECURE_DISABLED=1` に、HTTPS の強制の解除も兼ねさせる(「ローカルの HTTP 実行」の指定を1つにまとめる。#30 の環境変数の意味が広がるため、participant-login.md と README の記述も変わる)。AC8・10 がこれで決まる。
5. **ヘッダがない要求の扱い**(確認): 推奨は「http とみなす」(AC2。分からない要求を安全側に倒す)。本番で Cloud Run が必ず `X-Forwarded-Proto` を付けるかは未確認で、付けない場合は本番のすべての画面が 301 の繰り返しになる。その場合は AC12 で発覚するため、デプロイ直後の確認を PO にお願いする。この扱いでよいか。

## 変更理由

- issue #32: #30 で未ログインの拒否と他人の ID の拒否が入った後、POが追加の要件として「HTTPS の強制」を決めた(本番で http の要求を https に限定し、ログイン情報・データを平文で流さない)。そのために新規に起草した。値と範囲の論点(論点1〜5)は、PO の決定を待つ。
- issue #32(2026-10-26、PO決定の反映): 論点1〜5 の PO 決定(すべて推奨案)を「論点と PO の決定」の節に反映した。reviewer の差し戻し(DoD のドキュメントの同期)を受けた PO 決定により、「ドキュメントの更新」の表に docs/spec/framework-drivers-layer.md を追加した。AC の内容は変えていない。
