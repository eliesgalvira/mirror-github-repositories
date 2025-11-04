import subprocess
import sys
from textwrap import dedent

YAML = dedent(
    """\
name: Mirror to GitLab

on:
  push:
    branches: ["**"]
    tags: ["*"]
  create:
  delete:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  mirror:
    runs-on: ubuntu-latest
    permissions:
      contents: read
    concurrency:
      group: mirror-${{ github.repository }}-${{ github.ref }}
      cancel-in-progress: true

    steps:
      - name: Checkout (full history)
        uses: actions/checkout@v4
        with:
          fetch-depth: 0
          fetch-tags: true

      - name: Start SSH agent and add deploy key
        uses: webfactory/ssh-agent@v0.9.0
        with:
          ssh-private-key: ${{ secrets.MIRROR_SSH_KEY }}
          log-public-key: false

      - name: Trust gitlab.com host
        run: |
          mkdir -p ~/.ssh
          ssh-keyscan -t rsa,ed25519 gitlab.com >> ~/.ssh/known_hosts

      - name: Configure Git safe.directory
        run: git config --global --add safe.directory "$GITHUB_WORKSPACE"

      - name: Normalize origin and fetch everything
        run: |
          git remote set-url origin "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}.git"
          git fetch --prune --tags origin
          git for-each-ref --format='%(refname:strip=3)' refs/remotes/origin | while read -r br; do
            [ "$br" = "HEAD" ] && continue
            git update-ref "refs/heads/$br" "refs/remotes/origin/$br"
          done

      - name: Push to GitLab (branches/tags only)
        env:
          MIRROR_URL: ${{ secrets.MIRROR_URL }}
        run: |
          git remote remove mirror 2>/dev/null || true
          git remote add mirror "$MIRROR_URL"
          git push --prune mirror +refs/heads/*:refs/heads/* +refs/tags/*:refs/tags/*
          git push --prune mirror +refs/notes/*:refs/notes/* || true
    """
)


def copy_clipboard(text: str) -> bool:
    # Try pyperclip
    try:
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return True
    except Exception:
        pass

    # Wayland/X11 fallbacks
    for cmd in (
        ["wl-copy"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
    ):
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            return True
        except Exception:
            continue
    return False


def main() -> None:
    print(".github/workflows/mirror-to-gitlab.yml")
    # Print to stdout so it's easy to redirect to a file if desired
    print(YAML, end="")

    if copy_clipboard(YAML):
        print("\n(Copied workflow YAML to clipboard)", file=sys.stderr)
    else:
        print(
            "\n(Clipboard copy unavailable. Install pyperclip and "
            "wl-clipboard or xclip/xsel.)",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()
