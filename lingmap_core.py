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
from shapely.geometry import Point, box
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

@lru_cache(maxsize=1)
def coastline_data():
    """Natural Earth coastlines: lines only, with no political names or fills."""
    local=ROOT/"data"/"natural_earth_110m_coastline.geojson"
    url="https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_coastline.geojson"
    if not local.exists():
        try:
            with urllib.request.urlopen(url,timeout=35) as response:
                raw=response.read()
            obj=json.loads(raw)
            if obj.get("type")!="FeatureCollection" or not obj.get("features"):
                raise ValueError("Invalid coastline dataset")
            local.parent.mkdir(exist_ok=True)
            local.write_bytes(raw)
        except Exception as exc:
            raise RuntimeError("Natural Earth coastline data unavailable: "+str(exc)) from exc
    return gpd.read_file(local)

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
    fig,ax=plt.subplots(figsize=(width_in,width_in*.82))
    fig.subplots_adjust(left=.035,right=.965,top=.965,bottom=.115 if show_legend else .035)
    fig.patch.set_facecolor("white"); ax.set_facecolor("#e9edf0")
    xmin,ymin,xmax,ymax=focus.total_bounds
    px=max((xmax-xmin)*.055,.75); py=max((ymax-ymin)*.055,.75)
    # Wider Saudi extent reveals the opposite shores of both seas.
    if selected==["Saudi Arabia"]:
        xmin=min(xmin,32.0); xmax=max(xmax,58.0)
        ymin=min(ymin,15.0); ymax=max(ymax,31.0)
        px=.8; py=.8
    limits=(xmin-px,ymin-py,xmax+px,ymax+py)
    if selected==["Saudi Arabia"]:
        # Neutral land mask: white land against softly shaded water.
        # The mask adds no names, country fills or political boundaries.
        land_path=ROOT/"data"/"natural_earth_110m.geojson"
        land=gpd.read_file(land_path)
        land=land[land.intersects(box(*limits))]
        if not land.empty:
            land.plot(ax=ax,color="white",edgecolor="none",zorder=.5)
    if show_context:
        nearby=geo[(~geo.country.isin(selected)) & geo.intersects(
            __import__("shapely").geometry.box(*limits))]
        if selected==["Saudi Arabia"]:
            nearby=nearby[nearby.country.isin({"Jordan","Iraq","Kuwait","Qatar","United Arab Emirates","Oman","Yemen"})]
        if not nearby.empty:
            nearby.plot(ax=ax,color="#e3e3e3",edgecolor="#777777",linewidth=.42,zorder=1)
            anchors={"Jordan":(36.5,31.4),"Iraq":(44.5,31.2),
                     "Kuwait":(47.5,29.5),"Qatar":(51.1,25.3),
                     "United Arab Emirates":(54.5,23.5),
                     "Oman":(56.5,19.6),"Yemen":(44.4,15.8)}
            # Test the rendered text bounding box against the country geometry.
            # Small countries are left unlabeled rather than placing text at sea.
            for row in nearby.itertuples():
                p=row.geometry.representative_point()
                candidates=[anchors.get(row.country,(p.x,p.y)),(p.x,p.y)]
                for x,y in candidates:
                    if not (limits[0]+.3<x<limits[2]-.3 and limits[1]+.3<y<limits[3]-.3):
                        continue
                    label=ax.text(x,y,row.country,fontsize=6.1,color="#666666",
                                  ha="center",va="center",zorder=2,clip_on=True)
                    fig.canvas.draw()
                    bb=label.get_window_extent(fig.canvas.get_renderer())
                    corners=ax.transData.inverted().transform(
                        [[bb.x0,bb.y0],[bb.x1,bb.y0],[bb.x1,bb.y1],[bb.x0,bb.y1]])
                    if all(row.geometry.buffer(-.04).covers(Point(float(cx),float(cy)))
                           for cx,cy in corners):
                        break
                    label.remove()
    if selected==["Saudi Arabia"]:
        # Draw actual opposite shores (including Iran's Gulf coastline) using
        # unfilled Natural Earth linework. No Iran name, polygon, or shading.
        # The Red Sea's African shore is included without country labels.
        coast=coastline_data()
        view=box(*limits)
        coast=coast[coast.intersects(view)]
        if not coast.empty:
            coast.clip(view).plot(ax=ax,color="#777777",linewidth=.45,zorder=2.5)
    focus.plot(ax=ax,color="#d7d7d7",edgecolor="#333333",linewidth=.72,zorder=3)
    ax.set_xlim(limits[0],limits[2]); ax.set_ylim(limits[1],limits[3])
    # Place water names using the actual rendered text rectangle.
    # Search along the waterway, rather than silently dropping a label
    # when a few hand-picked points do not fit.
    if selected==["Saudi Arabia"]:
        sea_candidates=[("Red Sea",[(36.7,y) for y in (22.8,23.5,22.0,24.3,21.3,25.0,20.5,25.7)]
                         +[(x,y) for x in (36.3,37.0,37.3,36.0)
                           for y in (22.8,23.5,22.0,24.3,21.3,25.0)],70)]
        if show_gulf:
            sea_candidates.append(("Gulf Sea",[(51.8,27.3),(51.9,26.5),(52.4,27.5)],0))
        # All land polygons are used only to test whether text is over water.
        land_union=land.geometry.union_all()
        for name,positions,angle in sea_candidates:
            for x,y in positions:
                label=ax.text(x,y,name,fontsize=7.2,fontstyle="italic",
                              color="#4c5256",rotation=angle,ha="center",
                              va="center",zorder=4)
                fig.canvas.draw()
                bb=label.get_window_extent(fig.canvas.get_renderer())
                corners=ax.transData.inverted().transform(
                    [[bb.x0,bb.y0],[bb.x1,bb.y0],[bb.x1,bb.y1],[bb.x0,bb.y1]])
                label_area=box(float(corners[:,0].min()),float(corners[:,1].min()),
                               float(corners[:,0].max()),float(corners[:,1].max()))
                # Small clearance keeps the label visibly away from shore.
                if not land_union.intersects(label_area.buffer(.07)):
                    break
                label.remove()
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
    # Place labels using rendered pixel bounding boxes, not fixed offsets.
    # Explicit user offsets always take precedence over automatic placement.
    presets={"Buraydah":(14,18),"Unaizah":(23,-16),
             "Jeddah":(-22,22),"Makkah":(18,18),"Taif":(15,-17),
             "Madinah":(12,12),"Riyadh":(14,13),"Al-Kharj":(14,-15)}
    fig.canvas.draw()
    renderer=fig.canvas.get_renderer()
    occupied=[]
    for text_artist in ax.texts:
        occupied.append(text_artist.get_window_extent(renderer).expanded(1.05,1.15))
    marker_positions=[ax.transData.transform((r.longitude,r.latitude)) for r in coords]
    for row in coords:
        city=str(row.city)
        if not labels or city in hidden_labels:
            continue
        custom=label_offsets.get(city,(0,0))
        manual=any(float(x)!=0 for x in custom)
        preferred=tuple(map(float,custom)) if manual else presets.get(city,(12,10))
        candidates=[preferred] if manual else [
            preferred,(22,24),(-22,24),(22,-24),(-22,-24),
            (35,10),(-35,10),(35,-10),(-35,-10),
            (12,36),(-12,36),(12,-36),(-12,-36),
            (48,24),(-48,24),(48,-24),(-48,-24)]
        best=None
        for ox,oy in candidates:
            annotation=ax.annotate(city,(row.longitude,row.latitude),
                        xytext=(ox,oy),textcoords="offset points",
                        fontsize=7.2,color="black",
                        ha="left" if ox>=0 else "right",
                        va="bottom" if oy>=0 else "top",zorder=8,
                        bbox=dict(facecolor="white",edgecolor="none",alpha=.72,pad=.22),
                        arrowprops=dict(arrowstyle="-",color="#555555",
                                        lw=.7,shrinkA=1,shrinkB=3))
            fig.canvas.draw()
            rect=annotation.get_bbox_patch().get_window_extent(fig.canvas.get_renderer()).expanded(1.06,1.14)
            collisions=sum(rect.overlaps(other) for other in occupied)
            collisions+=sum(rect.contains(px,py) for px,py in marker_positions
                            if abs(px-ax.transData.transform((row.longitude,row.latitude))[0])>2
                            or abs(py-ax.transData.transform((row.longitude,row.latitude))[1])>2)
            outside=not ax.get_window_extent().contains(rect.x0,rect.y0) or not ax.get_window_extent().contains(rect.x1,rect.y1)
            score=collisions*100+int(outside)*1000+(abs(ox)+abs(oy))*.01
            if best is None or score<best[0]:
                best=(score,(ox,oy))
            annotation.remove()
            if score<1:
                break
        ox,oy=best[1]
        annotation=ax.annotate(city,(row.longitude,row.latitude),
                    xytext=(ox,oy),textcoords="offset points",
                    fontsize=7.2,color="black",
                    ha="left" if ox>=0 else "right",
                    va="bottom" if oy>=0 else "top",zorder=8,
                    bbox=dict(facecolor="white",edgecolor="none",alpha=.72,pad=.22),
                    arrowprops=dict(arrowstyle="-",color="#555555",
                                    lw=.7,shrinkA=1,shrinkB=3))
        fig.canvas.draw()
        occupied.append(annotation.get_window_extent(fig.canvas.get_renderer()).expanded(1.06,1.14))
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
        fig.legend(handles=handles,loc="lower center",bbox_to_anchor=(.5,.027),
                   ncol=min(3,len(handles)),fontsize=7,frameon=False)
    if show_notes:
        fig.text(.05,.005,"Natural Earth 1:110m. Points are research locations, not dialect boundaries.",
                 fontsize=6,color="#555555")
    return fig

def export_figure(fig,fmt="png",dpi=600):
    if fmt not in ("png","pdf","svg"): raise ValueError("Unsupported format")
    buf=BytesIO()
    fig.savefig(buf,format=fmt,dpi=dpi,bbox_inches="tight",facecolor="white")
    return buf.getvalue()
