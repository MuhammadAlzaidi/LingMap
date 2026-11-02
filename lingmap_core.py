"""LingMap: journal-ready monochrome linguistic maps (English figure text only)."""
from io import BytesIO
from pathlib import Path
from functools import lru_cache
import json
import urllib.request
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import pandas as pd
import geopandas as gpd

ROOT=Path(__file__).parent
COUNTRIES=["Saudi Arabia","Jordan","Iraq","Egypt","Morocco","Tunisia","Algeria"]
CONTEXT={"Yemen","Oman","United Arab Emirates","Qatar","Kuwait","Syria","Turkey",
         "Sudan","Libya","Mali","Niger","Mauritania","Lebanon","Djibouti","Bahrain"}
ALLOWED=set(COUNTRIES)|CONTEXT
REQUIRED={"country","city","latitude","longitude"}
MAP_URL="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
SIZES={"Single column (85 mm)":85,"Double column (175 mm)":175,
       "Presentation (250 mm)":250}
MARKERS={"Data collection site":("o","black",1.2),
         "Comparison site":("o","white",1.2),
         "Reference city":("^","#bdbdbd",1.0)}

def validate_locations(df):
    missing=REQUIRED-set(df.columns)
    if missing: raise ValueError("Missing CSV columns: "+", ".join(sorted(missing)))
    df=df.copy()
    for key in ("latitude","longitude"): df[key]=pd.to_numeric(df[key],errors="coerce")
    bad=df.latitude.isna()|df.longitude.isna()|~df.latitude.between(-90,90)|~df.longitude.between(-180,180)
    if bad.any(): raise ValueError(f"Invalid coordinates in {int(bad.sum())} row(s)")
    if df[["city","country"]].isna().any().any(): raise ValueError("Country and city are required")
    return df

@lru_cache(maxsize=1)
def boundaries():
    """Cache Natural Earth 1:110m geometries; NEVER render excluded countries."""
    local=ROOT/"data"/"natural_earth_110m.geojson"
    if not local.exists():
        # Download once on first map request; caching avoids repeated network calls.
        try:
            with urllib.request.urlopen(MAP_URL,timeout=35) as response:
                raw=response.read()
            obj=json.loads(raw)
            if obj.get("type")!="FeatureCollection" or len(obj.get("features",[]))<100:
                raise ValueError("Unexpected Natural Earth data")
            local.parent.mkdir(exist_ok=True)
            local.write_bytes(raw)
        except Exception as exc:
            raise RuntimeError("Natural Earth basemap unavailable. Retry shortly. "+str(exc)) from exc
    geo=gpd.read_file(local)
    col=next((c for c in ("ADMIN","admin","NAME","name") if c in geo.columns),None)
    if col is None: raise RuntimeError("Natural Earth country name field not found")
    geo=geo.rename(columns={col:"country"})
    # Source sometimes uses 'United States of America', irrelevant to our area.
    return geo[geo.country.isin(ALLOWED)][["country","geometry"]].copy()

