import re
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Conciliador de Retenciones - Coopagro", layout="wide"
)

st.title("🤝 Conciliador Automático de Facturas y Retenciones (Excel / HTML)")
st.markdown(
    "Subí el archivo exportado desde el sistema de Coopagro para detectar de"
    " forma automática qué facturas tienen sus retenciones asociadas y cuáles"
    " están pendientes."
)

st.sidebar.header("Carga de Archivo")
archivo_subido = st.sidebar.file_uploader(
    "Subir archivo exportado de Coopagro", type=["xls", "xlsx", "html", "htm"]
)


def procesar_archivo_coopagro(archivo):
  try:
    # Como los archivos .xls de estos sistemas son tablas HTML internas, usamos read_html
    tablas = pd.read_html(archivo)
    # Buscamos la tabla que contenga las columnas clave del resumen
    df_encontrado = None
    for t in tablas:
      columnas_texto = " ".join([str(c) for c in t.columns])
      if any(
          k in columnas_texto
          for k in [
              "Tipo Comprobante",
              "Nro. Comprobante",
              "Detalle",
              "Debe",
              "Haber",
          ]
      ):
        df_encontrado = t
        break
    if df_encontrado is None and len(tablas) > 0:
      # Si no encuentra coincidencia exacta, toma la tabla más grande
      df_encontrado = max(tablas, key=len)

    return df_encontrado
  except Exception as e:
    st.error(f"Error al leer el archivo: {e}")
    return None


if archivo_subido is not None:
  df = procesar_archivo_coopagro(archivo_subido)

  if df is not None and not df.empty:
    # Limpiar nombres de columnas y saltos de línea
    df.columns = [
        str(c).replace("\n", " ").strip() for c in df.columns
    ]

    with st.expander("🔍 Ver datos brutos importados"):
      st.dataframe(df.head(15), use_container_width=True)

    # Identificar columnas clave de forma flexible
    col_tipo = next(
        (c for c in df.columns if "Tipo Comprobante" in c), df.columns[5]
    )
    col_nro = next(
        (c for c in df.columns if "Nro." in c or "Comprobante" in c),
        df.columns[6],
    )
    col_detalle = next((c for c in df.columns if "Detalle" in c), df.columns[7])
    col_debe = next((c for c in df.columns if c in ["Debe", "Importe"]), df.columns[8])
    col_haber = next((c for c in df.columns if "Haber" in c), df.columns[9])

    # Separar Facturas y Retenciones
    facturas = df[
        df[col_tipo].astype(str).str.contains("Factura", case=False, na=False)
    ].copy()
    retenciones = df[
        df[col_tipo]
        .astype(str)
        .str.contains("Retención|Retencion", case=False, na=False)
    ].copy()

    st.subheader("📊 Diagnóstico de Retenciones por Factura")

    reporte = []

    for _, fac in facturas.iterrows():
      nro_factura_completo = str(fac[col_nro])
      # Extraer número corto (ej: 38 de 0079-00000038 o 79-38)
      match_nro = re.search(r"0079-(\d+)", nro_factura_completo)
      if not match_nro:
        continue

      nro_corto = str(
          int(match_nro.group(1))
      )  # Normaliza quitando ceros a la izquierda

      suss_total = 0.0
      iva_total = 0.0

      # Buscar retenciones asociadas en el detalle (ej. "79-38" o referencias cruzadas)
      for _, ret in retenciones.iterrows():
        det_ret = str(ret[col_detalle])
        if nro_corto in det_ret:
          # Obtener el monto (puede estar en Debe o Haber según cómo lo expida el sistema)
          val_str = str(ret[col_haber])
          if val_str in ["nan", "None", "", "0", "0.00", "nan"]:
            val_str = str(ret[col_debe])

          val_str = (
              val_str.replace(".", "")
              .replace(",", ".")
              .replace("-", "")
              .strip()
          )
          try:
            monto = float(val_str)
          except ValueError:
            monto = 0.0

          if "SUSS" in str(ret[col_tipo]) or "S.U.S.S" in det_ret:
            suss_total += monto
          elif "IVA" in str(ret[col_tipo]) or "IVA" in det_ret:
            iva_total += monto

      # Importe nominal de la factura
      imp_str = (
          str(fac[col_debe])
          .replace(".", "")
          .replace(",", ".")
          .replace("-", "")
          .strip()
      )
      try:
        importe_factura = float(imp_str)
      except ValueError:
        importe_factura = 0.0

      total_ret = suss_total + iva_total
      estado = (
          "⚠️ Falta Retención" if total_ret == 0 else "✅ Retenciones OK"
      )

      reporte.append({
          "Factura": nro_factura_completo,
          "Detalle / Producto": str(fac[col_detalle]),
          "Importe Factura ($)": importe_factura,
          "Retención S.U.S.S. ($)": suss_total,
          "Retención IVA ($)": iva_total,
          "Total Retenciones ($)": total_ret,
          "Estado": estado,
      })

    if reporte:
      df_reporte = pd.DataFrame(reporte)

      # Métricas superiores
      col1, col2, col3 = st.columns(3)
      col1.metric("Total Facturas Analizadas", len(df_reporte))
      col2.metric(
          "Facturas sin Retenciones",
          len(df_reporte[df_reporte["Total Retenciones ($)"] == 0]),
      )
      col3.metric(
          "Monto Total Facturado",
          f"${df_reporte['Importe Factura ($)'].sum():,.2f}",
      )

      # Tabla interactiva
      st.dataframe(df_reporte, use_container_width=True)

      # Botón de descarga CSV
      csv = df_reporte.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Descargar Reporte de Conciliación en CSV",
          data=csv,
          file_name="conciliacion_retenciones_coopagro.csv",
          mime="text/csv",
      )
    else:
      st.warning(
          "No se pudieron matchear retenciones con las facturas encontradas."
      )

  else:
    st.error("No se pudo leer una tabla válida del archivo subido.")
else:
  st.info(
      "👈 Subí tu archivo exportado de Coopagro en la barra lateral para"
      " comenzar."
  )
