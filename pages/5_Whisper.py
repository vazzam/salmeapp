import streamlit as st
from datetime import datetime 
from pathlib import Path
from streamlit.components.v1 import html
import app_functions as afx

st.set_page_config(
    page_title="Whisper",
    page_icon="fav.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

def get_base64_image(image_path):
    import base64
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

logo_path = Path('vitalia.png')

if logo_path.exists():
    logo_base64 = get_base64_image(logo_path)
else:
    logo_base64 = ""
    st.warning("Logotipo no encontrado en la ruta especificada.")

def load_css():
    with open('style.css', 'r') as f:
        css = f.read()
    st.markdown(f'<style>{css}</style>', unsafe_allow_html=True)

# Llama a la función al principio de tu app
load_css()

st.markdown(f"""
    <div class="app-header">
        <div class="logo-container">
            <img src="data:image/png;base64,{logo_base64}" class="logo" alt="Logo">
        </div>
    </div>
    <script>
        window.addEventListener('scroll', function() {{
            const header = document.querySelector('.app-header');
            const app = document.querySelector('.stApp');
            if (window.scrollY > 50) {{
                header.classList.add('scrolled');
                app.classList.add('scrolled');
            }} else {{
                header.classList.remove('scrolled');
                app.classList.remove('scrolled');
            }}
        }});
    </script>
""", unsafe_allow_html=True)

st.markdown('<div class="title-container"><h1>WhisperRec</h1></div>', unsafe_allow_html=True)

# Módulo principal de grabación y transcripción
st.markdown("---")

# Menú desplegable para tipo de nota
col_tipo, col_fecha = st.columns([0.5, 0.5])
with col_tipo:
    tipo_nota = st.selectbox(
        "Tipo de nota de transcripción:",
        ["primera", "subsecuente", "primera_paido"],
        help="Selecciona el tipo de nota para la transcripción"
    )

with col_fecha:
    fecha_actual = datetime.now().strftime("%d/%m/%Y %H:%M")
    st.info(f"📅 Fecha y hora: {fecha_actual}")


st.markdown("---")

# # Llamar a la función de grabación con el tipo de nota seleccionado
# st.subheader("🎙️ Grabación de Audio")
# st.info("Presiona el botón de grabación para comenzar a capturar el audio de la consulta")

transcripcion = afx.audio_recorder_transcriber(tipo_nota)

# Área para mostrar la transcripción
if transcripcion:
    st.markdown("---")
    st.subheader("📝")
    
    # Área de texto para editar la transcripción
    transcripcion_editada = st.text_area(
        "Puedes editar la transcripción antes de guardar o copiar:",
        value=transcripcion,
        height=400,
        key="transcripcion_area"
    )
    
    # Botones de acción
    col1, col2, col3, col4 = st.columns([0.2, 0.2, 0.2, 0.4])
    
    with col1:
        if st.button("📋 Copiar al portapapeles", type="primary"):
            # Código JavaScript para copiar al portapapeles
            copy_script = f"""
            <script>
            navigator.clipboard.writeText(`{transcripcion_editada}`);
            </script>
            """
            html(copy_script)
            st.success("✅ Transcripción copiada al portapapeles")
    
    with col2:
        # Botón de descarga
        st.download_button(
            label="⬇️ Descargar TXT",
            data=transcripcion_editada,
            file_name=f"transcripcion_{tipo_nota}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )
    
    with col3:
        if st.button("🗑️ Limpiar"):
            st.rerun()
    
    # Mostrar estadísticas de la transcripción
    st.markdown("---")
    col_stats1, col_stats2, col_stats3 = st.columns(3)
    
    with col_stats1:
        palabras = len(transcripcion_editada.split())
        st.metric("Palabras", palabras)
    
    with col_stats2:
        caracteres = len(transcripcion_editada)
        st.metric("Caracteres", caracteres)
    
    with col_stats3:
        lineas = len(transcripcion_editada.split('\n'))
        st.metric("Líneas", lineas)


# Script para mantener la pantalla activa durante la grabación
wake_lock_script = """
<script>
let wakeLock = null;
const requestWakeLock = async () => {
    try {
        wakeLock = await navigator.wakeLock.request('screen');
        console.log('Wake Lock activado');
    } catch (err) {
        console.log('Error al activar Wake Lock: ', err);
    }
};
requestWakeLock();

// Función para copiar al portapapeles
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(function() {
        console.log('Texto copiado al portapapeles');
    }, function(err) {
        console.error('Error al copiar: ', err);
    });
}
</script>
"""

# Inyectar el script en la app
html(wake_lock_script)

# Footer con información adicional
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #888; font-size: 0.9em;'>
    Sistema de Grabación y Transcripción Médica | Desarrollado con Streamlit
</div>
""", unsafe_allow_html=True)
