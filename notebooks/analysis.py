"""
F1 Data Engineering Portfolio — Analysis Layer
===============================================
Generates all charts and narrative outputs from the pipeline marts.
Run this after pipeline.py has populated the outputs/ directory.

    python notebooks/analysis.py
"""

import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.colors import LinearSegmentedColormap
import matplotlib.patheffects as pe

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT       = Path(__file__).resolve().parent.parent
OUTPUTS    = ROOT / "outputs"
CHARTS_DIR = ROOT / "outputs" / "charts"

# ---------------------------------------------------------------------------
# Global style
# ---------------------------------------------------------------------------
F1_RED    = "#E8002D"
F1_DARK   = "#0A0A0A"
F1_GREY   = "#1C1C1C"
F1_SILVER = "#C0C0C0"
F1_WHITE  = "#F5F5F5"
ACCENT    = "#FF8000"   # orange

TEAM_COLORS = {
    "Mercedes":    "#00D2BE",
    "Red Bull":    "#3671C6",
    "Ferrari":     "#DC0000",
    "McLaren":     "#FF8000",
    "Renault":     "#FFF500",
    "Alpine F1 Team": "#0093CC",
    "Williams":    "#005AFF",
    "Aston Martin":"#006F62",
    "Brawn":       "#80FF00",
    "Lotus F1 Team":"#FFB800",
}


def style_ax(ax, title="", xlabel="", ylabel="", grid_axis="y"):
    """Apply F1-themed styling to a matplotlib Axes."""
    ax.set_facecolor(F1_GREY)
    ax.set_title(title,  color=F1_WHITE, fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color=F1_SILVER, fontsize=10)
    ax.set_ylabel(ylabel, color=F1_SILVER, fontsize=10)
    ax.tick_params(colors=F1_SILVER, labelsize=9)
    for spine in ax.spines.values():
        spine.set_edgecolor("#333333")
    if grid_axis:
        ax.grid(axis=grid_axis, color="#2E2E2E", linewidth=0.8, linestyle="--")
    ax.set_axisbelow(True)


def save_chart(fig, name):
    """Save a figure to the charts directory and close it."""
    path = CHARTS_DIR / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=F1_DARK)
    plt.close(fig)
    print(f"  ✓ Saved: {name}")
    return path


# ===========================================================================
# Chart generators
# ===========================================================================

