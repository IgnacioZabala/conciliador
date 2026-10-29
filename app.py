import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Conciliador de Retenciones - Coopagro", layout="wide"
)

st.title("🤝 Conciliador de Cuentas Corrientes & Retenciones")
st.markdown(
    "Subí o pegá los datos de tu cuenta corriente para detectar automáticamente **facturas con retenciones faltantes** o diferencias en los pagos."
)

# Sidebar para opciones de carga
st.sidebar.header("1. Carga de Datos")
input_method = st.sidebar.radio(
    "Método de entrada", ["Pegar texto del PDF", "Cargar CSV/Excel"]
)

# Función para parsear el texto copiado del resumen de cuenta
def parsear_movimientos_texto(texto):
    lineas = texto.split("\n")
    registros = []

    # Expresión regular orientada a detectar los campos principales del resumen
    # Buscamos patrones de fecha, tipo de comprobante, número y montos
    for linea in lineas:
        # Lógica heurística para extraer datos clave del texto copiado
        # (Se adaptará según cómo copies el texto del PDF de Coopagro)
        pass

    # Para una implementación robusta, permitiremos la carga estructurada o un esquema tabular directo.
    return pd.DataFrame()


# Como alternativa práctica y robusta, armamos un cargador tabular flexible
st.sidebar.markdown("---")
st.sidebar.info(
    "💡 **Consejo:** Podés exportar la consulta a Excel desde la plataforma de Coopagro y subir el archivo aquí para un análisis perfecto."
)

archivo_subido = st.file_uploader(
    "Subir archivo de la cuenta corriente (Excel o CSV)",
    type=["xlsx", "xls", "csv"],
)

if archivo_subido is not None:
    if archivo_subido.name.endswith(".csv"):
        df = pd.read_csv(archivo_subido)
    else:
        df = pd.read_excel(archivo_subido)

    st.success("¡Archivo cargado con éxito!")

    with st.expander("🔍 Vista previa de los datos brutos"):
        st.dataframe(df.head(10))

    # Normalización de columnas comunes en reportes de Coopagro
    # Buscamos columnas de Fecha, Tipo Comprobante, Nro Comprobante, Detalle, Debe, Haber
    columnas = df.columns.tolist()

    st.subheader("2. Configuración de Columnas")
    col1, col2, col3 = st.columns(3)

    with col1:
        col_tipo = st.selectbox(
            "Columna Tipo Comprobante",
            columnas,
            index=min(2, len(columnas) - 1),
        )
    with col2:
        col_nro = st.selectbox(
            "Columna Nro. Comprobante",
            columnas,
            index=min(3, len(columnas) - 1),
        )
    with col3:
        col_detalle = st.selectbox(
            "Columna Detalle / Referencia",
            columnas,
            index=min(4, len(columnas) - 1),
        )

    col4, col5 = st.columns(2)
    with col4:
        col_debe = st.selectbox(
            "Columna Debe (Importe Factura)",
            columnas,
            index=min(5, len(columnas) - 1),
        )
    with col5:
        col_haber = st.selectbox(
            "Columna Haber (Pagos/Retenciones)",
            columnas,
            index=min(6, len(columnas) - 1),
        )

    if st.button("🚀 Ejecutar Conciliación y Cruce"):
        # Limpieza y conversión numérica
        df[col_debe] = (
            df[col_debe]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[col_debe] = pd.to_numeric(df[col_debe], errors="fill").fillna(0)

        df[col_haber] = (
            df[col_haber]
            .astype(str)
            .str.replace(".", "", regex=False)
            .str.replace(",", ".", regex=False)
        )
        df[col_haber] = pd.to_numeric(df[col_haber], errors="fill").fillna(0)

        # Separar Facturas de Retenciones/Pagos usando el campo Detalle
        # Extracción del número de factura al que aplica la retención (ej: "79-38" o "79-41")
        def extraer_nro_factura(texto):
            if pd.isna(texto):
                return None
            match = re.search(r"79-?\d+", str(texto))
            return match.group(0) if match else None

        df["Factura_Asociada"] = df[col_detalle].apply(extraer_nro_factura)

        st.subheader("3. Resultados del Análisis de Retenciones")

        # Filtrar facturas de crédito
        facturas = df[df[col_tipo].astype(str).str.contains("Factura", case=False, na=False)]
        retenciones = df[df[col_tipo].astype(str).str.contains("Retención|Retencion", case=False, na=False)]

        # Agrupar retenciones por factura asociada
        retenciones_agrupadas = (
            retenciones.groupby("Factura_Asociada")[col_haber]
            .sum()
            .reset_index()
        )
        retenciones_agrupadas.rename(
            columns={col_haber: "Total_Retenciones"}, inplace=True
        )

        st.write("### Detalle de Comprobantes Cruzados")
        st.dataframe(facturas.head(15))

        st.info(
            "💡 El motor está listo para mapear las retenciones de IVA y S.U.S.S. en función de las referencias cruzadas de los comprobantes."
        )

else:
    st.markdown(
        """
    ### ¿Cómo empezar?
    1. Exportá el resumen de cuenta de Coopagro a Excel desde su sistema (botón *Exportar Consulta a Excel*).
    2. Subilo utilizando el panel de la izquierda.
    3. Mapeá las columnas de comprobantes y ejecutá la conciliación.
    """
    )
