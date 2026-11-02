# Dockerで始めるPostgreSQL入門：コンテナ起動からデータ挿入まで

Dockerを使うと、ローカル環境を汚さずに数分でPostgreSQL環境を構築できます。本チュートリアルでは、DockerコンテナとしてPostgreSQLを立ち上げ、psql経由でテーブルを作成し、データを挿入・確認する一連の手順を初心者向けに解説します。

---

## 前提条件

- Docker（Docker DesktopまたはDocker Engine）がインストールされ、起動していること
- ターミナル（macOS / Linux）またはPowerShell（Windows）を使えること

---

## ステップ 1: PostgreSQLコンテナを起動する

ターミナルを開き、以下のコマンドを実行します。

```bash
docker run --name my-postgres \
  -e POSTGRES_PASSWORD=mysecretpassword \
  -p 5432:5432 \
  -d postgres:16
```

### オプションの解説

| オプション | 意味 |
| :--- | :--- |
| `--name my-postgres` | コンテナに `my-postgres` という名前を付けます。 |
| `-e POSTGRES_PASSWORD=mysecretpassword` | 環境変数で管理者ユーザー（`postgres`）のパスワードを設定します。 |
| `-p 5432:5432` | ホストマシンのポート5432をコンテナのポート5432に転送します。 |
| `-d` | バックグラウンド（デタッチモード）でコンテナを実行します。 |
| `postgres:16` | 使用するDockerイメージ（バージョン16）を指定します。 |

---

## ステップ 2: コンテナの起動状態を確認する

コンテナが正常に動作しているか確認します。

```bash
docker ps
```

出力例（`STATUS` が `Up ...` になっていれば成功です）:

```text
CONTAINER ID   IMAGE         COMMAND                  STATUS         PORTS                    NAMES
a1b2c3d4e5f6   postgres:16   "docker-entrypoint.s…"   Up 5 seconds   0.0.0.0:5432->5432/tcp   my-postgres
```

---

## ステップ 3: psql（PostgreSQL対話型シェル）に接続する

コンテナ内で動作しているPostgreSQLの対話型クライアント `psql` に接続します。

```bash
docker exec -it my-postgres psql -U postgres
```

プロンプトが以下のように変われば、接続完了です。

```text
postgres=#
```

---

## ステップ 4: テーブルを作成する

接続先のデータベース（デフォルトの `postgres`）に、サンプルとして `users` テーブルを作成します。

以下のSQLを入力して `Enter` キーを押します。

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**実行結果:**
```text
CREATE TABLE
```

### テーブル構造の確認

`\d` コマンドで作成したテーブルを確認できます。

```text
postgres=# \d users
```

---

## ステップ 5: データを挿入する（INSERT）

作成した `users` テーブルにレコードを追加します。

```sql
INSERT INTO users (name, email) VALUES
    ('田中 太郎', 'tanaka@example.com'),
    ('佐藤 花子', 'sato@example.com');
```

**実行結果:**
```text
INSERT 0 2
```

---

## ステップ 6: データを検索・確認する（SELECT）

挿入されたデータを確認します。

```sql
SELECT * FROM users;
```

**実行結果:**
```text
 id |   name    |       email        |         created_at         
----+-----------+--------------------+----------------------------
  1 | 田中 太郎 | tanaka@example.com | 2026-11-01 01:35:00.123456
  2 | 佐藤 花子 | sato@example.com   | 2026-11-01 01:35:00.123456
(2 rows)
```

---

## ステップ 7: 後片付け（psqlの終了とコンテナの停止）

### psqlを終了する

以下のコマンドを入力してpsqlを終了し、ローカルのターミナルに戻ります。

```text
postgres=# \q
```

### コンテナを停止・再開・削除する

- **コンテナの停止:**
  ```bash
  docker stop my-postgres
  ```

- **停止したコンテナの再開:**
  ```bash
  docker start my-postgres
  ```

- **コンテナの削除（不要になった場合）:**
  ```bash
  docker rm -f my-postgres
  ```
  ※ コンテナを削除すると、ボリュームマウントを行っていない場合データも消去されます。