def chart_top15_drivers(drivers):
    """Chart 1 — Top 15 Drivers by Total Points (career bar chart)."""
    print("\n[1/7] Top 15 Drivers by Career Points …")

    top15 = drivers.head(15).copy()
    fig, ax = plt.subplots(figsize=(12, 7), facecolor=F1_DARK)
    style_ax(ax, title="Top 15 Drivers — Career Points (2000–2024)",
             xlabel="", ylabel="Total Championship Points")

    bar_colors = [F1_RED if n == top15["full_name"].iloc[0] else F1_SILVER
                  for n in top15["full_name"]]

    bars = ax.barh(top15["full_name"][::-1], top15["points_total"][::-1],
                   color=bar_colors[::-1], height=0.7, edgecolor="#111111", linewidth=0.5)

    for bar, pts in zip(bars, top15["points_total"][::-1]):
        ax.text(bar.get_width() + 30, bar.get_y() + bar.get_height() / 2,
                f"{pts:,.0f}", va="center", color=F1_WHITE, fontsize=9, fontweight="bold")

    ax.set_xlim(0, top15["points_total"].max() * 1.15)
    ax.invert_yaxis()
    ax.tick_params(left=False)

    # Champion badge (data-driven)
    _leader = top15.iloc[0]
    ax.text(0.98, 0.02, f"★ {_leader['full_name']}\n   {_leader['points_total']:,.0f} pts",
            transform=ax.transAxes, ha="right", va="bottom",
            color=ACCENT, fontsize=11, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#1A1A1A", edgecolor=ACCENT, linewidth=1.5))

    fig.tight_layout()
    save_chart(fig, "01_top15_driver_career_points.png")


def chart_win_vs_podium(drivers):
    """Chart 2 — Win Rate vs Podium Rate Scatter."""
    print("[2/7] Win Rate vs Podium Rate scatter …")

    qual = drivers[drivers["races_entered"] >= 50].copy()
    qual["surname"] = qual["full_name"].str.split().str[-1]

    fig, ax = plt.subplots(figsize=(11, 8), facecolor=F1_DARK)
    style_ax(ax, title="Win Rate vs Podium Rate — Drivers with 50+ Starts (2000–2024)",
             xlabel="Podium Rate (%)", ylabel="Win Rate (%)", grid_axis=None)

    ax.grid(color="#2E2E2E", linewidth=0.8, linestyle="--")

    sizes = (qual["races_entered"] / qual["races_entered"].max() * 900) + 50

    scatter = ax.scatter(
        qual["podium_rate_pct"], qual["win_rate_pct"],
        s=sizes, c=qual["points_per_race"],
        cmap=LinearSegmentedColormap.from_list("f1", [F1_SILVER, F1_RED, ACCENT]),
        alpha=0.85, edgecolors="#111", linewidths=0.8,
    )

    labels = ["Hamilton", "Verstappen", "Vettel", "Schumacher", "Alonso", "Räikkönen", "Rosberg"]
    for _, row in qual.iterrows():
        if row["surname"] in labels:
            ax.annotate(
                row["surname"],
                xy=(row["podium_rate_pct"], row["win_rate_pct"]),
                xytext=(6, 4), textcoords="offset points",
                color=F1_WHITE, fontsize=9, fontweight="bold",
                path_effects=[pe.withStroke(linewidth=2, foreground=F1_DARK)],
            )

    cbar = fig.colorbar(scatter, ax=ax, pad=0.02)
    cbar.set_label("Points per Race", color=F1_SILVER, fontsize=9)
    cbar.ax.yaxis.set_tick_params(color=F1_SILVER)
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color=F1_SILVER, fontsize=8)

    for size_val, label in [(50, "50 races"), (200, "200 races"), (350, "350+ races")]:
        s = (size_val / qual["races_entered"].max() * 900) + 50
        ax.scatter([], [], s=s, c=F1_SILVER, alpha=0.7, label=label, edgecolors="#111")
    ax.legend(loc="upper left", facecolor=F1_GREY, edgecolor="#444",
              labelcolor=F1_WHITE, fontsize=8, title="Bubble = Races Entered",
              title_fontsize=8)

    fig.tight_layout()
    save_chart(fig, "02_win_rate_vs_podium_rate.png")


def chart_dominance_hhi(seasons):
    """Chart 3 — Dominance HHI over seasons."""
    print("[3/7] Dominance HHI over seasons …")

    fig, ax = plt.subplots(figsize=(14, 6), facecolor=F1_DARK)
    style_ax(ax, title="Championship Competitiveness Over Time (2000–2024)",
             xlabel="Season", ylabel="Dominance Index (HHI)\nHigher = More Dominant",
             grid_axis="y")

    years = seasons["year"]
    hhi   = seasons["dominance_hhi"]

    ax.fill_between(years, hhi, alpha=0.15, color=F1_RED)
    ax.plot(years, hhi, color=F1_RED, linewidth=2.5, zorder=5)
    ax.scatter(years, hhi, color=F1_WHITE, s=40, zorder=6, edgecolors=F1_RED, linewidths=1.5)

    ax.axhspan(0.0, 0.18, alpha=0.07, color="#00FF00", label="Competitive")
    ax.axhspan(0.35, 1.0,  alpha=0.07, color="#FF0000", label="Dominant")

    peaks = seasons.nlargest(3, "dominance_hhi")
    for _, row in peaks.iterrows():
        ax.annotate(
            f"{row['wdc_driver'].split()[-1]}\n{row['year']}\nHHI={row['dominance_hhi']:.2f}",
            xy=(row["year"], row["dominance_hhi"]),
            xytext=(0, 18), textcoords="offset points",
            ha="center", color=ACCENT, fontsize=8.5, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=ACCENT, lw=1),
        )

    for _, row in seasons.iterrows():
        ax.text(row["year"], -0.04, row["wdc_driver"].split()[-1],
                ha="center", va="top", color=F1_SILVER, fontsize=7,
                rotation=45, transform=ax.get_xaxis_transform())

    ax.set_xlim(1999.5, 2024.5)
    ax.set_ylim(-0.02, hhi.max() * 1.25)
    ax.legend(facecolor=F1_GREY, edgecolor="#444", labelcolor=F1_WHITE, fontsize=9)

    fig.tight_layout()
    save_chart(fig, "03_season_dominance_hhi.png")


