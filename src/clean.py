from pathlib import Path

import numpy as np
import pandas as pd
import pandas_market_calendars as mcal

# dates databento flagged as reduced quality
degraded = ["2024-09-18", "2025-09-17", "2025-09-24"]

# each contract follows its own globex calendar
calendars = {
    "ES": "CME_Equity",
    "ZN": "CME_Bond",
    "CL": "CMEGlobex_Energy",
    "GC": "CMEGlobex_EnergyAndMetals",
    "HG": "CMEGlobex_EnergyAndMetals",
    "ZC": "CMEGlobex_Grains",
}


def trading_days(instrument, start, end):
    """Full-length sessions only, so holidays and early closes are excluded."""
    sched = mcal.get_calendar(calendars[instrument]).schedule(start, end)
    hours = (sched.market_close - sched.market_open).dt.total_seconds() / 3600
    full = sched[hours >= hours.median() - 0.5]
    return set(full.index.date)


def load(raw_dir="data/raw"):
    frames = []
    for path in sorted(Path(raw_dir).glob("*_1h.csv")):
        d = pd.read_csv(path, usecols=["ts_event", "instrument_id", "close", "volume"])
        d["instrument"] = path.stem.replace("_1h", "")
        frames.append(d)

    df = pd.concat(frames, ignore_index=True)
    df["ts_event"] = pd.to_datetime(df["ts_event"], utc=True)
    df["date"] = df["ts_event"].dt.date
    df["hour"] = df["ts_event"].dt.hour
    return df.sort_values(["instrument", "ts_event"]).reset_index(drop=True)


def clean(df):
    n = len(df)

    # databento degraded dates
    df = df[~df["date"].isin(pd.to_datetime(degraded).date)]
    print(f"  {n - len(df):>6,} dropped (degraded dates)")

    # whole calendar day on which the contract rolls, before any other day is
    # removed, so the instrument_id change is detected on the day it happened
    n = len(df)
    ids = df.groupby("instrument")["instrument_id"]
    rolled = ids.transform(lambda s: s.ne(s.shift()) & s.shift().notna())
    roll_days = pd.MultiIndex.from_frame(
        df.loc[rolled, ["instrument", "date"]].drop_duplicates()
    )
    keys = pd.MultiIndex.from_arrays([df["instrument"], df["date"]])
    df = df[~keys.isin(roll_days)]
    print(f"  {n - len(df):>6,} dropped (roll days)")

    # holidays and early closes, per instrument calendar
    n = len(df)
    start, end = df["date"].min(), df["date"].max()
    keep = pd.Series(False, index=df.index)
    for name, part in df.groupby("instrument"):
        days = trading_days(name, start, end)
        keep.loc[part.index] = part["date"].isin(days)
    df = df[keep]
    print(f"  {n - len(df):>6,} dropped (holidays and early closes)")

    # amihud is undefined with no volume
    n = len(df)
    df = df[df["volume"] > 0]
    print(f"  {n - len(df):>6,} dropped (zero volume)")

    return df.reset_index(drop=True)


def measures(df):
    df = df.sort_values(["instrument", "ts_event"]).copy()
    g = df.groupby("instrument", sort=False)

    df["ret"] = g["close"].transform(lambda s: np.log(s).diff())

    # only measure a return between bars an hour apart, never across a gap
    gap = g["ts_event"].transform(lambda s: s.diff())
    df.loc[gap != pd.Timedelta(hours=1), "ret"] = np.nan

    df["rv"] = df["ret"].abs()
    df["amihud"] = df["rv"] / df["volume"]

    print(f"  {df['ret'].isna().sum():>6,} bars have no return (gap or first bar)")
    return df.reset_index(drop=True)