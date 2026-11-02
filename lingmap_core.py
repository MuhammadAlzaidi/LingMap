"""LingMap map generation and export; map text is always English."""
from io import BytesIO
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import geopandas as gpd

ROOT = Path(__file__).parent
COUNTRIES = ["Saudi Arabia", "Jordan", "Iraq", "Egypt", "Morocco", "Tunisia", "Algeria"]
REQUIRED = {"country", "city", "latitude", "longitude"}

def validate_locations(df):
    missing = REQUIRED - set(df.columns)
    if missing:
        raise ValueError("Missing CSV columns: " + ", ".join(sorted(missing)))
    df = df.copy()
    for col in ("latitude", "longitude"):
        df[col] = pd.to_numeric(df[col], errors="coerce")
    invalid = (df.latitude.isna() | df.longitude.isna() |
               ~df.latitude.between(-90, 90) | ~df.longitude.between(-180, 180))
    if invalid.any():
        raise ValueError(f"{invalid.sum()} row(s) contain invalid coordinates.")
    if df[["city", "country"]].isna().any().any():
        raise ValueError("Country and city must be provided for every row.")
    return df

def make_figure(df, selected_countries, title="Linguistic research locations",
                labels=True, marker_size=46, show_gulf=True, figsize=(11, 7)):
    df = validate_locations(df)
    selected_countries = [c for c in selected_countries if c in COUNTRIES]
    if not selected_countries:
        raise ValueError("Select at least one supported country.")
    shapes = gpd.read_file(ROOT / "data" / "arab_countries.geojson")
    shapes = shapes[shapes["name"].isin(selected_countries)]
    if shapes.empty:
        raise ValueError("No country boundaries available for selection.")
    fig, ax = plt.subplots(figsize=figsize, layout="constrained")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("#eef6f8")
    shapes.plot(ax=ax, color="#f5f2e9", edgecolor="#45576a", linewidth=.95)
    shown = df[df.country.isin(selected_countries)]
    palette = plt.get_cmap("tab10")
    for i, (country, group) in enumerate(shown.groupby("country", sort=True)):
        ax.scatter(group.longitude, group.latitude, s=marker_size,
                   color=palette(i % 10), edgecolor="white", linewidth=.6,
                   label=country, zorder=4)
        if labels:
            for row in group.itertuples():
                ax.annotate(str(row.city), (row.longitude, row.latitude),
                            xytext=(4, 4), textcoords="offset points",
                            fontsize=7.5, zorder=5)
    xmin, ymin, xmax, ymax = shapes.total_bounds
    xpad = max((xmax-xmin)*.08, 1.1)
    ypad = max((ymax-ymin)*.08, 1.1)
    ax.set_xlim(xmin-xpad, xmax+xpad)
    ax.set_ylim(ymin-ypad, ymax+ypad)
    if show_gulf and "Saudi Arabia" in selected_countries:
        ax.text(51.5, 26.7, "Gulf Sea", fontsize=9, color="#35677c",
                fontstyle="italic", ha="center")
    ax.set_title(title, fontsize=15, fontweight="bold", pad=14)
    ax.set_xlabel("Longitude (°E)")
    ax.set_ylabel("Latitude (°N)")
    ax.grid(alpha=.14, linewidth=.5)
    if shown.country.nunique() > 1:
        ax.legend(loc="best", fontsize=8)
    ax.text(.01, -.13,
            "Boundaries: Natural Earth (1:110m); locations: illustrative city coordinates.\n"
            "Locations do not indicate dialect boundaries. Custom waterbody label: Gulf Sea.",
            transform=ax.transAxes, fontsize=7, color="#5b6570", va="top")
    return fig

def export_figure(fig, fmt="png", dpi=600):
    if fmt not in ("png", "pdf", "svg"):
        raise ValueError("Unsupported export format")
    buf = BytesIO()
    fig.savefig(buf, format=fmt, dpi=dpi, bbox_inches="tight", facecolor="white")
    return buf.getvalue()