def chart_constructor_points(teams):
    """Chart 4 — Constructor Points Over Time (top 5 teams)."""
    print("[4/7] Constructor points over time …")

    top_teams = (
        teams.groupby("name")["points_total"].sum()
        .nlargest(5).index.tolist()
    )

    fig, ax = plt.subplots(figsize=(14, 7), facecolor=F1_DARK)
    style_ax(ax, title="Top 5 Constructors — Points Per Season (2000–2024)",
             xlabel="Season", ylabel="Championship Points")

    for team in top_teams:
        td = teams[teams["name"] == team].sort_values("year")
        color = TEAM_COLORS.get(team, F1_SILVER)
        ax.plot(td["year"], td["points_total"], marker="o", linewidth=2.2,
                markersize=5, label=team, color=color,
                path_effects=[pe.withStroke(linewidth=4, foreground="#00000055")])

    ax.legend(facecolor=F1_GREY, edgecolor="#444", labelcolor=F1_WHITE,
              fontsize=9, loc="upper left")
    ax.set_xlim(1999.5, 2024.5)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{int(x):,}"))

    fig.tight_layout()
    save_chart(fig, "04_constructor_points_over_time.png")


def chart_dnf_vs_points(drivers):
    """Chart 5 — DNF Rate vs Points Per Race."""
    print("[5/7] DNF Rate vs Points Per Race …")

    qual2 = drivers[drivers["races_entered"] >= 30].copy()
    qual2["surname"] = qual2["full_name"].str.split().str[-1]

    fig, ax = plt.subplots(figsize=(11, 7), facecolor=F1_DARK)
    style_ax(ax, title="Reliability vs Performance — DNF Rate vs Points Per Race",
             xlabel="DNF Rate (%)", ylabel="Points Per Race", grid_axis=None)
    ax.grid(color="#2E2E2E", linewidth=0.8, linestyle="--")

    nat_colors = {
        "British":   "#00247D", "German":    "#FFCE00", "Finnish":   "#003580",
        "Spanish":   "#AA151B", "Dutch":     "#FF6600", "Australian":"#00843D",
        "Brazilian": "#009c3b", "Mexican":   "#006847", "French":    "#0055A4",
        "Monegasque":"#CE1126",
    }

    for _, row in qual2.iterrows():
        c = nat_colors.get(row["nationality"], F1_SILVER)
        ax.scatter(row["dnf_rate_pct"], row["points_per_race"],
                   color=c, s=80, alpha=0.8, edgecolors="#111", linewidths=0.6)

    labels2 = ["Hamilton", "Verstappen", "Vettel", "Schumacher", "Alonso"]
    for _, row in qual2.iterrows():
        if row["surname"] in labels2:
            ax.annotate(row["surname"],
                        xy=(row["dnf_rate_pct"], row["points_per_race"]),
                        xytext=(6, 3), textcoords="offset points",
                        color=F1_WHITE, fontsize=9, fontweight="bold",
                        path_effects=[pe.withStroke(linewidth=2, foreground=F1_DARK)])

    med_dnf = qual2["dnf_rate_pct"].median()
    med_ppr = qual2["points_per_race"].median()
    ax.axvline(med_dnf, color="#444", linewidth=1, linestyle=":")
    ax.axhline(med_ppr, color="#444", linewidth=1, linestyle=":")
    ax.text(med_dnf + 0.3, ax.get_ylim()[1] * 0.97, "Median DNF", color="#666", fontsize=8)

    handles = [mpatches.Patch(color=c, label=n) for n, c in list(nat_colors.items())[:6]]
    ax.legend(handles=handles, facecolor=F1_GREY, edgecolor="#444",
              labelcolor=F1_WHITE, fontsize=8, title="Nationality",
              title_fontsize=8, loc="upper right")

    fig.tight_layout()
    save_chart(fig, "05_dnf_rate_vs_points_per_race.png")


