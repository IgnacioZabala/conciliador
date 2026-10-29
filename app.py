import re
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(
    page_title="Conciliador de Retenciones - Coopagro", layout="wide"
)

st.title("🤝 Conciliador de Cuentas Corrientes & Retenciones (PDF)")
st.markdown(
    "Subí el reporte en formato **PDF** exportado de Coopagro para detectar automáticamente facturas y sus retenciones asociadas."
)

st.sidebar.header("Carga de Archivo PDF")
pdf_subido = st.sidebar.file_uploader(
    "Subir PDF del Resumen de Cuenta", type=["pdf"]
)


def extraer_datos_pdf(archivo_pdf):
    filas_extraidas = []
    with pdfplumber.open(archivo_pdf) as pdf:
        for pagina in pdf.pages:
            tablas = pagina.extract_tables()
            for tabla in tablas:
                for fila in tabla:
                    # Limpiamos valores vacíos o nulos de la fila extraída
                    fila_limpia = [
                        celda.strip() if celda else "" for celda in fila
                    ]
                    if any(fila_limpia):
                        filas_extraidas.append(fila_limpia)
    return filas_extraidas


if pdf_subido is not None:
    st.success("¡PDF cargado correctamente!")

    # Extraer datos tabulares del PDF
    datos_brutos = extraer_datos_pdf(pdf_subido)

    if datos_brutos:
        df = pd.DataFrame(datos_brutos)

        with st.expander("🔍 Ver datos extraídos en bruto del PDF"):
            st.dataframe(df.head(15))

        st.info(
            "💡 El sistema procesará el texto y buscará las relaciones entre las facturas (ej. 79-38) y sus retenciones de IVA y S.U.S.S."
        )

        # Aquí puedes continuar con la lógica de filtrado y mapeo automático
        # buscando las columnas que contengan "Factura", "Retención", etc.

    else:
        st.warning(
            "No se pudieron extraer tablas legibles de este PDF. Verificá que sea el reporte directo del sistema."
        )

else:
    st.markdown(
        """
    ### Instrucciones:
    1. Descargá el resumen de cuenta en formato **PDF** desde el sistema de la Cooperativa Agropecuaria de Tandil.
    2. Subilo usando el selector de la izquierda.
    3. El sistema leerá las filas y te permitirá conciliar los pagos automáticamente.
    """
    )
