import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.clean import clean, load, measures

df = load("data/raw")
print(f"loaded {len(df):,} bars across {df['instrument'].nunique()} instruments")

df = clean(df)
df = measures(df)

out = Path("data/processed/bars.parquet")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_parquet(out, index=False)
print(f"wrote {len(df):,} bars to {out}")