def chart_wdc_margin(seasons):
    """Chart 6 — WDC margin of victory over time."""
    print("[6/7] WDC margin of victory …")

    fig, axes = plt.subplots(1, 2, figsize=(16, 6), facecolor=F1_DARK)

    ax = axes[0]
    style_ax(ax, title="WDC Points Margin (P1 vs P2) by Season",
             xlabel="Season", ylabel="Margin (Points)", grid_axis="y")

    colors_bar = [F1_RED if m > 100 else F1_SILVER for m in seasons["wdc_margin_pts"]]
    ax.bar(seasons["year"], seasons["wdc_margin_pts"],
           color=colors_bar, edgecolor="#111", linewidth=0.5, width=0.75)

    tight = seasons[seasons["wdc_margin_pts"] <= 5]
    for _, row in tight.iterrows():
        ax.text(row["year"], row["wdc_margin_pts"] + 4,
                f"±{row['wdc_margin_pts']:.0f}",
                ha="center", color=ACCENT, fontsize=8, fontweight="bold")

    ax2 = axes[1]
    style_ax(ax2, title="Races Per Season — Calendar Growth",
             xlabel="Season", ylabel="Number of Races", grid_axis="y")
    ax2.bar(seasons["year"], seasons["total_races"],
            color=F1_SILVER, edgecolor="#111", linewidth=0.5, width=0.75)
    ax2.plot(seasons["year"], seasons["total_races"],
             color=F1_RED, linewidth=2, marker="o", markersize=4)
    ax2.set_ylim(0, seasons["total_races"].max() + 3)

    fig.tight_layout()
    save_chart(fig, "06_wdc_margin_and_calendar.png")


def chart_reliability_heatmap(teams):
    """Chart 7 — Team reliability heatmap (2015-2024)."""
    print("[7/7] Team reliability heatmap …")

    team_rel = teams[teams["year"] >= 2015].copy()
    pivot = team_rel.pivot_table(index="name", columns="year",
                                  values="reliability_pct", aggfunc="mean")

    pivot = pivot.dropna(thresh=5)
    pivot = pivot.sort_values(by=pivot.columns[-1], ascending=False)

    fig, ax = plt.subplots(figsize=(14, max(6, len(pivot) * 0.55)), facecolor=F1_DARK)
    ax.set_facecolor(F1_DARK)
    fig.patch.set_facecolor(F1_DARK)

    cmap = LinearSegmentedColormap.from_list("rel", ["#8B0000", "#FF6B6B", "#FFD700", "#00C851"])
    im = ax.imshow(pivot.values, cmap=cmap, aspect="auto", vmin=70, vmax=100)

    ax.set_xticks(range(len(pivot.columns)))
    ax.set_xticklabels([str(y) for y in pivot.columns], color=F1_SILVER, fontsize=9)
    ax.set_yticks(range(len(pivot.index)))
    ax.set_yticklabels(pivot.index, color=F1_WHITE, fontsize=9)
    ax.tick_params(left=False, bottom=False)
    for spine in ax.spines.values():
        spine.set_visible(False)

    for i in range(len(pivot.index)):
        for j in range(len(pivot.columns)):
            val = pivot.values[i, j]
            if not np.isnan(val):
                ax.text(j, i, f"{val:.0f}%",
                        ha="center", va="center",
                        color="white" if val < 88 else "black",
                        fontsize=8, fontweight="bold")

    cbar = fig.colorbar(im, ax=ax, orientation="horizontal", pad=0.05, shrink=0.5)
    cbar.set_label("Reliability (%)", color=F1_SILVER, fontsize=9)
    cbar.ax.xaxis.set_tick_params(color=F1_SILVER)
    plt.setp(cbar.ax.xaxis.get_ticklabels(), color=F1_SILVER, fontsize=8)

    ax.set_title("Team Reliability Heatmap (2015–2024)\n% of Race Entries That Finished",
                 color=F1_WHITE, fontsize=13, fontweight="bold", pad=15)

    fig.tight_layout()
    save_chart(fig, "07_team_reliability_heatmap.png")


