"""
Gestor de Fixtures - Streamlit App
Autor: Mario
Descripción: Aplicación para visualizar y filtrar fixtures de torneos deportivos
             desde un archivo CSV, con filtros por fecha, equipo y fase.
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime


# --------------------------------------------------------------------------
# CONFIGURACIÓN GENERAL DE LA PÁGINA
# --------------------------------------------------------------------------
st.set_page_config(
    page_title="Gestor de Fixtures",
    page_icon="📅",
    layout="wide",
    initial_sidebar_state="expanded",
)

DATA_PATH = Path(__file__).parent / "data" / "fixtures.csv"

# Columnas obligatorias que debe tener el CSV para que la app funcione
REQUIRED_COLUMNS = {
    "fecha",
    "fase",
    "equipo_local",
    "equipo_visitante",
    "estadio",
    "hora",
}


# --------------------------------------------------------------------------
# 1. CARGA DE DATOS
# --------------------------------------------------------------------------
@st.cache_data(show_spinner="Cargando fixtures...")
def cargar_datos(ruta_csv: Path) -> pd.DataFrame:
    """
    Carga el archivo CSV de fixtures y realiza validaciones básicas.

    Args:
        ruta_csv: Ruta al archivo CSV de fixtures.

    Returns:
        DataFrame con los fixtures, con la columna 'fecha' convertida a datetime.

    Raises:
        FileNotFoundError: si el archivo no existe.
        ValueError: si el CSV no tiene las columnas esperadas o está vacío.
    """
    if not ruta_csv.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo de datos en: {ruta_csv}"
        )

    df = pd.read_csv(ruta_csv)

    if df.empty:
        raise ValueError("El archivo CSV está vacío.")

    columnas_faltantes = REQUIRED_COLUMNS - set(df.columns)
    if columnas_faltantes:
        raise ValueError(
            f"Faltan columnas obligatorias en el CSV: {', '.join(columnas_faltantes)}"
        )

    # Conversión de tipos
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")

    # Si alguna fecha no se pudo parsear, la marcamos como advertencia
    if df["fecha"].isna().any():
        st.warning(
            "⚠️ Algunas filas tienen fechas con formato inválido y fueron excluidas."
        )
        df = df.dropna(subset=["fecha"])

    df = df.sort_values("fecha").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------
# 2. FILTRADO DE DATOS
# --------------------------------------------------------------------------
def obtener_lista_equipos(df: pd.DataFrame) -> list:
    """Devuelve la lista única y ordenada de equipos (local + visitante)."""
    equipos = pd.concat([df["equipo_local"], df["equipo_visitante"]]).unique()
    return sorted(equipos.tolist())


def filtrar_fixtures(
    df: pd.DataFrame,
    rango_fechas: tuple,
    equipo: str,
    fase: str,
) -> pd.DataFrame:
    """
    Aplica filtros combinados de fecha, equipo y fase sobre el DataFrame.

    Args:
        df: DataFrame original de fixtures.
        rango_fechas: Tupla (fecha_inicio, fecha_fin) como objetos date.
        equipo: Nombre del equipo a filtrar, o "Todos".
        fase: Fase del torneo a filtrar, o "Todas".

    Returns:
        DataFrame filtrado.
    """
    df_filtrado = df.copy()

    # Filtro por rango de fechas
    if rango_fechas and len(rango_fechas) == 2:
        fecha_inicio, fecha_fin = rango_fechas
        df_filtrado = df_filtrado[
            (df_filtrado["fecha"].dt.date >= fecha_inicio)
            & (df_filtrado["fecha"].dt.date <= fecha_fin)
        ]

    # Filtro por equipo (local o visitante)
    if equipo and equipo != "Todos":
        df_filtrado = df_filtrado[
            (df_filtrado["equipo_local"] == equipo)
            | (df_filtrado["equipo_visitante"] == equipo)
        ]

    # Filtro por fase
    if fase and fase != "Todas":
        df_filtrado = df_filtrado[df_filtrado["fase"] == fase]

    return df_filtrado


# --------------------------------------------------------------------------
# 3. VISUALIZACIÓN
# --------------------------------------------------------------------------
def formatear_para_visualizacion(df: pd.DataFrame) -> pd.DataFrame:
    """
    Prepara una copia del DataFrame con formato amigable para mostrar en pantalla.
    """
    df_vista = df.copy()
    df_vista["fecha"] = df_vista["fecha"].dt.strftime("%d/%m/%Y")
    df_vista["Partido"] = (
        df_vista["equipo_local"] + "  vs  " + df_vista["equipo_visitante"]
    )

    columnas_orden = ["fecha", "hora", "fase", "Partido", "estadio"]
    df_vista = df_vista[columnas_orden]

    df_vista.columns = ["Fecha", "Hora", "Fase", "Partido", "Estadio"]
    return df_vista


def mostrar_tabla(df_vista: pd.DataFrame) -> None:
    """Renderiza la tabla de fixtures con formato profesional."""
    if df_vista.empty:
        st.info("No se encontraron fixtures con los filtros seleccionados.")
        return

    st.dataframe(
        df_vista,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Fecha": st.column_config.TextColumn("📅 Fecha", width="small"),
            "Hora": st.column_config.TextColumn("🕐 Hora", width="small"),
            "Fase": st.column_config.TextColumn("🏆 Fase", width="medium"),
            "Partido": st.column_config.TextColumn("⚽ Partido", width="large"),
            "Estadio": st.column_config.TextColumn("📍 Estadio", width="medium"),
        },
    )


def mostrar_metricas(df_filtrado: pd.DataFrame, df_total: pd.DataFrame) -> None:
    """Muestra métricas resumen en la parte superior del dashboard."""
    col1, col2, col3 = st.columns(3)
    col1.metric("Fixtures mostrados", len(df_filtrado))
    col2.metric("Total en base de datos", len(df_total))
    col3.metric("Fases disponibles", df_total["fase"].nunique())


# --------------------------------------------------------------------------
# 4. INTERFAZ PRINCIPAL (SIDEBAR + CUERPO)
# --------------------------------------------------------------------------
def construir_sidebar(df: pd.DataFrame):
    """Construye los controles de filtro en la barra lateral."""
    st.sidebar.header("🔍 Filtros")

    fecha_min = df["fecha"].min().date()
    fecha_max = df["fecha"].max().date()

    rango_fechas = st.sidebar.date_input(
        "Rango de fechas",
        value=(fecha_min, fecha_max),
        min_value=fecha_min,
        max_value=fecha_max,
    )

    equipos = ["Todos"] + obtener_lista_equipos(df)
    equipo_sel = st.sidebar.selectbox("Equipo", equipos)

    fases = ["Todas"] + sorted(df["fase"].unique().tolist())
    fase_sel = st.sidebar.selectbox("Fase del torneo", fases)

    st.sidebar.divider()
    st.sidebar.caption(
        f"Última actualización de datos: "
        f"{datetime.fromtimestamp(DATA_PATH.stat().st_mtime).strftime('%d/%m/%Y %H:%M')}"
    )

    return rango_fechas, equipo_sel, fase_sel


def main() -> None:
    st.title("📅 Gestor de Fixtures")
    st.caption("Visualizá y filtrá los partidos del torneo en tiempo real.")

    # Carga de datos con manejo de errores
    try:
        df = cargar_datos(DATA_PATH)
    except FileNotFoundError:
        st.error(
            "❌ No se encontró el archivo de datos `fixtures.csv`. "
            "Verificá que exista en la carpeta `/data` del repositorio."
        )
        st.stop()
    except ValueError as e:
        st.error(f"❌ Error en el formato del archivo de datos: {e}")
        st.stop()
    except Exception as e:
        st.error(f"❌ Ocurrió un error inesperado al cargar los datos: {e}")
        st.stop()

    # Filtros en sidebar
    rango_fechas, equipo_sel, fase_sel = construir_sidebar(df)

    # Si el usuario solo eligió una fecha (todavía no completó el rango), usamos todo el rango
    if isinstance(rango_fechas, tuple) and len(rango_fechas) == 1:
        rango_fechas = (rango_fechas[0], rango_fechas[0])

    df_filtrado = filtrar_fixtures(df, rango_fechas, equipo_sel, fase_sel)

    mostrar_metricas(df_filtrado, df)
    st.divider()

    df_vista = formatear_para_visualizacion(df_filtrado)
    mostrar_tabla(df_vista)

    # Botón de descarga del resultado filtrado
    if not df_filtrado.empty:
        csv_descarga = df_vista.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="⬇️ Descargar fixtures filtrados (CSV)",
            data=csv_descarga,
            file_name="fixtures_filtrados.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
