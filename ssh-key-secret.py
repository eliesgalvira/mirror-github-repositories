import base64
import sys
from pathlib import Path

KEY_PATH = Path.home() / ".ssh" / "gitlab_gha_mirror"


def osc52_copy(text: str) -> None:
    # OSC 52 escape sequence to set clipboard contents
    b64 = base64.b64encode(text.encode("utf-8")).decode("ascii")
    sys.stdout.write(f"\033]52;c;{b64}\a")
    sys.stdout.flush()


def main() -> None:
    print("MIRROR_SSH_KEY")
    path = KEY_PATH
    if not path.is_file():
        print(f"Error: {path} not found or not a file", file=sys.stderr)
        sys.exit(1)

    try:
        data = path.read_text(encoding="utf-8")
    except Exception as e:
        print(f"Error reading key: {e}", file=sys.stderr)
        sys.exit(1)

    if "PRIVATE KEY" not in data:
        print("Error: file does not look like a private key", file=sys.stderr)
        sys.exit(1)

    # Normalize trailing newline (some clipboards/targets prefer it)
    data = data.rstrip("\n") + "\n"

    try:
        osc52_copy(data)
        print("Copied private key via OSC 52 (terminal clipboard).", file=sys.stderr)
    except Exception as e:
        print(f"OSC 52 copy failed: {e}", file=sys.stderr)
        sys.exit(1)

    if len(sys.argv) > 1 and sys.argv[1] == "--print":
        print(data, end="")


if __name__ == "__main__":
    main()
