import pandas as pd

# turnover only needs a bar; rv and amihud need a return as well
needs_return = {"volume": False, "rv": True, "amihud": True}

# an instrument-hour needs at least this many observations to be estimated
min_obs = 150


def usable(df, measure="amihud"):
    if needs_return[measure]:
        df = df.dropna(subset=["ret"])

    n = df.groupby(["instrument", "hour"])[measure].transform("size")
    return df[n >= min_obs]


def ranked(df):
    out = {}
    for m in needs_return:
        d = usable(df, m)

        r = d.groupby(["instrument", "date"])[m].rank(pct=True)

        out[m] = (d.assign(rank=r)
                   .pivot_table(index="instrument", columns="hour",
                                values="rank", aggfunc="median"))
    return out


def profiles(df, measure="amihud"):
    return (usable(df, measure)
            .groupby(["instrument", "hour"])[measure]
            .quantile([0.25, 0.5, 0.75])
            .unstack())


def overlay(df, measure="amihud"):
    med = (usable(df, measure)
           .groupby(["instrument", "hour"])[measure]
           .median()
           .unstack())
    return med.div(med.mean(axis=1), axis=0)


def best_worst(df, n=3, measure="amihud"):
    rows = []
    med = usable(df, measure).groupby(["instrument", "hour"])[measure].median()

    for name in med.index.get_level_values(0).unique():
        s = med[name].sort_values()
        rows.append({
            "instrument": name,
            "cheapest hours (UTC)": ", ".join(f"{h:02d}:00" for h in s.index[:n]),
            "dearest hours (UTC)": ", ".join(f"{h:02d}:00" for h in s.index[-n:][::-1]),
            "worst / best": round(s.iloc[-1] / s.iloc[0], 1),
        })

    return (pd.DataFrame(rows)
            .set_index("instrument")
            .sort_values("worst / best", ascending=False))


def counts(df, measure="amihud"):
    d = df.dropna(subset=["ret"]) if needs_return[measure] else df
    return d.pivot_table(index="instrument", columns="hour",
                         values=measure, aggfunc="size")