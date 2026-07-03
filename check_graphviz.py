from __future__ import annotations

import shutil
import subprocess
import sys


def main() -> int:
    dot_path = shutil.which("dot")

    if not dot_path:
        print("Graphviz check: FAILED")
        print("Could not find 'dot' on PATH.")
        print()
        print("Windows setup steps:")
        print("1. Install Graphviz from https://graphviz.org/download/")
        print("2. Add the Graphviz bin folder to PATH, for example:")
        print("   C:\\Program Files\\Graphviz\\bin")
        print("3. Open a new terminal and run this script again.")
        print()
        print("Tip: You can verify manually with: dot -V")
        return 1

    print("Graphviz check: FOUND")
    print(f"dot path: {dot_path}")

    try:
        # Graphviz writes version text to stderr in many builds.
        result = subprocess.run(
            [dot_path, "-V"],
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as error:
        print(f"Graphviz check: FAILED ({error})")
        return 1

    version_output = (result.stderr or result.stdout).strip()
    if version_output:
        print(version_output)

    if result.returncode != 0:
        print("Graphviz check: FAILED to execute dot correctly.")
        return result.returncode

    print("Graphviz check: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())