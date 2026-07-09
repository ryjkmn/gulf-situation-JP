# GULF WATCH JP

無料のGitHub Pages用プロトタイプです。

## 公開手順
1. GitHubで `gulf-watch-jp` というPublic repositoryを作る。
2. このZIPを展開し、中身をrepositoryのルートへアップロードする。
3. GitHubの Settings → Pages を開く。
4. Sourceを `Deploy from a branch`、Branchを `main`、Folderを `/ (root)` にしてSave。
5. 数分後に公開URLが表示される。

## 自動更新
`.github/workflows/update-news.yml` は毎時実行されます。
現時点の `update_news.py` は安全な土台で、AI要約APIや具体的なRSSソースはまだ接続していません。
