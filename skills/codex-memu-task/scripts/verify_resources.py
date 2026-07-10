import os

MEMU_BASE_DIR = "~/.memu"
TEMP_RESOURCE_FILE = ".resource.tmp"
OUTPUT_RESOURCE_FILE = "resources.md"

MAX_RESOURCE = 50


def main():
    base_dir = os.path.expanduser(MEMU_BASE_DIR)
    input_path = os.path.join(base_dir, TEMP_RESOURCE_FILE)
    output_path = os.path.join(base_dir, OUTPUT_RESOURCE_FILE)

    valid_paths = []
    seen = set()

    with open(input_path, encoding="utf-8") as f:
        for line in f:
            path = line.strip()
            if not path:
                continue
            # keep only absolute paths (/ or ~)
            if not (path.startswith("/") or path.startswith("~")):
                continue
            # dedup, preserving first-seen order
            if path in seen:
                continue
            seen.add(path)
            # verify the path exists and is a file
            if os.path.isfile(os.path.expanduser(path)):
                valid_paths.append(path)
            if len(valid_paths) >= MAX_RESOURCE:
                break

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("---\n")
        for path in valid_paths:
            f.write(f"path: {path}\n")
            f.write("description: \n")
            f.write("---\n")


if __name__ == "__main__":
    main()