def make_figure(df,selected_countries,title="",labels=True,marker_size=42,
                show_gulf=True,sampled_cities=None,show_context=True,
                show_legend=True,show_axes=False,show_notes=False,
                roles=None,hidden_labels=None,label_offsets=None,
                width_mm=175,show_title=False,show_insets=False):
    df=validate_locations(df)
    selected=[c for c in selected_countries if c in COUNTRIES]
    if not selected: raise ValueError("Choose at least one supported country")
    geo=boundaries()
    focus=geo[geo.country.isin(selected)]
    if focus.empty: raise RuntimeError("Selected country boundaries unavailable")
    roles=roles or {}; hidden_labels=set(hidden_labels or [])
    label_offsets=label_offsets or {}
    # Width in physical mm is the controlling dimension for print typography.
    width_in=width_mm/25.4
    fig,ax=plt.subplots(figsize=(width_in,width_in*.78),layout="constrained")
    fig.patch.set_facecolor("white"); ax.set_facecolor("white")
    xmin,ymin,xmax,ymax=focus.total_bounds
    px=max((xmax-xmin)*.11,1.3); py=max((ymax-ymin)*.11,1.3)
    limits=(xmin-px,ymin-py,xmax+px,ymax+py)
    if show_context:
        nearby=geo[(~geo.country.isin(selected)) & geo.intersects(
            __import__("shapely").geometry.box(*limits))]
        if not nearby.empty:
            nearby.plot(ax=ax,color="#fafafa",edgecolor="#777777",linewidth=.5,zorder=1)
            for row in nearby.itertuples():
                # Use point on surface, not a potentially offshore centroid.
                p=row.geometry.representative_point()
                if limits[0]<p.x<limits[2] and limits[1]<p.y<limits[3]:
                    ax.text(p.x,p.y,row.country,fontsize=6.8,color="#666666",
                            ha="center",va="center",zorder=2)
    focus.plot(ax=ax,color="#ebebeb",edgecolor="#222222",linewidth=.9,zorder=3)
    ax.set_xlim(limits[0],limits[2]); ax.set_ylim(limits[1],limits[3])
    # Geographic labels are deliberately in English.
    if show_gulf and "Saudi Arabia" in selected:
        ax.text(51.6,26.8,"Gulf Sea",fontsize=7.4,fontstyle="italic",color="#555555",
                ha="center",zorder=4)
    if "Saudi Arabia" in selected:
        ax.text(38.2,23.4,"Red Sea",fontsize=7.2,fontstyle="italic",
                color="#555555",rotation=70,ha="center",zorder=4)
    shown=df[df.country.isin(selected)]
    # Fixed, short point offsets: labels cannot drift geographically.
    # Crowded sites alternate directions. Every label remains attached
    # to its own marker; no global repulsion or stray arrows.
    coords=list(shown.itertuples())
    for row in coords:
        city=str(row.city)
        role=roles.get(city,"Reference city")
        if sampled_cities and city in sampled_cities:
            role="Data collection site"
        marker,face,edge=MARKERS.get(role,MARKERS["Reference city"])
        ax.scatter(row.longitude,row.latitude,s=marker_size,marker=marker,
                   facecolor=face,edgecolor="black",linewidth=edge,zorder=6)
    # Labels are attached to actual coordinates using visible leader lines.
    presets={"Buraydah":(14,18),"Unaizah":(-14,-17),
             "Jeddah":(-17,18),"Makkah":(14,18),"Taif":(15,-17),
             "Madinah":(12,12),"Riyadh":(14,13),"Al-Kharj":(14,-15)}
    for row in coords:
        city=str(row.city)
        if not labels or city in hidden_labels:
            continue
        custom=label_offsets.get(city,(0,0))
        ox,oy=(float(custom[0]),float(custom[1])) if any(float(x)!=0 for x in custom) else presets.get(city,(12,10))
        ax.annotate(city,(row.longitude,row.latitude),
                    xytext=(ox,oy),textcoords="offset points",
                    fontsize=7.2,color="black",
                    ha="left" if ox>=0 else "right",
                    va="bottom" if oy>=0 else "top",zorder=8,
                    bbox=dict(facecolor="white",edgecolor="none",alpha=.9,pad=.5),
                    arrowprops=dict(arrowstyle="-",color="#555555",
                                    lw=.7,shrinkA=1,shrinkB=3))
    if show_insets and "Saudi Arabia" in selected:
        from mpl_toolkits.axes_grid1.inset_locator import inset_axes
        clusters=[("Qassim",(42.8,25.4,45.0,27.2),"upper left"),
                  ("Western region",(38.7,20.7,41.1,22.2),"lower right")]
        for name,(x0,y0,x1,y1),position in clusters:
            subset=shown[shown.longitude.between(x0,x1)&shown.latitude.between(y0,y1)]
            if len(subset)<2:
                continue
            ia=inset_axes(ax,width="28%",height="23%",loc=position,borderpad=1.2)
            ia.set_facecolor("white")
            ia.set_xlim(x0,x1);ia.set_ylim(y0,y1)
            ia.set_title(name,fontsize=7,pad=3)
            for r in subset.itertuples():
                role=roles.get(str(r.city),"Reference city")
                marker,face,edge=MARKERS.get(role,MARKERS["Reference city"])
                ia.scatter(r.longitude,r.latitude,s=25,marker=marker,
                           facecolor=face,edgecolor="black",linewidth=.8,zorder=3)
                if str(r.city) not in hidden_labels:
                    ia.annotate(str(r.city),(r.longitude,r.latitude),
                                xytext=(5,5),textcoords="offset points",fontsize=6)
            ia.set_xticks([]);ia.set_yticks([])
            for spine in ia.spines.values():
                spine.set_linewidth(.7);spine.set_color("#777777")
    if show_title and title: ax.set_title(title,fontsize=10.5,pad=8)
    if show_axes:
        ax.set_xlabel("Longitude (°E)",fontsize=8)
        ax.set_ylabel("Latitude (°N)",fontsize=8)
        ax.tick_params(labelsize=7)
        ax.grid(color="#dddddd",linewidth=.35,zorder=0)
    else: ax.set_axis_off()
    if show_legend and not shown.empty:
        present=[r for r in MARKERS if r in {roles.get(str(c),"Reference city") for c in shown.city}]
        handles=[Line2D([],[],marker=MARKERS[r][0],linestyle="None",markersize=6,
                        markerfacecolor=MARKERS[r][1],markeredgecolor="black",label=r)
                 for r in present]
        ax.legend(handles=handles,loc="lower center",bbox_to_anchor=(.5,-.025),ncol=min(3,len(handles)),fontsize=6.4,frameon=False,
                  facecolor="white",edgecolor="#aaaaaa")
    if show_notes:
        fig.text(.05,.01,"Natural Earth 1:110m. Points are research locations, not dialect boundaries.",
                 fontsize=6,color="#555555")
    return fig

def export_figure(fig,fmt="png",dpi=600):
    if fmt not in ("png","pdf","svg"): raise ValueError("Unsupported format")
    buf=BytesIO()
    fig.savefig(buf,format=fmt,dpi=dpi,bbox_inches="tight",facecolor="white")
    return buf.getvalue()
