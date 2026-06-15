import argparse
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
TRANSLATIONS_DIR = ROOT_DIR / "docs" / "translations"


def resolve_series_dir(value):
    path = Path(value)
    if path.exists():
        return path

    series_path = TRANSLATIONS_DIR / value
    if series_path.exists():
        return series_path

    raise FileNotFoundError(f"Novel folder or series id not found: {value}")


def normalize_chapter_text(text):
    text = text.replace("<blank>", "<b>")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    fixed_lines = []
    for line in text.split("\n"):
        is_blank = line.strip() == ""
        if is_blank:
            if fixed_lines and fixed_lines[-1] != "":
                fixed_lines.append("")
            continue

        if fixed_lines and fixed_lines[-1] != "":
            fixed_lines.append("")
        fixed_lines.append(line)

    while fixed_lines and fixed_lines[-1] == "":
        fixed_lines.pop()

    return "\n".join(fixed_lines) + ("\n" if fixed_lines else "")


def quick_fix_chapters(series_dir):
    en_dir = series_dir / "en"
    if not en_dir.exists():
        raise FileNotFoundError(f"EN folder does not exist: {en_dir}")

    files_checked = 0
    files_changed = 0
    for path in sorted(en_dir.glob("*.txt")):
        files_checked += 1
        original = path.read_text(encoding="utf-8-sig")
        fixed = normalize_chapter_text(original)
        if fixed != original:
            path.write_text(fixed, encoding="utf-8")
            files_changed += 1
            print(f"Fixed {path}")

    return files_checked, files_changed


def parse_args():
    parser = argparse.ArgumentParser(
        description="Apply quick formatting fixes to all EN chapter files in a novel folder."
    )
    parser.add_argument("novel", help="Novel folder path or series id under docs/translations.")
    return parser.parse_args()


def main():
    args = parse_args()
    series_dir = resolve_series_dir(args.novel)
    files_checked, files_changed = quick_fix_chapters(series_dir)
    print(f"Checked {files_checked} EN file(s); changed {files_changed}.")


if __name__ == "__main__":
    main()
