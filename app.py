import streamlit as st
import pandas as pd
import requests
import numpy as np
import matplotlib.pyplot as plt

st.set_page_config(
    page_title="Consultor Agroforestal Chota",
    page_icon="🌱",
    layout="wide"
)

st.title("🌱 Plataforma Inteligente Agroforestal - Chota")
st.markdown(
    "Sistema de consulta agroclimática basado en datos de **NASA POWER** "
    "para evaluar la aptitud de especies forestales y agroforestales."
)

especies = {
    "Tara (Nativa)": {"t_min": 14, "t_max": 22, "h_min": 40, "h_max": 70, "lluvia_min": 300, "lluvia_max": 800},
    "Aliso (Nativa)": {"t_min": 10, "t_max": 18, "h_min": 60, "h_max": 90, "lluvia_min": 700, "lluvia_max": 1500},
    "Sauco (Nativa)": {"t_min": 7, "t_max": 20, "h_min": 50, "h_max": 85, "lluvia_min": 600, "lluvia_max": 1200},
    "Quinual (Nativa)": {"t_min": 4, "t_max": 12, "h_min": 60, "h_max": 95, "lluvia_min": 600, "lluvia_max": 1400},
    "Pino Patula (Exótica)": {"t_min": 12, "t_max": 18, "h_min": 50, "h_max": 80, "lluvia_min": 700, "lluvia_max": 1800},
    "Eucalipto (Exótica)": {"t_min": 10, "t_max": 20, "h_min": 50, "h_max": 85, "lluvia_min": 500, "lluvia_max": 1500},
}

st.sidebar.header("⚙️ Parámetros de consulta")

seleccion = st.sidebar.selectbox("Seleccione especie:", list(especies.keys()))
p = especies[seleccion]

latitud = st.sidebar.number_input("Latitud", value=-6.56, format="%.4f")
longitud = st.sidebar.number_input("Longitud", value=-78.65, format="%.4f")
anio = st.sidebar.selectbox("Año de análisis", [2024, 2023, 2022, 2021, 2020])

fecha_inicio = f"{anio}0101"
fecha_fin = f"{anio}1231"


@st.cache_data(ttl=3600)
def cargar_datos(lat, lon, inicio, fin):
    url = (
        "https://power.larc.nasa.gov/api/temporal/daily/point"
        f"?parameters=T2M_MAX,T2M_MIN,T2M,RH2M,PRECTOTCORR"
        f"&community=AG"
        f"&longitude={lon}"
        f"&latitude={lat}"
        f"&start={inicio}"
        f"&end={fin}"
        f"&format=JSON"
    )

    response = requests.get(url, timeout=40)
    response.raise_for_status()

    data = response.json()
    parametros = data["properties"]["parameter"]

    df = pd.DataFrame(parametros)
    df.index = pd.to_datetime(df.index, format="%Y%m%d")
    df = df.replace(-999, np.nan)

    return df


def calcular_aptitud(valor, minimo, maximo):
    if pd.isna(valor):
        return 0
    if minimo <= valor <= maximo:
        return 100
    if valor < minimo:
        return max(0, (valor / minimo) * 100)
    return max(0, 100 - ((valor - maximo) / maximo * 100))


