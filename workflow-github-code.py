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

jobs:
  mirror:
    runs-on: ubuntu-latest
    permissions:
      contents: read

    steps:
      - name: Checkout
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

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

      - name: Fetch all branches and tags from origin
        run: |
          # Point origin to the canonical repo URL and fetch everything
          git remote set-url origin "${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}.git"
          git fetch --prune --tags origin

          # Materialize every remote branch as a local branch
          git for-each-ref --format='%(refname:strip=3)' refs/remotes/origin | while read -r br; do
            [ "$br" = "HEAD" ] && continue
            git update-ref "refs/heads/$br" "refs/remotes/origin/$br"
          done

          echo "Local heads before cleanup:" >&2
          git for-each-ref --format='%(refname)' refs/heads | sed 's#^#  #'

          # Remove synthetic/internal heads created by actions/checkout in PRs:
          # e.g., refs/heads/repo/mirror-*, or any heads starting with repo/, pull/, changes/
          for ns in repo pull changes; do
            git for-each-ref --format='%(refname)' "refs/heads/${ns}" | while read -r ref; do
              echo "Deleting stray head: $ref" >&2
              git update-ref -d "$ref" || true
            done
          done

          echo "Local heads after cleanup:" >&2
          git for-each-ref --format='%(refname)' refs/heads | sed 's#^#  #'

      - name: Push to GitLab (branches/tags only)
        env:
          MIRROR_URL: ${{ secrets.MIRROR_URL }}
        run: |
          git remote remove mirror 2>/dev/null || true
          git remote add mirror "$MIRROR_URL"

          # Push only standard namespaces
          git push --prune mirror +refs/heads/*:refs/heads/* +refs/tags/*:refs/tags/*

          # Optional notes
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
