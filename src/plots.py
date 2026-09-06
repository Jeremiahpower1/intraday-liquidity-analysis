from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

sns.set_theme(style="darkgrid", context="paper")
plt.rcParams["figure.titlesize"] = 14

figdir = Path("figures")
period = "Aug 2024 to Aug 2026"

labels = {"volume": "turnover", "rv": "absolute return", "amihud": "Amihud illiquidity"}

names = {
    "ES": "E-mini S&P 500",
    "CL": "WTI Crude Oil",
    "ZC": "Corn",
    "ZN": "10-Year T-Note",
    "GC": "Gold",
    "HG": "Copper",
}

# rough session windows in UTC; they overlap, so shaded regions darken where more than one session is open
sessions = [
    ("Asia", 0, 9, "#4c72b0"),
    ("Europe", 8, 17, "#55a868"),
    ("US", 13, 22, "#c44e52"),
]


def shade_sessions(ax, alpha=0.08):
    lo, hi = ax.get_xlim()
    for name, start, end, colour in sessions:
        if end > lo and start < hi:
            a, b = max(start, lo), min(end, hi)
            ax.axvspan(a, b, color=colour, alpha=alpha, zorder=0, lw=0)
            ax.text((a + b) / 2, 0.97, name, transform=ax.get_xaxis_transform(),
                    ha="center", va="top", fontsize=8, color=colour, alpha=0.9)


def save(fig, name):
    # called explicitly, so nothing is written unless you ask for it
    figdir.mkdir(exist_ok=True)
    fig.savefig(figdir / f"{name}.png", dpi=200)


def heatmap(tables, measure):
    # span the same hours in every figure, even where one measure has a gap, so the three read against each other
    hours = sorted(set().union(*(t.columns for t in tables.values())))

    fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
    sns.heatmap(tables[measure].reindex(columns=hours), ax=ax, cmap="viridis",
                cbar_kws={"label": "Median percentile within day (0 = lowest)"})
    ax.set_title(f"Hourly {labels[measure]} heatmap (UTC, {period})", fontsize=14)
    ax.set_ylabel("")
    ax.set_xticks([i + 0.5 for i in range(len(hours))],
                  [f"{h:02d}:00" for h in hours], rotation=90)
    ax.set_xlabel("Hour (UTC)")
    return fig


def profiles(prof):
    insts = prof.index.get_level_values(0).unique()
    ncol = 3
    nrow = -(-len(insts) // ncol)

    fig, axes = plt.subplots(nrow, ncol, figsize=(11, 3 * nrow),
                             constrained_layout=True)
    for ax, inst in zip(axes.flat, insts):
        s = prof.loc[inst]
        ax.plot(s.index, s[0.5])
        ax.fill_between(s.index, s[0.25], s[0.75], alpha=0.25)
        ax.set_yscale("log")

        # scale from the median line, so an extreme quartile doesn't stretch the panel
        ax.set_ylim(s[0.5].min() / 4, s[0.5].max() * 4)

        ax.set_title(f"{names.get(inst, inst)} ({inst})", fontsize=9)

        # end the axis where the contract stops trading, so no empty grid
        ax.set_xlim(s.index.min(), s.index.max())
        ticks = [h for h in range(0, 24, 4) if s.index.min() <= h <= s.index.max()]
        ax.set_xticks(ticks, [f"{h:02d}:00" for h in ticks], rotation=90)

    for ax in axes.flat[len(insts):]:
        ax.set_visible(False)

    fig.supxlabel("Hour (UTC)")
    fig.supylabel("Amihud illiquidity (higher = less liquid)")
    fig.suptitle(f"Hourly illiquidity profile by contract (UTC, {period})")
    return fig


def overlay(norm):
    fig, ax = plt.subplots(figsize=(11, 6), constrained_layout=True)
    for inst in norm.index:
        ax.plot(norm.columns, norm.loc[inst], marker="o", ms=3, label=inst)
    ax.axhline(1.0, color="grey", lw=0.8, ls="--")
    ax.set_xticks(range(24), [f"{h:02d}:00" for h in range(24)], rotation=90)
    ax.set_xlabel("Hour (UTC)")
    ax.set_ylabel("illiquidity vs own daily mean")
    ax.set_title(f"Normalised hourly illiquidity profile (UTC, {period})", fontsize=14)
    shade_sessions(ax)
    leg = ax.legend(facecolor="white", edgecolor="black", framealpha=1)
    leg.get_frame().set_boxstyle("Square", pad=0.4)
    return fig