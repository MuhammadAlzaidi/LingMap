"""Arabic user interface; English-only research figure labels."""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from lingmap_core import COUNTRIES, ROOT, validate_locations, make_figure, export_figure

COUNTRY_AR={"Saudi Arabia":"المملكة العربية السعودية","Jordan":"الأردن","Iraq":"العراق","Egypt":"مصر","Morocco":"المغرب","Tunisia":"تونس","Algeria":"الجزائر"}
REGION_AR={"Central":"الوسطى","Western":"الغربية","Eastern":"الشرقية","Southern":"الجنوبية","Northern":"الشمالية"}
st.set_page_config(page_title="LingMap | خرائط الدراسات اللغوية",page_icon="🗺️",layout="wide")
st.markdown("""<style>[data-testid="stAppViewContainer"],[data-testid="stSidebar"]{direction:rtl;}h1,h2,h3,p,label{text-align:right;}</style>""",unsafe_allow_html=True)
st.title("لينغ ماب | LingMap 🗺️")
st.caption("خرائط بالأبيض والأسود لمواقع الدراسات اللغوية والتجارب الصوتية")
st.info("تعليمات الاستخدام بالعربية، بينما تبقى جميع التسميات المطبوعة على الخرائط باللغة الإنجليزية.")
base=pd.read_csv(ROOT/"data"/"cities.csv")
with st.sidebar:
    st.header("١ · تحديد مواقع الدراسة")
    selected=st.multiselect("الدول",COUNTRIES,default=["Saudi Arabia"],
                            format_func=lambda x:COUNTRY_AR.get(x,x))
    if not selected: st.warning("اختر دولة واحدة على الأقل"); st.stop()
    candidate=base[base.country.isin(selected)]
    if selected==["Saudi Arabia"]:
        regions=st.multiselect("مناطق المملكة",
             sorted(candidate.region.dropna().unique()),
             default=sorted(candidate.region.dropna().unique()),
             format_func=lambda x:REGION_AR.get(x,x))
        candidate=candidate[candidate.region.isin(regions)]
    uploaded=st.file_uploader("ملف مواقع الدراسة (CSV) — اختياري",type="csv")
    st.download_button("تنزيل نموذج CSV",base.head(4).to_csv(index=False).encode("utf-8-sig"),
                       "lingmap_template.csv","text/csv")
    if uploaded is not None:
        try:
            candidate=validate_locations(pd.read_csv(uploaded))
            candidate=candidate[candidate.country.isin(selected)]
        except (ValueError,pd.errors.ParserError) as exc:
            st.error(str(exc)); st.stop()
    options=candidate.city.astype(str).tolist()
    st.markdown("**المدن الظاهرة على الخريطة**")
    cities=st.multiselect("ألغِ اختيار أي مدينة لحذفها من الخريطة",options,
                          default=options[:8] if uploaded is None else options)
    st.markdown("**مواقع جمع البيانات / المشاركين**")
    sampled=st.multiselect("حدد المدن التي ستظهر بدوائر سوداء ممتلئة",cities,
                           default=cities[:1])
    st.caption("الدوائر السوداء الممتلئة = مواقع الدراسة؛ الدوائر الفارغة = مدن مرجعية.")
    st.header("٢ · إعدادات الشكل العلمي")
    title=st.text_input("عنوان الخريطة بالإنجليزية","Linguistic research locations")
    labels=st.checkbox("إظهار أسماء المدن",True)
    context=st.checkbox("إظهار أسماء الدول المجاورة للتموضع الجغرافي",True)
    gulf=st.checkbox("إظهار Gulf Sea",True)
    legend=st.checkbox("إظهار مفتاح مواقع الدراسة",True)
    axes=st.checkbox("إظهار خطوط الطول والعرض",False)
    notes=st.checkbox("إظهار ملاحظة علمية أسفل الشكل",False)
    size=st.slider("حجم علامات المواقع",20,120,45)
    dpi=st.selectbox("دقة PNG", [300,600],index=1)
    st.caption("تُرسم الخرائط بدرجات الأسود والأبيض والرمادي لتناسب الطباعة الأكاديمية.")
data=candidate[candidate.city.astype(str).isin(cities)]
try:
    fig=make_figure(data,selected,title=title,labels=labels,marker_size=size,
                    show_gulf=gulf,sampled_cities=sampled,show_context=context,
                    show_legend=legend,show_axes=axes,show_notes=notes)
    main,side=st.columns([3,1])
    with main:
        st.pyplot(fig,use_container_width=True)
    with side:
        st.subheader("تنزيل الشكل")
        for fmt,mime in [("png","image/png"),("pdf","application/pdf"),("svg","image/svg+xml")]:
            st.download_button(f"تنزيل {fmt.upper()}",export_figure(fig,fmt,dpi),
                               f"lingmap_figure.{fmt}",mime=mime,use_container_width=True)
        st.caption("تُستخدم حدود جغرافية مبسطة؛ لا تصلح لتحليل الحدود السياسية أو خطوط الساحل الدقيقة.")
        st.caption("تُعرض أسماء الدول المجاورة للسياق فقط، دون إظهار حدود الدول المستبعدة.")
    plt.close(fig)
    with st.expander("البيانات المختارة"):
        st.dataframe(data,use_container_width=True)
except ValueError as exc:
    st.error(f"تعذر إنشاء الخريطة: {exc}")