def print_narrative_summary(drivers, teams, seasons):
    """Print data-driven narrative insights to the console."""
    print("\n" + "=" * 65)
    print("  F1 DATA PIPELINE — KEY INSIGHTS (2000–2024)")
    print("=" * 65)

    champ = drivers.iloc[0]
    print(f"\n● GREATEST DRIVER\n  {champ['full_name']} leads with {champ['points_total']:,.0f} pts across "
          f"{champ['seasons_active']} seasons,\n  {champ['wins']} wins ({champ['win_rate_pct']:.1f}% win rate) "
          f"and {champ['podiums']} podiums.")

    dom_season = seasons.loc[seasons["dominance_hhi"].idxmax()]
    print(f"\n● MOST DOMINANT SEASON\n  {int(dom_season['year'])}: {dom_season['wdc_driver']} won by "
          f"{dom_season['wdc_margin_pts']:.0f} pts (HHI={dom_season['dominance_hhi']:.2f}).")

    tight_season = seasons.loc[seasons["wdc_margin_pts"].idxmin()]
    print(f"\n● CLOSEST TITLE FIGHT\n  {int(tight_season['year'])}: {tight_season['wdc_driver']} won "
          f"by just {tight_season['wdc_margin_pts']:.0f} pt(s).")

    best_team = teams.groupby("name")["points_total"].sum().idxmax()
    best_pts  = teams.groupby("name")["points_total"].sum().max()
    print(f"\n● DOMINANT CONSTRUCTOR\n  {best_team} accumulated the most points of any team "
          f"({best_pts:,.0f} total across the modern era).")

    most_wins_driver = drivers.sort_values("wins", ascending=False).iloc[0]
    print(f"\n● MOST RACE WINS\n  {most_wins_driver['full_name']}: {most_wins_driver['wins']} wins "
          f"from {most_wins_driver['races_entered']} starts.")

    print(f"\n● CALENDAR GROWTH\n  F1 expanded from {seasons['total_races'].min()} races/season "
          f"(2003) to {seasons['total_races'].max()} (2024) — a "
          f"{seasons['total_races'].max() - seasons['total_races'].min()} race increase.")

    print(f"\n● 2023 ANOMALY\n  Verstappen's 2023 HHI of "
          f"{seasons.loc[seasons['year'] == 2023, 'dominance_hhi'].values[0]:.2f} "
          "is the highest since the Schumacher era,\n  with 21 wins and a 290-pt margin over P2.")

    print("\n" + "=" * 65)
    print(f"  All charts saved to: {CHARTS_DIR}")
    print("=" * 65 + "\n")


# ===========================================================================
# Main entry point
# ===========================================================================

def main():
    """Generate all charts and print narrative insights."""
    CHARTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load marts
    drivers = pd.read_csv(OUTPUTS / "driver_performance_mart.csv")
    teams   = pd.read_csv(OUTPUTS / "team_performance_mart.csv")
    seasons = pd.read_csv(OUTPUTS / "season_trends_mart.csv")

    # Generate charts
    chart_top15_drivers(drivers)
    chart_win_vs_podium(drivers)
    chart_dominance_hhi(seasons)
    chart_constructor_points(teams)
    chart_dnf_vs_points(drivers)
    chart_wdc_margin(seasons)
    chart_reliability_heatmap(teams)

    # Print insights
    print_narrative_summary(drivers, teams, seasons)


if __name__ == "__main__":
    main()
