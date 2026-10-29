import re
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(
    page_title="Conciliador de Retenciones - Coopagro", layout="wide"
)

st.title("🤝 Conciliador Automático de Facturas y Retenciones")
st.markdown(
    "Subí el PDF de Coopagro para extraer los comprobantes y detectar retenciones faltantes."
)

st.sidebar.header("Carga de Archivo")
pdf_subido = st.sidebar.file_uploader(
    "Subir PDF del Resumen de Cuenta", type=["pdf"]
)


def procesar_pdf_coopagro(archivo_pdf):
  filas_totales = []
  with pdfplumber.open(archivo_pdf) as pdf:
    for pagina in pdf.pages:
      tablas = pagina.extract_tables()
      for tabla in tablas:
        for fila in tabla:
          # Limpiar espacios en blanco
          fila_limpia = [c.strip() if c else "" for c in fila]
          if any(fila_limpia):
            filas_totales.append(fila_limpia)
  return filas_totales


if pdf_subido is not None:
  datos_brutos = procesar_pdf_coopagro(pdf_subido)

  if datos_brutos:
    # Buscamos en qué fila están los nombres de las columnas reales
    idx_encabezado = -1
    for i, fila in enumerate(datos_brutos):
      fila_texto = " ".join(fila)
      if "Tipo Comprobante" in fila_texto or "Nro. Comprobante" in fila_texto:
        idx_encabezado = i
        break

    if idx_encabezado != -1:
      headers = datos_brutos[idx_encabezado]
      filas_datos = datos_brutos[idx_encabezado + 1 :]

      # Normalizar la longitud de las filas para que coincidan con los headers
      filas_normalizadas = []
      for f in filas_datos:
        if len(f) < len(headers):
          f.extend([""] * (len(headers) - len(f)))
        elif len(f) > len(headers):
          f = f[: len(headers)]
        filas_normalizadas.append(f)

      df = pd.DataFrame(filas_normalizadas, columns=headers)

      # Limpiar columnas vacías o con saltos de línea en los nombres
      df = df.loc[:, df.columns != ""]
      df.columns = [c.replace("\n", " ").strip() for c in df.columns]

      st.success("¡Datos estructurados con éxito desde el PDF!")

      with st.expander("🔍 Ver tabla limpia detectada"):
        st.dataframe(df.head(15), use_container_width=True)

      # Filtrar columnas clave (buscando nombres aproximados)
      col_tipo = next(
          (c for c in df.columns if "Tipo Comprobante" in c), df.columns[2]
      )
      col_nro = next(
          (c for c in df.columns if "Nro." in c or "Comprobante" in c),
          df.columns[3],
      )
      col_detalle = next((c for c in df.columns if "Detalle" in c), df.columns[4])
      col_debe = next((c for c in df.columns if "Debe" in c), df.columns[5])
      col_haber = next((c for c in df.columns if "Haber" in c), df.columns[6])

      # Separar Facturas y Retenciones
      facturas = df[
          df[col_tipo].str.contains("Factura", case=False, na=False)
      ].copy()
      retenciones = df[
          df[col_tipo].str.contains("Retención|Retencion", case=False, na=False)
      ].copy()

      st.subheader("📊 Diagnóstico de Retenciones por Factura")

      reporte = []

      for _, fac in facturas.iterrows():
        nro_factura_completo = str(fac[col_nro])
        # Extraer número corto (ej: 38 de 0079-00000038)
        match_nro = re.search(r"0079-(\d+)", nro_factura_completo)
        if not match_nro:
          continue

        nro_corto = str(int(match_nro.group(1)))  # quita ceros a la izquierda

        # Buscar retenciones asociadas en el campo detalle (ej: "79-38" o "79- 38")
        suss_total = 0
        iva_total = 0

        for _, ret in retenciones.iterrows():
          det_ret = str(ret[col_detalle])
          if nro_corto in det_ret:
            # Parsear monto de haber o debe según corresponda
            monto_str = (
                str(ret[col_haber])
                if str(ret[col_haber]) not in ["", "0", "0.00"]
                else str(ret[col_debe])
            )
            monto_str = (
                monto_str.replace(".", "")
                .replace(",", ".")
                .replace("-", "")
            )
            try:
              monto = float(monto_str)
            except ValueError:
              monto = 0.0

            if "SUSS" in ret[col_tipo] or "S.U.S.S" in det_ret:
              suss_total += monto
            elif "IVA" in ret[col_tipo] or "IVA" in det_ret:
              iva_total += monto

        total_ret = suss_total + iva_total
        estado = (
            "⚠️ Falta Retención" if total_ret == 0 else "✅ Retenciones OK"
        )

        reporte.append({
            "Factura": nro_factura_completo,
            "Detalle / Producto": str(fac[col_detalle]),
            "Retención S.U.S.S. ($)": suss_total,
            "Retención IVA ($)": iva_total,
            "Total Retenciones ($)": total_ret,
            "Estado": estado,
        })

      if reporte:
        df_reporte = pd.DataFrame(reporte)

        col1, col2 = st.columns(2)
        col1.metric("Total Facturas Analizadas", len(df_reporte))
        col2.metric(
            "Facturas sin Retenciones",
            len(df_reporte[df_reporte["Total Retenciones ($)"] == 0]),
        )

        st.dataframe(df_reporte, use_container_width=True)

        # Botón de descarga
        csv = df_reporte.to_csv(index=False).encode("utf-8")
        st.download_button(
            "📥 Descargar Reporte de Control",
            csv,
            "control_retenciones.csv",
            "text/csv",
        )
      else:
        st.warning(
            "No se pudieron matchear facturas con retenciones. Verificá que"
            " el PDF contenga ambas en el período seleccionado."
        )

    else:
      st.error(
          "No se encontró la cabecera de la tabla en el PDF. Asegurate de que"
          " sea el reporte completo de cuenta corriente."
      )
  else:
    st.warning("El archivo PDF está vacío.")
else:
  st.info("👈 Subí tu archivo PDF en la barra lateral para comenzar.")
