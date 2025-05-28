import streamlit as st
import geopandas as gpd
import pandas as pd
import fiona
import tempfile
import shutil
import os
import zipfile

st.set_page_config(page_title="Analizador GDB", layout="centered")

st.title("🔍 Analizador de Geodatabase (.gdb)")
st.markdown("Sube una carpeta .gdb comprimida en ZIP, analizaremos las capas y podrás descargar el reporte.")

@st.cache_data
def cargar_diccionario_mag():
    try:
        mag_df = pd.read_excel("MAG_con_obligacion.xlsx")
        return mag_df
    except Exception as e:
        st.error(f"No se pudo cargar el archivo MAG_con_obligacion.xlsx: {e}")
        return pd.DataFrame()

def obtener_obligacion(mag_df, capa, campo):
    row = mag_df[(mag_df["Capa/Tabla"] == capa) & (mag_df["Campo"] == campo)]
    if not row.empty:
        return row.iloc[0]["OBLIGACIÓN/CONDICIÓN"]
    return "Desconocido"

# Cargar diccionario
mag_df = cargar_diccionario_mag()

# Subir archivo ZIP con la GDB
archivo_zip = st.file_uploader("📁 Sube tu archivo .gdb en formato ZIP", type=["zip"])

if archivo_zip:
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "temp.zip")
        with open(zip_path, "wb") as f:
            f.write(archivo_zip.read())

        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(tmpdir)

        gdb_dirs = [os.path.join(tmpdir, d) for d in os.listdir(tmpdir) if d.endswith(".gdb")]

        if gdb_dirs:
            gdb_path = gdb_dirs[0]
            capas = fiona.listlayers(gdb_path)
            resultado = []

            progress = st.progress(0)
            for i, capa in enumerate(capas):
                try:
                    gdf = gpd.read_file(gdb_path, layer=capa)
                    for col in gdf.columns:
                        if col == "geometry":
                            continue
                        nulos = gdf[col].isnull().sum()
                        ceros = ((gdf[col] == 0) & gdf[col].notnull()).sum() if pd.api.types.is_numeric_dtype(gdf[col]) else 0
                        obligacion = obtener_obligacion(mag_df, capa, col)

                        if nulos > 0:
                            resultado.append(["Valores Nulos", capa, col, obligacion])
                        if ceros > 0:
                            resultado.append(["Valores en Cero", capa, col, obligacion])
                except Exception as e:
                    st.warning(f"⚠️ Error en capa {capa}: {e}")
                progress.progress((i + 1) / len(capas))

            if resultado:
                df_result = pd.DataFrame(resultado, columns=["Inconsistencia", "Capa/Tabla", "Campo", "OBLIGACIÓN/CONDICIÓN"])
                st.success("✔ Análisis completado")

                # Exportar a Excel
                output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
                df_result.to_excel(output.name, index=False)
                output.seek(0)

                with open(output.name, "rb") as f:
                    st.download_button("📥 Descargar reporte Excel", f, file_name="reporte_inconsistencias.xlsx")

            else:
                st.success("✔ Sin inconsistencias encontradas")
        else:
            st.error("❌ No se encontró ninguna carpeta .gdb en el ZIP subido.")