"""Interactive cleanup for the soundbank -> bnk -> wem -> wav pipeline.

Only files with the listed extensions are deleted. The category folders
themselves are kept (so your batch files still find them), and empty
subfolders left behind are removed.
"""

from pathlib import Path

BASE = Path(__file__).resolve().parent

CATEGORIES = {
    "1": ("Soundbanks (.soundbank)", BASE / ".." / "Soundbanks", ".soundbank"),
    "2": ("Banks (.bnk)", BASE / ".." / "Banks", ".bnk"),
    "3": ("WEMs (.wem)", BASE / ".." / "WEMs", ".wem"),
    "4": ("WAVs (.wav)", BASE / ".." / "WAVs", ".wav"),
}


def find_files(folder: Path, ext: str) -> list[Path]:
    if not folder.is_dir():
        return []
    return [p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == ext]


def human_size(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024 or unit == "GB":
            return f"{n:.1f} {unit}"
        n /= 1024


def remove_empty_dirs(root: Path) -> None:
    if not root.is_dir():
        return
    for d in sorted((p for p in root.rglob("*") if p.is_dir()), reverse=True):
        try:
            d.rmdir()  # only succeeds if empty
        except OSError:
            pass


def show_menu() -> dict[str, list[Path]]:
    print("\nDelete which file types?\n")
    found = {}
    for key, (label, folder, ext) in CATEGORIES.items():
        files = find_files(folder, ext)
        found[key] = files
        size = sum(f.stat().st_size for f in files)
        status = f"{len(files)} files, {human_size(size)}" if folder.is_dir() else "folder not found"
        print(f"  [{key}] {label:<26} {status}")
    print("  [a] All of the above")
    print("  [q] Quit\n")
    return found


def main() -> None:
    while True:
        found = show_menu()
        choice = input("Enter numbers separated by commas (e.g. 2,3), 'a', or 'q': ").strip().lower()

        if choice in ("q", ""):
            print("Nothing deleted.")
            return

        keys = list(CATEGORIES) if choice == "a" else [c.strip() for c in choice.split(",")]
        invalid = [k for k in keys if k not in CATEGORIES]
        if invalid:
            print(f"Invalid option(s): {', '.join(invalid)}")
            continue
        keys = list(dict.fromkeys(keys))  # dedupe, keep order

        to_delete = [(k, f) for k in keys for f in found[k]]
        if not to_delete:
            print("No matching files found for that selection.")
            continue

        total = sum(f.stat().st_size for _, f in to_delete)
        print("\nAbout to permanently delete:")
        for k in keys:
            print(f"  - {CATEGORIES[k][0]}: {len(found[k])} files")
        print(f"Total: {len(to_delete)} files, {human_size(total)}")
        print("This does not use the Recycle Bin.\n")

        if input("Type DELETE to confirm: ").strip() != "DELETE":
            print("Cancelled.\n")
            continue

        deleted = failed = 0
        for _, f in to_delete:
            try:
                f.unlink()
                deleted += 1
            except OSError as e:
                failed += 1
                print(f"  [FAILED] {f}: {e}")

        for k in keys:
            remove_empty_dirs(CATEGORIES[k][1])

        print(f"\nDeleted {deleted} files" + (f", {failed} failed." if failed else "."))

        if input("\nDelete more? (y/n): ").strip().lower() != "y":
            return


if __name__ == "__main__":
    main()