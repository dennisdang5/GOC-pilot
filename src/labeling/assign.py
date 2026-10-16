"""Split the samples into ID-only assignment files to send to labelers.

Run from anywhere:  python -m src.labeling.assign

  data/assignments/test_physician.parquet   all 50 test notes
  data/assignments/dev_A.parquet .. dev_E   6 dev notes each (consecutive chunks of the
                                            already-random label_order)

Columns: ROW_ID, CATEGORY, n_chars, label_order. Stratum and cues are dropped so labelers stay
blind. No note text. Refuses to overwrite existing assignments. Prints counts only.
"""

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DERIVED = ROOT / "data" / "derived"
OUT_DIR = ROOT / "data" / "assignments"
DEV_SLOTS = ["A", "B", "C", "D", "E"]
COLUMNS = ["ROW_ID", "CATEGORY", "n_chars", "label_order"]


def split_dev(dev: pd.DataFrame, slots: list[str]) -> dict[str, pd.DataFrame]:
    """Consecutive equal chunks of dev in label_order, renumbered 1..n within each chunk."""
    dev = dev.sort_values("label_order", ignore_index=True)
    if len(dev) % len(slots):
        raise ValueError(f"{len(dev)} dev notes do not split evenly into {len(slots)}")
    size = len(dev) // len(slots)
    out = {}
    for i, slot in enumerate(slots):
        chunk = dev.iloc[i * size:(i + 1) * size][COLUMNS].copy()
        chunk["label_order"] = range(1, size + 1)
        out[f"dev_{slot}"] = chunk.reset_index(drop=True)
    return out


def main() -> int:
    test = pd.read_parquet(DERIVED / "test_sample.parquet")
    dev = pd.read_parquet(DERIVED / "dev_sample.parquet")
    files = {"test_physician": test.sort_values("label_order", ignore_index=True)[COLUMNS]}
    files.update(split_dev(dev, DEV_SLOTS))

    all_ids = pd.concat([df["ROW_ID"] for df in files.values()])
    assert all_ids.is_unique, "a ROW_ID is assigned twice"

    existing = [n for n in files if (OUT_DIR / f"{n}.parquet").exists()]
    if existing:
        print(f"assign: refusing to overwrite {existing}; delete by hand to redo")
        return 1
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, df in files.items():
        df.to_parquet(OUT_DIR / f"{name}.parquet", index=False)
        cats = {c.strip(): int(v) for c, v in df["CATEGORY"].value_counts().items()}
        print(f"{name:<16}{len(df):>4} notes  {cats}")
    print(f"\nwrote {len(files)} files to {OUT_DIR.relative_to(ROOT).as_posix()}/ ({len(all_ids)} notes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
