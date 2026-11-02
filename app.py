"""LingMap v0.3 — Arabic controls, English publication figures."""
import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from lingmap_core import COUNTRIES,ROOT,SIZES,MARKERS,validate_locations,make_figure,export_figure

AR={"Saudi Arabia":"المملكة العربية السعودية","Jordan":"الأردن","Iraq":"العراق",
    "Egypt":"مصر","Morocco":"المغرب","Tunisia":"تونس","Algeria":"الجزائر"}
REGION={"Central":"الوسطى","Western":"الغربية","Eastern":"الشرقية",
        "Southern":"الجنوبية","Northern":"الشمالية"}
ROLE_AR={"Data collection site":"موقع جمع البيانات","Comparison site":"موقع مقارنة",
         "Reference city":"مدينة مرجعية"}
st.set_page_config(page_title="LingMap | الخرائط اللغوية",page_icon="🗺️",layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"]{direction:rtl;}
h1,h2,h3,p,label{text-align:right;}
/* Center Streamlit's calculation indicator over the page viewport. */
div[data-testid="stSpinner"] {
  position: fixed !important;
  inset: 0 !important;
  z-index: 99999 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  background: rgba(10, 29, 46, .36) !important;
  backdrop-filter: blur(2px);
  pointer-events: all;
}
div[data-testid="stSpinner"] > div {
  background: #10283e !important;
  color: #fff !important;
  padding: 22px 32px !important;
  border: 1px solid #3fd0e7;
  border-radius: 18px !important;
  box-shadow: 0 15px 55px rgba(0,0,0,.28);
  font-size: 1.1rem;
  text-align: center;
}
div[data-testid="stSpinner"] p { color: #fff !important; text-align: center !important; }

</style>""",unsafe_allow_html=True)
st.title("LingMap | الخرائط اللغوية")
st.caption("إنشاء خرائط أبيض وأسود للدراسات اللغوية والتجارب الصوتية")
st.info("تعليمات الموقع باللغة العربية. جميع النصوص على الخريطة المُصدّرة باللغة الإنجليزية.")
base=pd.read_csv(ROOT/"data"/"cities.csv")

def defaults():
    return dict(countries=["Saudi Arabia"],regions=["Central","Western","Eastern","Southern","Northern"],
                city_selection=[],role_map={},hidden=[],offsets={},title="",
                preset="Double column (175 mm)",dpi=600,selection_initialized=False)
if "cfg" not in st.session_state: st.session_state.cfg=defaults()
cfg=st.session_state.cfg
st.caption("اضبط جميع الخيارات أولاً، ثم اضغط «تحديث الخريطة» مرة واحدة. لن يُعاد إنشاء الخريطة عند تغيير الإعدادات.")
with st.form("lingmap_settings_form", clear_on_submit=False):
    tabs=st.tabs(["١. مواقع الدراسة","٢. تصنيف المواقع","٣. تصميم الخريطة"])
    with tabs[0]:
        cfg["countries"]=st.multiselect("اختر الدول",COUNTRIES,default=cfg["countries"],
                                         format_func=lambda x:AR[x])
        if not cfg["countries"]: st.warning("اختر دولة واحدة على الأقل"); st.stop()
        data=base[base.country.isin(cfg["countries"])].copy()
        if cfg["countries"]==["Saudi Arabia"]:
            cfg["regions"]=st.multiselect("اختر مناطق المملكة",list(REGION),default=cfg["regions"],
                                         format_func=lambda x:REGION[x])
            data=data[data.region.isin(cfg["regions"])]
        uploaded=st.file_uploader("ملف مواقع الدراسة CSV (اختياري)",type="csv")
        if uploaded is not None:
            try:
                data=validate_locations(pd.read_csv(uploaded))
                data=data[data.country.isin(cfg["countries"])]
            except (ValueError,pd.errors.ParserError) as exc:
                st.error(f"خطأ في الملف: {exc}");st.stop()
        options=data.city.astype(str).tolist()
        if not cfg.get("selection_initialized",False):
            cfg["city_selection"]=options[:8] if uploaded is None else options
            cfg["selection_initialized"]=True
        cfg["city_selection"]=[x for x in cfg["city_selection"] if x in options]
        cfg["city_selection"]=st.multiselect("المدن التي ستظهر على الخريطة",
                                            options,default=cfg["city_selection"])
        st.caption("يمكن حذف مدينة أو أكثر بإلغاء اختيارها. المواقع المحذوفة لن تظهر في الشكل.")
    with tabs[1]:
        st.markdown("**تصنيف مواقع الدراسة**")
        st.caption("● جمع البيانات | ○ مقارنة | ▲ مدينة مرجعية. الرموز تظل واضحة عند الطباعة دون ألوان.")
        role_map={}
        for city in cfg["city_selection"]:
            old=cfg["role_map"].get(city,"Reference city")
            role_map[city]=st.selectbox(city,list(MARKERS),
                                        index=list(MARKERS).index(old),
                                        format_func=lambda x:ROLE_AR[x],key="role_"+city)
        cfg["role_map"]=role_map
        cfg["hidden"]=st.multiselect("إخفاء أسماء مدن محددة (مع إبقاء العلامات)",
                                     cfg["city_selection"],
                                     default=[x for x in cfg["hidden"] if x in cfg["city_selection"]])
        with st.expander("ضبط موضع تسمية مدينة يدويًا"):
            chosen=st.selectbox("المدينة",["—"]+cfg["city_selection"])
            if chosen!="—":
                dx,dy=cfg["offsets"].get(chosen,[0,0])
                c1,c2=st.columns(2)
                with c1: dx=st.number_input("الإزاحة الأفقية (نقاط)",-100,100,int(dx),key="dx_"+chosen)
                with c2: dy=st.number_input("الإزاحة الرأسية (نقاط)",-100,100,int(dy),key="dy_"+chosen)
                cfg["offsets"][chosen]=[dx,dy]
    with tabs[2]:
        cfg["preset"]=st.selectbox("مقاس الشكل للمجلة",list(SIZES),
                                    index=list(SIZES).index(cfg["preset"]))
        custom=st.checkbox("تحديد العرض يدويًا",False)
        width=st.number_input("العرض بالمليمتر",60,350,SIZES[cfg["preset"]]) if custom else SIZES[cfg["preset"]]
        show_title=st.checkbox("طباعة عنوان داخل الشكل (غير مفضّل للمجلات)",False)
        cfg["title"]=st.text_input("عنوان الخريطة بالإنجليزية",cfg["title"])
        labels=st.checkbox("إظهار أسماء المدن",True)
        context=st.checkbox("إظهار حدود الدول المجاورة وأسمائها",True)
        gulf=st.checkbox("إظهار Gulf Sea",True)
        legend=st.checkbox("إظهار مفتاح الرموز",True)
        insets=st.checkbox("إضافة خرائط مكبرة لمناطق المدن المتقاربة",False)
        axes=st.checkbox("إظهار خطوط الطول والعرض",False)
        notes=st.checkbox("إضافة ملاحظة المصدر داخل الشكل",False)
        size=st.slider("حجم رموز المواقع",20,100,42)
        cfg["dpi"]=st.selectbox("دقة PNG", [300,600],index=[300,600].index(cfg["dpi"]))
        st.caption("الخرائط بالأبيض والأسود والرمادي، ومناسبة لإخراج PDF وSVG المتجهي.")

    submitted=st.form_submit_button("🔄 تحديث الخريطة",type="primary",use_container_width=True)
st.download_button("تنزيل نموذج CSV",base.head(4).to_csv(index=False).encode("utf-8-sig"),
                   "lingmap_template.csv","text/csv")
if submitted:
    st.session_state["render_cfg"]={
        "countries":list(cfg["countries"]),"title":cfg["title"],"labels":labels,
        "size":size,"gulf":gulf,"context":context,"legend":legend,
        "axes":axes,"notes":notes,"role_map":dict(cfg["role_map"]),
        "hidden":list(cfg["hidden"]),"offsets":dict(cfg["offsets"]),
        "width":width,"show_title":show_title,"insets":insets,"dpi":cfg["dpi"],
        "cities":list(cfg["city_selection"]),
        "data":data.copy()
    }
    st.session_state.pop("rendered_files",None)
st.subheader("معاينة الخريطة وتنزيلها")
if "render_cfg" not in st.session_state:
    st.info("لن تُنشأ الخريطة تلقائيًا. اضبط الإعدادات في الأقسام أعلاه، ثم اضغط «تحديث الخريطة».")
else:
    rendered=st.session_state["render_cfg"]
    shown=rendered["data"][rendered["data"].city.astype(str).isin(rendered["cities"])]
    try:
        if "rendered_files" not in st.session_state:
            with st.spinner("جارٍ إعداد الخريطة وتحديث المعاينة… يرجى الانتظار"):
                fig=make_figure(shown,rendered["countries"],title=rendered["title"],labels=rendered["labels"],
                                marker_size=rendered["size"],show_gulf=rendered["gulf"],show_context=rendered["context"],
                                show_legend=rendered["legend"],show_axes=rendered["axes"],show_notes=rendered["notes"],
                                roles=rendered["role_map"],hidden_labels=rendered["hidden"],
                                label_offsets=rendered["offsets"],width_mm=rendered["width"],
                                show_title=rendered["show_title"],show_insets=rendered["insets"])
                st.session_state["rendered_files"]={
                    fmt:outputs[fmt] for fmt in ("png","pdf","svg")
                }
                plt.close(fig)
        outputs=st.session_state["rendered_files"]
        left,right=st.columns([3,1])
        with left:
            st.image(outputs["png"],use_container_width=True)
        with right:
            st.subheader("تنزيل الشكل")
            for fmt,mime in [("png","image/png"),("pdf","application/pdf"),("svg","image/svg+xml")]:
                st.download_button("تنزيل "+fmt.upper(),export_figure(fig,fmt,rendered["dpi"]),
                                   "lingmap_figure."+fmt,mime=mime,use_container_width=True)
            st.download_button("حفظ إعدادات الشكل JSON",
                               json.dumps({k:v for k,v in cfg.items() if k!="selection_initialized"},
                                          ensure_ascii=False,indent=2).encode("utf-8"),
                               "lingmap_settings.json","application/json")
    except (ValueError,RuntimeError) as exc:
        st.error(f"تعذر إنشاء الخريطة: {exc}")
    with st.expander("بيانات المدن المستخدمة"):
        st.dataframe(shown,use_container_width=True)
st.divider()
with st.expander("استعادة إعدادات سابقة / إعادة الضبط"):
    setting_file=st.file_uploader("ارفع ملف الإعدادات JSON",type="json")
    if setting_file and st.button("استعادة الإعدادات"):
        try:
            restored=json.load(setting_file)
            if not isinstance(restored,dict): raise ValueError("JSON object required")
            cfg.update({k:v for k,v in restored.items() if k in defaults()})
            st.rerun()
        except (ValueError,TypeError) as exc: st.error(str(exc))
    if st.button("إعادة ضبط جميع الخيارات"):
        st.session_state.cfg=defaults()
        for key in list(st.session_state):
            if key.startswith(("role_","dx_","dy_")): del st.session_state[key]
        st.rerun()
st.caption("المصدر الجغرافي: Natural Earth 1:110m. حدود الدول تعكس بيانات المصدر ولا تُستخدم لتحديد حدود اللهجات أو الفصل في النزاعات الحدودية.")

st.markdown("""
<style>
.lingmap-footer {
  direction: rtl; text-align: center; margin-top: 2rem;
  padding: 1.3rem 1rem; border-top: 1px solid #c9d7e2;
  color: #526478; font-size: .93rem;
}
.lingmap-footer a { color: #087ea4; text-decoration: none; font-weight: 600; }
.lingmap-footer a:hover { text-decoration: underline; }
</style>
<footer class="lingmap-footer">
  <div>تطوير: <a href="https://github.com/MuhammadAlzaidi" target="_blank" rel="noopener noreferrer">د. محمد بن صويلح الزايدي</a></div>
  <div>إحدى الأدوات البحثية ضمن <a href="https://www.arabicling.com" target="_blank" rel="noopener noreferrer">منصة ظ.ai — Arabicling.com</a></div>
</footer>
""", unsafe_allow_html=True)
