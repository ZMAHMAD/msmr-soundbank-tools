import os

SRC_DIR = "../Soundbanks/"
DST_DIR = "../Banks/"
MAGIC = b"BKHD"

os.makedirs(DST_DIR, exist_ok=True)

for fname in os.listdir(SRC_DIR):
    if not fname.endswith(".soundbank"):
        continue

    path = os.path.join(SRC_DIR, fname)
    with open(path, "rb") as f:
        data = f.read()

    offset = data.find(MAGIC)

    if offset == -1:
        print(f"[SKIP] {fname}: BKHD not found")
        continue

    stripped = data[offset:]
    out_name = fname.replace(".soundbank", ".bnk")
    out_path = os.path.join(DST_DIR, out_name)

    with open(out_path, "wb") as f:
        f.write(stripped)

    print(f"[OK] {fname}: BKHD at offset {hex(offset)} -> {out_name}")