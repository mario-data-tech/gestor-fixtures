import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

# --------------------------------------------------------------------------
# CONFIGURACIÓN
# --------------------------------------------------------------------------
st.set_page_config(page_title="Gestor de Fixtures", page_icon="📅", layout="wide")
DATA_PATH = Path(__file__).parent / "data" / "fixtures.csv"
REQUIRED_COLUMNS = {"fecha", "fase", "equipo_local", "equipo_visitante", "estadio", "hora"}

# --------------------------------------------------------------------------
# LÓGICA Y DATOS
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando...")
def cargar_datos(ruta_csv: Path) -> pd.DataFrame:
    if not ruta_csv.exists(): raise FileNotFoundError("Archivo no encontrado")
    df = pd.read_csv(ruta_csv)
    if df.empty: raise ValueError("CSV vacío")
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    df = df.dropna(subset=["fecha"]).sort_values("fecha").reset_index(drop=True)
    return df

def determinar_estado(fecha_partido):
    hoy = datetime.now().date()
    f_dt = fecha_partido.date()
    if f_dt < hoy: return "Finalizado"
    if f_dt == hoy: return "En juego"
    return "Pendiente"

def filtrar_fixtures(df, rango_fechas, equipo, fase, busqueda):
    df_f = df.copy()
    if rango_fechas and len(rango_fechas) == 2:
        df_f = df_f[(df_f["fecha"].dt.date >= rango_fechas[0]) & (df_f["fecha"].dt.date <= rango_fechas[1])]
    if equipo != "Todos":
        df_f = df_f[(df_f["equipo_local"] == equipo) | (df_f["equipo_visitante"] == equipo)]
    if fase != "Todas":
        df_f = df_f[df_f["fase"] == fase]
    if busqueda:
        df_f = df_f[df_f['equipo_local'].str.contains(busqueda, case=False) | df_f['equipo_visitante'].str.contains(busqueda, case=False)]
    return df_f

# --------------------------------------------------------------------------
# VISUALIZACIÓN
# --------------------------------------------------------------------------
def mostrar_metricas(df_filtrado, df_total):
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Partidos", len(df_total))
    c2.metric("En Pantalla", len(df_filtrado))
    c3.metric("Fases", df_total["fase"].nunique())
    c4.metric("Actualización", "Reciente")

def mostrar_tabla(df):
    df_v = df.copy()
    df_v["Estado"] = df_v["fecha"].apply(determinar_estado)
    df_v["Partido"] = df_v["equipo_local"] + " vs " + df_v["equipo_visitante"]
    df_v = df_v[["fecha", "hora", "Estado", "Partido", "fase", "estadio"]]
    df_v.columns = ["Fecha", "Hora", "Estado", "Partido", "Fase", "Estadio"]
    df_v["Fecha"] = df_v["Fecha"].dt.strftime("%d/%m/%Y")
    
    st.dataframe(df_v, width='stretch', hide_index=True, column_config={
        "Estado": st.column_config.SelectboxColumn("Estado", options=["Finalizado", "En juego", "Pendiente"])
    })

def main():
    st.title("📅 Gestor de Fixtures Pro")
    try:
        df = cargar_datos(DATA_PATH)
    except Exception as e:
        st.error(f"Error: {e}"); st.stop()

    # Sidebar
    st.sidebar.header("🔍 Filtros")
    busqueda = st.sidebar.text_input("🔍 Buscar equipo")
    rango = st.sidebar.date_input("Rango de fechas", (df["fecha"].min().date(), df["fecha"].max().date()))
    equipo_sel = st.sidebar.selectbox("Equipo", ["Todos"] + sorted(list(set(df["equipo_local"])|set(df["equipo_visitante"]))))
    fase_sel = st.sidebar.selectbox("Fase", ["Todas"] + sorted(df["fase"].unique().tolist()))

    # Lógica principal
    df_filtrado = filtrar_fixtures(df, rango, equipo_sel, fase_sel, busqueda)
    mostrar_metricas(df_filtrado, df)
    st.divider()
    mostrar_tabla(df_filtrado)
    
    if not df_filtrado.empty:
        csv = df_filtrado.to_csv(index=False).encode('utf-8')
        st.download_button("⬇️ Descargar CSV", csv, "fixtures.csv", "text/csv")

if __name__ == "__main__":
    main()
