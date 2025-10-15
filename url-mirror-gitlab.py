import sys
from urllib.parse import urlparse
import subprocess


def extract_project_path(url: str) -> str:
    p = urlparse(url)
    if not p.netloc:
        raise ValueError("Invalid URL: missing host")
    if p.netloc.lower() != "gitlab.com":
        raise ValueError("Only gitlab.com is supported")

    parts = [seg for seg in p.path.strip("/").split("/") if seg]

    if "-" in parts:
        cut = parts.index("-")
        proj_parts = parts[:cut]
    else:
        proj_parts = parts

    if len(proj_parts) < 2:
        raise ValueError(
            "Could not determine project path. Expect https://gitlab.com/group/repo/..."
        )

    if proj_parts[-1].endswith(".git"):
        proj_parts[-1] = proj_parts[-1][:-4]

    return "/".join(proj_parts)


def to_ssh_url(project_path: str) -> str:
    return f"git@gitlab.com:{project_path}.git"


def copy_clipboard(text: str) -> bool:
    # Try pyperclip
    try:
        import pyperclip  # type: ignore

        pyperclip.copy(text)
        return True
    except Exception:
        pass

    # Wayland: wl-copy
    for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]):
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True)
            return True
        except Exception:
            continue
    return False


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "Usage:\n  python url-mirror-gitlab.py https://gitlab.com/group/repo/-/tree/main",
            file=sys.stderr,
        )
        sys.exit(2)

    url = sys.argv[1]
    try:
        project_path = extract_project_path(url)
        ssh_url = to_ssh_url(project_path)
        print(f"MIRROR_URL={ssh_url}")
        if copy_clipboard(ssh_url):
            print("(Copied SSH URL to clipboard)", file=sys.stderr)
        else:
            print(
                "(Clipboard copy unavailable. Install pyperclip and xclip/xsel or wl-clipboard.)",
                file=sys.stderr,
            )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
