# Mirror GitHub repositories

One-time setup (do this once)
- Generate and secure an SSH key for mirroring:
  ```bash
  ssh-keygen -t ed25519 -C "gha-mirror" -f ~/.ssh/gitlab_gha_mirror -N ""
  chmod 600 ~/.ssh/gitlab_gha_mirror
  ```
- Add this key once to any GitLab project as a Deploy Key with write access:
  - GitLab → Project → Settings → Repository → Deploy keys → Add new key
  - Title: gha-mirror
  - Key:
    ```bash
    cat ~/.ssh/gitlab_gha_mirror.pub
    ```
  - Check “Grant write permissions to this key” → Add key
- Prepare your GitHub secret value (you’ll paste this per repo as a repository secret):
  - Private key content:
    ```bash
    cat ~/.ssh/gitlab_gha_mirror
    ```

For each additional GitLab destination repo
1) Enable the existing key (don’t paste again)
- GitLab → Project → Settings → Repository → Deploy keys
- Find the key under “Privately accessible deploy keys” (or “Publicly accessible deploy keys”)
- Click Enable
- If an Edit button is present, open it and ensure “Grant write permissions to this key” is checked

2) Get the GitLab SSH URL
- It’s on the project homepage → Clone → SSH
- Or construct it: git@gitlab.com:GROUP_OR_USER/REPO.git

For each GitHub source repo you want to mirror
3) Add repository-level GitHub Actions secrets
- GitHub → Repo → Settings → Secrets and variables → Actions → New repository secret
- MIRROR_SSH_KEY
  - Value is the entire private key content:
    ```bash
    cat ~/.ssh/gitlab_gha_mirror
    ```
  - Paste everything including the BEGIN/END lines
- MIRROR_URL
  - Value is the GitLab SSH URL, e.g.:
    ```text
    git@gitlab.com:GROUP/REPO.git
    ```
  - If you are lazy, just copy the url and run `uv run url-mirror-gitlab.py URL` (file in this repo) and it'll paste to clipboard the right format
Note: Use repository secrets (not environment secrets) unless you have a specific env setup.

4) Add the workflow file
- Create .github/workflows/mirror-to-gitlab.yml with:
```yaml
name: Mirror to GitLab
on:
  push:
    branches: ["**"]
    tags: ["*"]

jobs:
  mirror:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    steps:
      - name: Checkout full history
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Start SSH agent and add deploy key
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.MIRROR_SSH_KEY }}

      - name: Trust gitlab.com host
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -t rsa,ed25519 gitlab.com >> ~/.ssh/known_hosts

      - name: Configure Git safe.directory
        run: git config --global --add safe.directory "$GITHUB_WORKSPACE"

      - name: Fetch all branches/tags
        run: |
          git fetch --prune --tags origin

      - name: Push mirror to GitLab (heads/tags/notes only)
        env:
          MIRROR_URL: ${{ secrets.MIRROR_URL }}
        run: |
          git remote remove mirror 2>/dev/null || true
          git remote add mirror "$MIRROR_URL"
          git push --prune mirror +refs/heads/*:refs/heads/* +refs/tags/*:refs/tags/*
          git push --prune mirror +refs/notes/*:refs/notes/* || true
```

5) Commit and push
- Any push to the GitHub repo will trigger the workflow and mirror to GitLab.

Optional adjustments
- If GitLab protected branches prevent forced updates, remove the leading + signs:
  - Change `+refs/heads/*:refs/heads/*` to `refs/heads/*:refs/heads/*`
  - Do the same for tags if needed.

Quick verification
- After first run, list branches and tags on GitLab:
  - UI: Project → Repository → Branches / Tags
  - Or via SSH:
    ```bash
    git ls-remote --heads git@gitlab.com:GROUP_OR_USER/REPO.git
    git ls-remote --tags  git@gitlab.com:GROUP_OR_USER/REPO.git
    ```

If you want, tell me the next repo pair and I’ll produce the exact MIRROR_URL and a ready workflow patch.
