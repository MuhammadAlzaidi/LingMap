"""Black-and-white linguistic maps with English figure labels."""
from io import BytesIO
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import geopandas as gpd
from adjustText import adjust_text

ROOT = Path(__file__).parent
COUNTRIES = ["Saudi Arabia","Jordan","Iraq","Egypt","Morocco","Tunisia","Algeria"]
REQUIRED = {"country","city","latitude","longitude"}
CONTEXT = {
"Saudi Arabia":[("Yemen",44.6,15.3),("Oman",56.3,20.7),("United Arab Emirates",54.4,24.4),("Qatar",51.4,25.4),("Kuwait",47.8,29.8),("Jordan",36.7,31.0),("Iraq",43.0,32.5)],
"Jordan":[("Saudi Arabia",39.3,28.3),("Iraq",43.1,33.4),("Syria",36.5,33.5)],
"Iraq":[("Turkey",43.0,38.3),("Syria",39.0,35.2),("Jordan",36.7,31.0),("Saudi Arabia",43.1,27.9),("Kuwait",47.8,29.4)],
"Egypt":[("Sudan",30.0,19.6),("Libya",21.4,26.0)],
"Morocco":[("Algeria",-1.0,32.0)],
"Tunisia":[("Algeria",7.3,34.2),("Libya",12.1,31.8)],
"Algeria":[("Morocco",-6.3,32.2),("Tunisia",10.3,34.5),("Libya",12.5,28.5),("Mali",-4.5,19.0),("Niger",9.8,18.8)]
}
def validate_locations(df):
    missing = REQUIRED-set(df.columns)
    if missing: raise ValueError("Missing CSV columns: "+", ".join(sorted(missing)))
    df = df.copy()
    for col in ("latitude","longitude"):
        df[col] = pd.to_numeric(df[col],errors="coerce")
    bad = (df.latitude.isna()|df.longitude.isna()|~df.latitude.between(-90,90)|~df.longitude.between(-180,180))
    if bad.any(): raise ValueError(f"{bad.sum()} row(s) contain invalid coordinates")
    if df[["city","country"]].isna().any().any(): raise ValueError("Country and city are required")
    return df

def make_figure(df, selected_countries, title="Linguistic research locations",
                labels=True,marker_size=46,show_gulf=True,figsize=(10,8),
                sampled_cities=None,show_context=True,show_legend=True,
                show_axes=False,show_notes=False):
    df=validate_locations(df)
    selected_countries=[x for x in selected_countries if x in COUNTRIES]
    if not selected_countries: raise ValueError("Select at least one supported country")
    shapes=gpd.read_file(ROOT/"data"/"arab_countries.geojson")
    shapes=shapes[shapes.name.isin(selected_countries)]
    if shapes.empty: raise ValueError("No country boundaries available")
    sampled_cities=set(sampled_cities or [])
    shown=df[df.country.isin(selected_countries)]
    fig,ax=plt.subplots(figsize=figsize,layout="constrained")
    fig.patch.set_facecolor("white")
    ax.set_facecolor("white")
    shapes.plot(ax=ax,color="#f1f1f1",edgecolor="#333333",linewidth=1.1,zorder=1)
    xmin,ymin,xmax,ymax=shapes.total_bounds
    xp=max((xmax-xmin)*.13,1.5); yp=max((ymax-ymin)*.13,1.5)
    ax.set_xlim(xmin-xp,xmax+xp); ax.set_ylim(ymin-yp,ymax+yp)
    if show_context:
        for country in selected_countries:
            for name,lon,lat in CONTEXT.get(country,[]):
                if name not in selected_countries and xmin-xp<lon<xmax+xp and ymin-yp<lat<ymax+yp:
                    ax.text(lon,lat,name,color="#666666",fontsize=8,ha="center",zorder=2)
    if show_gulf and "Saudi Arabia" in selected_countries:
        ax.text(51.7,26.6,"Gulf Sea",fontsize=9,color="#555555",fontstyle="italic",ha="center")
    if show_context and "Saudi Arabia" in selected_countries:
        ax.text(38,23,"Red Sea",fontsize=9,color="#555555",fontstyle="italic",rotation=70,ha="center")
    texts=[]
    for row in shown.itertuples():
        sample=str(row.city) in sampled_cities
        ax.scatter(row.longitude,row.latitude,s=marker_size*(1.5 if sample else 1),
                   facecolor="black" if sample else "white",edgecolor="black",
                   linewidth=1.2,zorder=5)
        if labels:
            texts.append(ax.text(row.longitude+.06,row.latitude+.06,str(row.city),
                                 fontsize=8.2,color="black",zorder=6))
    if texts:
        adjust_text(texts,ax=ax,expand=(1.2,1.35),
                    arrowprops=dict(arrowstyle="-",color="#888888",lw=.5))
    ax.set_title(title,fontsize=14,fontweight="bold",pad=12)
    if show_axes:
        ax.set_xlabel("Longitude (°E)"); ax.set_ylabel("Latitude (°N)")
        ax.grid(color="#dddddd",linewidth=.4,zorder=0)
    else: ax.set_axis_off()
    if show_legend and len(shown):
        handles=[Line2D([],[],marker="o",linestyle="None",markerfacecolor="black",
                        markeredgecolor="black",label="Data collection site"),
                 Line2D([],[],marker="o",linestyle="None",markerfacecolor="white",
                        markeredgecolor="black",label="Reference city")]
        ax.legend(handles=handles,loc="lower left",fontsize=8,
                  facecolor="white",edgecolor="#777777")
    if show_notes:
        fig.text(.08,.015,"Illustrative locations; not dialect boundaries. "
                 "Country outlines are simplified.",fontsize=7,color="#555555")
    return fig

def export_figure(fig,fmt="png",dpi=600):
    if fmt not in ("png","pdf","svg"): raise ValueError("Unsupported export format")
    buf=BytesIO()
    fig.savefig(buf,format=fmt,dpi=dpi,bbox_inches="tight",facecolor="white")
    return buf.getvalue()
