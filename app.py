import re
import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(
    page_title="Conciliador de Retenciones - Coopagro", layout="wide"
)

st.title("🤝 Conciliador Automático de Facturas y Retenciones")
st.markdown(
    "Subí el PDF de Coopagro y el sistema detectará automáticamente qué facturas tienen retenciones asociadas y cuáles están pendientes o sin retenciones."
)

st.sidebar.header("Carga de Archivo")
pdf_subido = st.sidebar.file_uploader(
    "Subir PDF del Resumen de Cuenta", type=["pdf"]
)


def extraer_texto_y_tablas(archivo_pdf):
  filas = []
  with pdfplumber.open(archivo_pdf) as pdf:
    for pagina in pdf.pages:
      tabla = pagina.extract_tables()
      for t in tabla:
        for row in t:
          row_clean = [c.strip() if c else "" for c in row]
          if any(row_clean):
            filas.append(row_clean)
  return filas


if pdf_subido is not None:
  datos = extraer_texto_y_tablas(pdf_subido)

  if datos:
    facturas_dict = {}
    retenciones_lista = []

    # Barrido inteligente de filas para extraer comprobantes y retenciones
    for r in datos:
      texto_fila = " | ".join(r)

      # Omitir cabeceras o totales
      if any(
          x in texto_fila
          for x in [
              "SALDO ANTERIOR",
              "Saldo entre Fechas",
              "Tipo Comprobante",
              "Resumen de Cuenta",
          ]
      ):
        continue

      # Detectar Facturas (ej: Factura A Crédito MiPyme 0079-00000038)
      if "Factura" in texto_fila and "0079-" in texto_fila:
        match_nro = re.search(r"0079-\d+", texto_fila)
        match_montos = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto_fila)
        if match_nro and match_montos:
          nro_factura = match_nro.group(0)
          # Tomamos el primer monto relevante como importe
          importe = float(match_montos[0].replace(".", "").replace(",", "."))
          facturas_dict[nro_factura] = {
              "Factura": nro_factura,
              "Importe": importe,
              "Detalle": texto_fila,
          }

      # Detectar Retenciones (S.U.S.S o IVA) y su asociación (ej: s/FC 79-38)
      if (
          "Retención" in texto_fila
          or "Retencion" in texto_fila
          or "S.U.S.S" in texto_fila
          or "IVA" in texto_fila
      ):
        match_asoc = re.search(r"79-?\d+", texto_fila)
        match_montos = re.findall(r"\d{1,3}(?:\.\d{3})*,\d{2}", texto_fila)
        if match_asoc and match_montos:
          fc_asociada = match_asoc.group(0)
          monto_ret = float(
              match_montos[0].replace(".", "").replace(",", ".")
          )
          retenciones_lista.append({
              "Asociada_A": fc_asociada,
              "Monto": monto_ret,
              "Texto": texto_fila,
          })

    st.subheader("📊 Resultado del Análisis de Retenciones")

    if facturas_dict:
      reporte = []
      for nro, info in facturas_dict.items():
        # Extraemos el número corto de la factura (ej: 38 de 0079-00000038)
        nro_corto = nro.split("-")[-1]

        # Buscamos retenciones asociadas a esta factura
        suss = sum(
            r["Monto"]
            for r in retenciones_lista
            if nro_corto in r["Asociada_A"]
            and ("SUSS" in r["Texto"] or "S.U.S.S" in r["Texto"])
        )
        iva = sum(
            r["Monto"]
            for r in retenciones_lista
            if nro_corto in r["Asociada_A"] and "IVA" in r["Texto"]
        )

        total_retenciones = suss + iva

        # Estado de alerta si no tiene retenciones cargadas
        estado = (
            "⚠️ Faltan Cargar Retenciones"
            if total_retenciones == 0
            else "✅ Retenciones OK"
        )

        reporte.append({
            "Factura": nro,
            "Importe Factura ($)": info["Importe"],
            "Retención S.U.S.S. ($)": suss,
            "Retención IVA ($)": iva,
            "Total Retenciones ($)": total_retenciones,
            "Estado": estado,
        })

      df_final = pd.DataFrame(reporte)

      # Mostrar métricas rápidas
      col1, col2 = st.columns(2)
      col1.metric("Total Facturas Detectadas", len(df_final))
      col2.metric(
          "Facturas sin Retenciones Detectadas",
          len(df_final[df_final["Total Retenciones ($)"] == 0]),
      )

      # Mostrar tabla interactiva con formato
      st.dataframe(df_final, use_container_width=True)

      # Opción de descarga a CSV
      csv = df_final.to_csv(index=False).encode("utf-8")
      st.download_button(
          label="📥 Descargar Reporte en CSV",
          data=csv,
          file_name="conciliacion_retenciones.csv",
          mime="text/csv",
      )

    else:
      st.warning(
          "No se pudieron estructurar las facturas automáticamente. Podés"
          " revisar los datos en bruto debajo:"
      )
      st.dataframe(pd.DataFrame(datos))

  else:
    st.warning("El archivo PDF está vacío o no contiene texto legible.")
else:
  st.info("👈 Sube tu archivo PDF en la barra lateral para empezar.")