try:
    with st.spinner("Consultando datos climáticos NASA POWER..."):
        df = cargar_datos(latitud, longitud, fecha_inicio, fecha_fin)

    temp_prom = df["T2M"].mean()
    humedad_prom = df["RH2M"].mean()
    lluvia_total = df["PRECTOTCORR"].sum()

    apt_temp = calcular_aptitud(temp_prom, p["t_min"], p["t_max"])
    apt_humedad = calcular_aptitud(humedad_prom, p["h_min"], p["h_max"])
    apt_lluvia = calcular_aptitud(lluvia_total, p["lluvia_min"], p["lluvia_max"])

    apt_general = (apt_temp * 0.40) + (apt_humedad * 0.30) + (apt_lluvia * 0.30)

    st.subheader(f"🌳 Evaluación para: {seleccion}")

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aptitud general", f"{apt_general:.1f}%")
    col2.metric("Temperatura promedio", f"{temp_prom:.1f} °C")
    col3.metric("Humedad promedio", f"{humedad_prom:.1f}%")
    col4.metric("Lluvia anual", f"{lluvia_total:.1f} mm")

    if apt_general >= 80:
        st.success("✅ Alta aptitud agroclimática para la especie seleccionada.")
    elif apt_general >= 60:
        st.warning("🟡 Aptitud media. Se recomienda validar suelo, altitud, pendiente y manejo hídrico.")
    else:
        st.error("🔴 Baja aptitud agroclimática. La especie presenta limitaciones climáticas relevantes.")

    st.info(
        f"""
        **Rango óptimo de la especie seleccionada:**

        - Temperatura: {p["t_min"]} °C a {p["t_max"]} °C  
        - Humedad relativa: {p["h_min"]}% a {p["h_max"]}%  
        - Precipitación anual: {p["lluvia_min"]} mm a {p["lluvia_max"]} mm
        """
    )

    st.subheader("📈 Temperatura diaria")
    fig, ax = plt.subplots(figsize=(12, 4))
    ax.plot(df.index, df["T2M"], label="Temperatura media diaria")
    ax.axhspan(p["t_min"], p["t_max"], alpha=0.2, label="Rango térmico óptimo")
    ax.set_ylabel("Temperatura °C")
    ax.set_xlabel("Fecha")
    ax.legend()
    ax.grid(alpha=0.3)
    st.pyplot(fig)

    st.subheader("💧 Humedad relativa diaria")
    fig2, ax2 = plt.subplots(figsize=(12, 4))
    ax2.plot(df.index, df["RH2M"], label="Humedad relativa diaria")
    ax2.axhspan(p["h_min"], p["h_max"], alpha=0.2, label="Rango óptimo de humedad")
    ax2.set_ylabel("Humedad relativa %")
    ax2.set_xlabel("Fecha")
    ax2.legend()
    ax2.grid(alpha=0.3)
    st.pyplot(fig2)

    st.subheader("🌧️ Precipitación mensual")
    lluvia_mensual = df["PRECTOTCORR"].resample("ME").sum()

    fig3, ax3 = plt.subplots(figsize=(12, 4))
    ax3.bar(lluvia_mensual.index.strftime("%b"), lluvia_mensual.values)
    ax3.set_ylabel("Precipitación mm")
    ax3.set_xlabel("Mes")
    ax3.grid(alpha=0.3)
    st.pyplot(fig3)

    st.subheader("🏆 Ranking de especies recomendadas")

    ranking = []
    for nombre, esp in especies.items():
        r_temp = calcular_aptitud(temp_prom, esp["t_min"], esp["t_max"])
        r_hum = calcular_aptitud(humedad_prom, esp["h_min"], esp["h_max"])
        r_lluvia = calcular_aptitud(lluvia_total, esp["lluvia_min"], esp["lluvia_max"])
        r_total = (r_temp * 0.40) + (r_hum * 0.30) + (r_lluvia * 0.30)

        ranking.append({
            "Especie": nombre,
            "Aptitud general (%)": round(r_total, 1),
            "Aptitud temperatura (%)": round(r_temp, 1),
            "Aptitud humedad (%)": round(r_hum, 1),
            "Aptitud lluvia (%)": round(r_lluvia, 1),
        })

    ranking_df = pd.DataFrame(ranking).sort_values("Aptitud general (%)", ascending=False)
    st.dataframe(ranking_df, use_container_width=True)

    csv = ranking_df.to_csv(index=False).encode("utf-8")

    st.download_button(
        label="📥 Descargar ranking en CSV",
        data=csv,
        file_name="ranking_agroforestal_chota.csv",
        mime="text/csv",
    )

    with st.expander("Ver datos climáticos diarios NASA POWER"):
        st.dataframe(df, use_container_width=True)

except requests.exceptions.RequestException as e:
    st.error(f"Error de conexión con NASA POWER: {e}")

except KeyError:
    st.error("La API no devolvió los parámetros esperados. Revise coordenadas, fechas o disponibilidad de datos.")

except Exception as e:
    st.error(f"Error inesperado: {e}")
