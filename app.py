"""واجهة عربية، مع إخراج جميع نصوص الخرائط باللغة الإنجليزية."""
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from lingmap_core import COUNTRIES, ROOT, validate_locations, make_figure, export_figure

COUNTRY_AR = {"Saudi Arabia":"المملكة العربية السعودية","Jordan":"الأردن","Iraq":"العراق","Egypt":"مصر","Morocco":"المغرب","Tunisia":"تونس","Algeria":"الجزائر"}
REGION_AR = {"Central":"الوسطى","Western":"الغربية","Eastern":"الشرقية","Southern":"الجنوبية","Northern":"الشمالية"}

st.set_page_config(page_title="لينغ ماب | خرائط الدراسات اللغوية", page_icon="🗺️", layout="wide")
st.markdown("""<style>
[data-testid="stAppViewContainer"], [data-testid="stSidebar"] {direction:rtl;}
h1,h2,h3,p,label {text-align:right;}
</style>""", unsafe_allow_html=True)
st.title("لينغ ماب | LingMap 🗺️")
st.caption("أداة لإنشاء خرائط مواقع الدراسات اللغوية واللهجية بجودة مناسبة للنشر العلمي")
st.info("تعليمات الموقع باللغة العربية، لكن أسماء المدن والدول وجميع النصوص المطبوعة على الخرائط باللغة الإنجليزية.")
base = pd.read_csv(ROOT / "data" / "cities.csv")

with st.sidebar:
    st.header("١ · مواقع الدراسة")
    selected = st.multiselect("اختر الدول", COUNTRIES, default=["Saudi Arabia"],
                              format_func=lambda x: COUNTRY_AR.get(x,x))
    if not selected:
        st.warning("يرجى اختيار دولة واحدة على الأقل.")
        st.stop()
    candidate = base[base.country.isin(selected)]
    if selected == ["Saudi Arabia"]:
        regions = st.multiselect("مناطق المملكة",
            sorted(candidate.region.dropna().unique()),
            default=sorted(candidate.region.dropna().unique()),
            format_func=lambda x: REGION_AR.get(x,x))
        candidate = candidate[candidate.region.isin(regions)]
    cities = st.multiselect("اختر المدن", candidate.city.tolist(),
                            default=candidate.city.tolist()[:8])
    st.header("٢ · إعدادات الخريطة")
    title = st.text_input("عنوان الخريطة (بالإنجليزية)", "Linguistic research locations")
    labels = st.checkbox("إظهار أسماء المدن", value=True)
    gulf = st.checkbox("إظهار تسمية Gulf Sea", value=True)
    size = st.slider("حجم علامات المدن", 20, 130, 52)
    dpi = st.selectbox("دقة صورة PNG", [300,600], index=1)
    st.header("٣ · بيانات اختيارية")
    uploaded = st.file_uploader("ارفع ملف CSV يتضمن country, city, latitude, longitude", type="csv")
    st.download_button("تنزيل نموذج CSV", base.head(4).to_csv(index=False).encode("utf-8-sig"),
                       "lingmap_template.csv", "text/csv")

try:
    if uploaded is not None:
        data = validate_locations(pd.read_csv(uploaded))
        data = data[data.country.isin(selected)]
        if data.empty:
            st.error("لا يحتوي الملف المرفوع على مواقع تابعة للدول المختارة.")
            st.stop()
    else:
        data = candidate[candidate.city.isin(cities)]
    left, right = st.columns([3,1])
    with left:
        fig = make_figure(data, selected, title=title, labels=labels,
                          marker_size=size, show_gulf=gulf)
        st.pyplot(fig, use_container_width=True)
    with right:
        st.subheader("تنزيل الخريطة")
        for fmt, mime in [("png","image/png"),("pdf","application/pdf"),("svg","image/svg+xml")]:
            st.download_button(f"تنزيل {fmt.upper()}", export_figure(fig,fmt,dpi),
                f"lingmap_figure.{fmt}", mime=mime, use_container_width=True)
        st.caption("تُحفظ أسماء المواقع وعنوان الخريطة باللغة الإنجليزية.")
        st.caption("لا تظهر تسميات أو حدود الدول المستبعدة في خرائط المشروع.")
    plt.close(fig)
    with st.expander("عرض بيانات مواقع الدراسة"):
        st.dataframe(data, use_container_width=True)
except (ValueError, pd.errors.ParserError) as exc:
    st.error(f"تعذر إنشاء الخريطة: {exc}")
