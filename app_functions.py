# @title Texto de título predeterminado
import random
from datetime import date, datetime 
import streamlit as st
from unidecode import unidecode
from pymongo import MongoClient
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from openai import OpenAI
import google.generativeai as genai
import re
import threading
import io
import wave
from pydub import AudioSegment
from streamlit_mic_recorder import mic_recorder
import os
from dotenv import load_dotenv
import tempfile
from pathlib import Path

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)

def save_audio_bytes_to_file(audio_bytes: bytes, suffix: str = ".webm") -> Path:
    """Guarda bytes de audio a un archivo en disco con nombre único."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = RECORDINGS_DIR / f"rec_{ts}{suffix}"
    with open(file_path, "wb") as f:
        f.write(audio_bytes)
    return file_path

def convert_to_wav(input_path: Path) -> Path:
    """Convierte webm/mp3 a wav mono 16kHz usando pydub."""
    audio = AudioSegment.from_file(input_path)
    audio = audio.set_channels(1).set_frame_rate(16000)
    wav_path = input_path.with_suffix(".wav")
    audio.export(wav_path, format="wav")
    return wav_path
load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI")
gemini_api = os.getenv("GEMINI_API")
deepinfra_api = os.getenv("DEEPINFRA_API")

genai.configure(api_key=gemini_api)
# RAND BLOOD PRESSURE VALUES
openai = OpenAI(
    api_key=deepinfra_api,
    base_url="https://api.deepinfra.com/v1/openai",
)
def rand_ta():
    ta = f'{random.randint(100,130)}/{random.randint(66,78)}'
    return ta

def procesar_texto(texto):
    patron = r"^```(.*?)```$"
    coincidencia = re.search(patron, texto, re.DOTALL)
    
    return coincidencia.group(1) if coincidencia else texto

#ALMACEN DATOS FIJOS
# @st.cache_data
def stored_data(name):
    
    data = {
            'escalas': ['RASS.pdf','bush y francis.pdf', 'simpson angus.pdf', 'gad7.pdf', 'sad persons.pdf', 'young.pdf', 'fab.pdf', 'assist.pdf', 'dimensional.pdf', 'psp.pdf', 'yesavage.pdf', 'phq9.pdf', 'Escala dimensional de psicosis.pdf', 'moca.pdf', 'moriski-8.pdf', 'mdq.pdf', 'calgary.pdf', 'eeag.pdf', 'madrs.pdf'],
            'gpc': ['SSA-222-09 Diagnostico y tratamiento de la esquizofrenia', 'IMSS 170-09 Diagnostico y tratamiento del trastorno bipolar',
            'IMSS-392-10 Diagnostico y tratamiento del trastorno de ansiedad en el adulto', 'APA- Practice guideline for the treatment of patients with borderline personality disorder',
            'IMSS-161-09 Diagnostico y tratamiento del trastorno depresivo en el adulto', 'IMSS-528-12 Diagnostico y manejo de los trastornos del espectro autista',
            'IMSS-515-11 Diagnostico y manejo del estres post traumatico', 'SS-343-16 Diagnostico y tratamiento del consumo de marihuana en adultos en primer y segundo nivel de atención',
            'SS-023-08 Prevención, detección y consejeria en adicciones para adolescentes y adultos.', 'IMSS-385-10 Diagnostico y tratamiento de los trastornos del Sueño',
            'SS-666-14 Prevención, diagnóstico y manejo de la depresión prenatal', 'SS-294-10 Detección y atención de violencia de pareja en adulto',
            'ss-210-09 Diagnostico y tratamiento de epilepsia en el adulto',
            'IMSS-465-11 Prevención, diagnóstico y tratamiento del DELIRIUM en el adulto mayor hospitalizado'    
            ]
        }
    return data[name]


# Configurar cliente OpenAI compatible con deepinfra
client = OpenAI(
    api_key=deepinfra_api,  # Reemplaza con tu clave real
    base_url="https://api.deepinfra.com/v1/openai",
)
# def resumen_paciente(datos):
#     model = genai.GenerativeModel('gemini-2.0-flash')
#     response = model.generate_content(f'''INSTRUCCIONES: Actúa como un especialista médico y elabora un resumen conciso del expediente clínico proporcionado, siguiendo estrictamente la estructura solicitada.

#                                         FORMATO: 
#                                         - Presenta la información en una tabla con las columnas: Fecha, Evolución y síntomas, Hallazgos clínicos, Análisis médico y Tratamiento.
#                                         - Utiliza terminología médica apropiada manteniendo un tono profesional.
#                                         - Enfatiza y detalla más extensamente la última consulta, mientras que las anteriores deberán ser más breves y concisas.

#                                         ESTRUCTURA REQUERIDA:
#                                         1. Encabezado: Nombre completo, edad y ocupación del paciente
#                                         2. Motivo de la consulta inicial
#                                         3. Antecedentes médicos relevantes: Historia médica previa significativa para el caso actual
#                                         4. Tabla cronológica de consultas que incluya para cada visita:
#                                         - Fecha exacta
#                                         - Síntomas reportados (con citas textuales del paciente cuando estén disponibles)
#                                         - Resumen muy breve de los hallazgos más relevantes durante la consulta
#                                         - Resumen del análisis médico de la consulta
#                                         - Plan de tratamiento y recomendaciones

#                                         ELEMENTOS ADICIONALES:
#                                         - Si el expediente contiene valores registrados de escalas de valoración (GAF, PHQ-9, GAD-7, MDQ, etc), genera una tabla cronológica con las fechas y resultados correspondientes.

#                                         EXPEDIENTE CLÍNICO:
#                                         {datos}'''
#                                     )
#     resumen = response.text + '---'
#     return resumen

html_ex = '''<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evolución de Escalas Clinimétricas y Peso</title>
    <style>
        body {
            background-color: transparent;
            margin: 0;
            padding: 40px;
            font-family: 'Segoe UI', Arial, sans-serif;
            color: #fff;
        }
        .frame {
            background: linear-gradient(145deg, rgba(44, 44, 44, 0.9), rgba(37, 37, 37, 0.9));
            border-radius: 20px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
            padding: 30px;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            max-width: 2100px;
            margin: 0 auto;
            flex-wrap: nowrap;
            overflow-x: auto;
        }
        .chart-container {
            width: 400px;
            height: 300px;
            background: transparent;
            position: relative;
            border-radius: 12px;
            padding: 15px;
            transition: all 0.3s ease;
            flex-shrink: 0;
        }
        .chart-container:hover {
            transform: scale(1.02);
            box-shadow: 0 5px 20px rgba(0, 0, 0, 0.3);
        }
        canvas {
            background: transparent !important;
            border-radius: 10px;
        }
        ::-webkit-scrollbar {
            height: 8px;
        }
        ::-webkit-scrollbar-track {
            background: rgba(51, 51, 51, 0.5);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb {
            background: rgba(85, 85, 85, 0.7);
            border-radius: 4px;
        }
        ::-webkit-scrollbar-thumb:hover {
            background: rgba(119, 119, 119, 0.9);whius
        }
    </style>
</head>
<body>
    <div class="frame">
        <div class="chart-container">
            <canvas id="phq9Chart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="gad7Chart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="gafChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="mdqChart"></canvas>
        </div>
        <div class="chart-container">
            <canvas id="weightChart"></canvas>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const chartConfig = {
            type: 'line',
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        grid: { 
                            color: 'rgba(255, 255, 255, 0.05)',
                            borderColor: 'rgba(255, 255, 255, 0.2)'
                        },
                        ticks: { 
                            color: '#e0e0e0',
                            font: { size: 12, weight: '500' }
                        }
                    },
                    y: {
                        grid: { 
                            color: 'rgba(255, 255, 255, 0.05)',
                            borderColor: 'rgba(255, 255, 255, 0.2)'
                        },
                        ticks: { 
                            color: '#e0e0e0',
                            font: { size: 12, weight: '500' }
                        }
                    }
                },
                plugins: {
                    legend: {
                        labels: { 
                            color: '#ffffff',
                            font: { size: 16, weight: '600' },
                            padding: 20,
                            boxWidth: 20,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleFont: { size: 14, weight: '600' },
                        bodyFont: { size: 12 },
                        cornerRadius: 10,
                        padding: 12,
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }
                },
                elements: {
                    line: {
                        tension: 0.5,
                        borderWidth: 3,
                        fill: false,
                        spanGaps: true
                    },
                    point: {
                        radius: 6,
                        hoverRadius: 9,
                        backgroundColor: '#fff',
                        borderWidth: 2
                    }
                },
                animation: {
                    duration: 1800,
                    easing: 'easeOutExpo'
                }
            }
        };

        const data = {
            labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            phq9: [10, null, 8, null, 6, 5],
            gad7: [8, 9, null, 6, null, 4],
            gaf: [60, null, 65, 70, null, 75],
            mdq: [null, 5, 3, null, 3, 2],
            weight: [70, 71, null, 70, null, 69]
        };

        new Chart(document.getElementById('phq9Chart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'PHQ-9',
                    data: data.phq9,
                    borderColor: '#ff6b6b',
                    pointBackgroundColor: '#ff6b6b',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('gad7Chart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'GAD-7',
                    data: data.gad7,
                    borderColor: '#4ecdc4',
                    pointBackgroundColor: '#4ecdc4',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('gafChart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'GAF',
                    data: data.gaf,
                    borderColor: '#45b7d1',
                    pointBackgroundColor: '#45b7d1',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('mdqChart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'MDQ',
                    data: data.mdq,
                    borderColor: '#96c93d',
                    pointBackgroundColor: '#96c93d',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });

        new Chart(document.getElementById('weightChart'), {
            ...chartConfig,
            data: {
                labels: data.labels,
                datasets: [{
                    label: 'Peso (kg)',
                    data: data.weight,
                    borderColor: '#ffa502',
                    pointBackgroundColor: '#ffa502',
                    pointBorderColor: '#fff',
                    backgroundColor: 'transparent'
                }]
            }
        });
    </script>
</body>
</html>'''


def resumen_paciente(datos):
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(f'''INSTRUCCIONES: Actúa como un especialista médico y elabora un resumen conciso del expediente clínico proporcionado, 
                                        seguido del código HTML para visualizar gráficamente la evolución de las escalas clinimétricas registradas.
                                        RESUMEN DE EXPEDIENTE CLÍNICO
                                          - Presenta la información en una tabla con las columnas: Fecha, Evolución y síntomas, Hallazgos clínicos, Análisis médico y Tratamiento.
                                          - Utiliza terminología médica apropiada manteniendo un tono profesional.
                                          - Enfatiza y detalla más extensamente la última consulta, mientras que las anteriores deberán ser más breves y concisas.

                                          ESTRUCTURA REQUERIDA:
                                          1. Encabezado: Nombre completo, edad y ocupación del paciente
                                          2. Motivo de la consulta inicial
                                          3. Antecedentes médicos relevantes: Historia médica previa significativa para el caso actual
                                          4. Tabla cronológica de consultas que incluya para cada visita:
                                          - Fecha exacta
                                          - Síntomas reportados (con citas textuales del paciente cuando estén disponibles)
                                          - Resumen muy breve de los hallazgos más relevantes durante la consulta
                                          - Resumen del análisis médico de la consulta
                                          - Plan de tratamiento y recomendaciones
                                          5. Utiliza escritura markdown para resaltar títulos y subtítulos
                                          
                                          EXPEDIENTE CLÍNICO:
                                          {datos}
                                        
                                        GRÁFICAS DE CLINIMETRÍAS
                                        
                                        Si el expediente contiene valores registrados de escalas de valoración (GAF, PHQ-9, GAD-7, MDQ, etc.),
                                        genera código HTML para visualizar la evolución de los puntajes de las escalas clinimétricas registradas junto con el peso del paciente.
                                        Crea una gráfica individual para cada conjunto de valores y muéstralas dentro de un marco que contenga todas las gráficas generadas.
                                        Solo incluye gráficos de los parámetros con más de 2 valores registrados.
                                        La escala de cada gráfica debe comenzar en 0 y terminar en el valor máximo de la escala correspondiente.
                                        Si faltan valores entre dos mediciones registradas, la línea debe unir directamente los puntos existentes sin considerar los valores ausentes como 0.
                                        Evita explicaciones adicionales sobre el código html o las gŕaficas generadas.
                                        Usa la siguiente plantilla HTML como base:
                                        {html_ex}
                                        '''
                                    )
    html_code = re.search(r'```html(.*?)```', response.text, re.DOTALL)
    if html_code:
        html_code = html_code.group(1).strip()
    else:
        html_code = ""

# Extraer el resto del texto (todo lo demás)
    resumen = re.sub(r'```html(.*?)```', '', response.text, flags=re.DOTALL).strip()
    resumen = re.sub(r'```markdown(.*?)', '', resumen, flags=re.DOTALL).strip()
    
    # resumen = re.search(r'```(.*?)```', resumen, re.DOTALL)
    # if resumen:
    #     resumen = resumen.group(1).strip()
    # else:
    #     resumen = resumen

    # st.text(resumen)
    return resumen, html_code

def chat_expediente(pregunta, expediente):
    model = genai.GenerativeModel('gemini-2.5-flash')
    response = model.generate_content(f'''INSTRUCCIONES: Actúa como un especialista médico y responde la pregunta sobre el expediente clínico proporcionado, siguiendo estrictamente la estructura solicitada.

                                        FORMATO: 
                                        - Presenta la información de una forma breve, precisa y concisa con un formato de fácil lectura e interpretación en pocas líneas
                                        - Utiliza terminología médica apropiada manteniendo un tono profesional.
                                        PREGUNTA:
                                        {pregunta}
                                        EXPEDIENTE CLÍNICO:
                                        {expediente}'''
                                    )
    respuesta = response.text
    return respuesta

    def audio_recorder_transcriber_improved(nota: str):
        """Función mejorada para grabar, segmentar y transcribir audio desde el navegador."""
        
        def split_audio(audio_data: io.BytesIO, segment_duration_ms: int = 300000):
            """Divide el audio en fragmentos menores con mejor manejo de errores."""
            try:
                # Verificar tamaño del archivo
                audio_size_mb = len(audio_data.getvalue()) / (1024 * 1024)
                if audio_size_mb > 25:
                    st.warning(f"El archivo de audio ({audio_size_mb:.2f} MB) es muy grande. Se dividirá en segmentos.")
                
                audio = AudioSegment.from_file(audio_data, format="webm")
                duration_ms = len(audio)
                segments = []
                
                if duration_ms <= segment_duration_ms:
                    # Si el audio es menor al límite, no dividir
                    return [audio_data]
                
                for start_ms in range(0, duration_ms, segment_duration_ms):
                    end_ms = min(start_ms + segment_duration_ms, duration_ms)
                    segment = audio[start_ms:end_ms]
                    segment_io = io.BytesIO()
                    segment.export(segment_io, format="webm")
                    segment_io.seek(0)
                    segments.append(segment_io)
                
                return segments
            except Exception as e:
                st.error(f"Error al segmentar el audio: {str(e)}")
                return None
    
        def transcribe_audio_with_retry(audio_data, max_retries=3):
            """Transcribe el audio con reintentos y mejor manejo de errores."""
            for attempt in range(max_retries):
                try:
                    st.info(f"Intento de transcripción {attempt + 1}/{max_retries}")
                    
                    # Verificar tamaño antes de enviar
                    audio_size_mb = len(audio_data.getvalue()) / (1024 * 1024)
                    if audio_size_mb > 25:
                        st.error(f"El archivo ({audio_size_mb:.2f} MB) excede el límite de 25 MB")
                        return None
                    
                    response = client.audio.transcriptions.create(
                        model="openai/whisper-large-v3-turbo",
                        file=("audio.webm", audio_data, "audio/webm"),
                        language="es",
                        timeout=300  # 5 minutos de timeout
                    )
                    
                    if response.text:
                        return response.text
                        
                except Exception as e:
                    st.error(f"Error en intento {attempt + 1}: {str(e)}")
                    if attempt < max_retries - 1:
                        st.info("Reintentando en 2 segundos...")
                        time.sleep(2)
                    else:
                        st.error("Se agotaron los reintentos para la transcripción")
            
            return None
    
        def process_transcription(transcription_text, nota):
            """Procesa la transcripción con manejo de errores mejorado."""
            try:
                summarized = resumen_transcripcion(transcription_text, nota)
                try:
                    summarized2 = resumen_transcripcion2(transcription_text, nota)
                    return summarized + " VERSION 2: --------»»              " + summarized2
                except Exception as e:
                    st.warning(f"Error en resumen 2: {str(e)}")
                    return summarized
            except Exception as e:
                try:
                    st.warning(f"Error en resumen 1: {str(e)}")
                    summarized2 = resumen_transcripcion2(transcription_text, nota)
                    return summarized2
                except Exception as e2:
                    st.error(f"Error en ambos resúmenes: {str(e2)}")
                    return transcription_text
    
        # Inicializar estado con claves únicas
        audio_key = f"audio_data_{nota}"
        transcription_key = f"transcripcion_{nota}"
        recording_key = f"is_recording_{nota}"
        processing_key = f"is_processing_{nota}"
        
        if audio_key not in st.session_state:
            st.session_state[audio_key] = None
        if transcription_key not in st.session_state:
            st.session_state[transcription_key] = ""
        if recording_key not in st.session_state:
            st.session_state[recording_key] = False
        if processing_key not in st.session_state:
            st.session_state[processing_key] = False
    
        # Interfaz mejorada
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.text('Grabación de Audio')
            
            # Usar key único para evitar conflictos
            recorder_key = f"mic_recorder_{nota}_{datetime.now().strftime('%H%M%S')}"
            
            audio_value = mic_recorder(
                start_prompt="🎙️ Iniciar Grabación",
                stop_prompt="⏹️ Detener",
                just_once=False,
                use_container_width=True,
                format="webm",
                callback=None,
                args=(),
                kwargs={},
                key=recorder_key
            )
            
            # Mostrar información del audio si existe
            if audio_value:
                audio_size_mb = len(audio_value['bytes']) / (1024 * 1024)
                st.info(f"Audio capturado: {audio_size_mb:.2f} MB")
                
                # Mostrar reproductor de audio
                st.audio(audio_value['bytes'], format="audio/webm")
                
                # Guardar en session state
                st.session_state[audio_key] = audio_value['bytes']
                st.session_state[recording_key] = True
    
        with col2:
            # Botón de transcripción con estado mejorado
            transcribe_disabled = (
                not st.session_state[audio_key] or 
                st.session_state[processing_key]
            )
            
            if st.button(
                "🔮 Transcribir", 
                use_container_width=True,
                disabled=transcribe_disabled,
                help="Haga clic para transcribir el audio grabado"
            ):
                if st.session_state[audio_key]:
                    st.session_state[processing_key] = True
                    st.session_state[recording_key] = False
                    
                    try:
                        with st.spinner("Procesando transcripción..."):
                            # Crear BytesIO desde los bytes
                            audio_io = io.BytesIO(st.session_state[audio_key])
                            
                            # Intentar transcripción directa primero
                            transcription = transcribe_audio_with_retry(audio_io)
                            
                            if transcription:
                                # Procesar transcripción
                                processed_result = process_transcription(transcription, nota)
                                st.session_state[transcription_key] = processed_result
                                st.success("✅ Transcripción completada exitosamente")
                            else:
                                st.error("❌ No se pudo completar la transcripción")
                    
                    except Exception as e:
                        st.error(f"Error durante el procesamiento: {str(e)}")
                    
                    finally:
                        st.session_state[processing_key] = False
    
        with col3:
            # Botón para limpiar
            if st.button("🗑️ Limpiar", use_container_width=True):
                st.session_state[audio_key] = None
                st.session_state[transcription_key] = ""
                st.session_state[recording_key] = False
                st.session_state[processing_key] = False
                st.rerun()
    
        # Mostrar estado actual
        if st.session_state[processing_key]:
            st.info("🔄 Procesando audio... Por favor espere.")
        elif st.session_state[recording_key] and st.session_state[audio_key]:
            st.success("🎵 Audio listo para transcribir")
        elif not st.session_state[audio_key]:
            st.info("🎙️ Grabe un audio para comenzar")
    
        # Mostrar progreso de duración si hay audio
        if st.session_state[audio_key]:
            try:
                audio_io = io.BytesIO(st.session_state[audio_key])
                audio = AudioSegment.from_file(audio_io, format="webm")
                duration_seconds = len(audio) / 1000
                duration_minutes = duration_seconds / 60
                
                if duration_minutes > 10:
                    st.warning(f"⚠️ Audio largo detectado: {duration_minutes:.1f} minutos. "
                              "Esto podría requerir procesamiento en segmentos.")
        except:
            pass

    return st.session_state[transcription_key]
    
def calculate_age(born):
    today = datetime.now()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def clin_merge(scale):
    if scale != '':
        return f' {scale}, '
    else:
        return ''

def radio_check(var):
    if var != '':
        return 'Yes'
    else:
        return ''
    
def update_dict(dic,var):
    dic.update({var:'Yes',})

def id_gen():
    now = datetime.now()
    date_id = now.strftime('%d%m%y%H%M%S')
    return int(date_id)
# @st.cache_data
def ensure_index(action, collection, index_name, index_key):
    """
    Ensure that a specified index exists on a collection. If the index does not
    exist, create it using the specified index key.

    :param action: Must be an str an lets us to 'delete' or 'create' an index.
    :param collection: The MongoDB collection to ensure the index on.
    :param index_name: The name of the index to check/create.
    :param index_key: A dictionary of field names and sort orders to use as the index key.
    """
    if action == 'create':
        # Check if the index exists
        if index_name not in [idx['name'] for idx in collection.list_indexes()]:
            # If the index does not exist, create it
            collection.create_index(index_key, name=index_name)
            print(f"Created index '{index_name}' on collection '{collection.name}'")
        else:
            print(f"Index '{index_name}' already exists on collection '{collection.name}'")
    else:
        collection.drop_index(index_name)
        print(f'Index {index_name} has been deleted')
# @st.cache_data
def search_collection(collection, criteria, all_info = True):
    """
    Search a MongoDB collection for documents that match a set of criteria.

    :param collection: The MongoDB collection to search.
    :param criteria: A dictionary of search criteria.
    :return: A list of all documents in the collection that match the criteria.
    """
    results = []
    if all_info:
        for document in collection.find(criteria):
            results.append(document)
        return results
    else:
        for document in collection.find(criteria,{'_id': 0, 'nombres':1,'primer apellido':1,'segundo apellido':1,'generales.nacimiento.fecha': 1}):
            results.append(document)
        return results
    st.write(results)

def unidecode_except(string):
    # Replace all characters except for the ones in the exception list
    exceptions = ['ñ','1','2','3','4','5','6','7','8','9','0',]
    replaced_string = ''
    for c in string:
        if c in exceptions:
            replaced_string += c
        else:
            replaced_string += unidecode(c)

    return replaced_string

def data_format(field, val):
    """
    :param field: Debe ser array
    :param val: Debe ser array
    """
    for i in range(len(val)):
        val[i]= unidecode_except(val[i])

    # print(val)    

    temp_ar = {}
    for i in range(len(field)):
        temp_ar[field[i]] = {"$regex": val[i],"$options": "i"}
        # print(f'{i}. {temp_ar}')
    # print(temp_ar['nombres'])
    return temp_ar

def doc_field( database_name, collection_name, filter, projection):
    # Set up a MongoDB client and database
    db = database_name
    
    # Set up a collection in the database
    collection = db[collection_name]
    
    # Find all matching documents with the specified fields
    documents = collection.find(filter, projection)
    
    # Loop through the documents and return the specified fields
    results = []
    for document in documents:
        result = {}
        for field in projection:
            result[field] = document[field]
        results.append(result)
    return results

def buscar_clientes(nombre, apellido_paterno, apellido_materno):
    # crear una conexión con la base de datos
    db = ['expedinente electronico']
    collection = db['pacientes']

    # buscar coincidencias usando los parámetros de búsqueda
    resultados = collection.find({
        'nombre': nombre,
        'apellido_paterno': apellido_paterno,
        'apellido_materno': apellido_materno
    }, {
        '_id': 0,
        'generales.fecha_nacimiento': 1
    })

    # retornar los resultados de la búsqueda junto con la fecha de nacimiento
    return [r for r in resultados]

def check_ef(var):
    if var == "":
        var = 'sin alteraciones'
    return var

def note_show(consultas_previas, paciente, nota):
    renglon = '\n'
    evol = st.expander('CONSULTAS PREVIAS', expanded=True)
    with evol:
        # st.subheader(consultas_previas)
        fechas_citas = []                       
        for i in range(consultas_previas):
            fechas_citas.insert(0,paciente[0]['consultas'][i]['fecha'])
            # fechas_citas = sorted(fechas_citas, key=lambda x: datetime.strptime(x, "%d/%m/%Y %H:%M"), reverse=True)
        fecha_nota_prev = st.selectbox('Seleccione fecha de citas previas:', fechas_citas)
        for consulta in paciente[0]["consultas"]:
            if consulta["fecha"] == fecha_nota_prev:
                if consulta['fecha'] == fechas_citas[-1]: # Se coteja si es la consulta de primera vez
                    #Es consulta de primera vez
                    st.subheader('Consulta de primera vez')
                    # st.write(consulta)
                    st.text_area('', nota, height=300)
                else:
                    # st.write("Se encontró una consulta en la fecha buscada:")
                    # st.write(consulta)
                    prev_cons = consulta

                    consulta_anterior = ('##### '+prev_cons['fecha'] + renglon + renglon + #'- ' +
                                            '> ' + prev_cons['presentacion'].replace('\n', ' ') + renglon + '- ' + 
                                            prev_cons['subjetivo'] + renglon + renglon + 
                                            '- '+'SOMATOMETRÍA Y SIGNOS VITALES:' + renglon + 
                                            'FC: ' + prev_cons['fc'] + ' lpm' + ' | ' +  'FR: ' + prev_cons['fr'] + ' rpm' + ' | ' + 'TA: ' + prev_cons['ta'] + ' mmHg' + ' | ' + ' ------- ' + 'PESO: ' +  str(prev_cons['peso']) + ' ' + 'kg' + '  ' + 'TALLA: ' + str(prev_cons['talla']) + ' ' + 'cm' + renglon + renglon + '- ' +
                                            prev_cons['objetivo'] + renglon + renglon + 
                                            'PHQ-9: '+ prev_cons['clinimetrias']['phq9'] + ' ' + ' |   ' + 
                                            'GAD-7: '+ prev_cons['clinimetrias']['gad7'] + ' ' + ' |   ' +
                                            'SADPERSONS: '+ prev_cons['clinimetrias']['sadpersons'] + ' ' + ' |   ' +
                                            'YOUNG: '+ prev_cons['clinimetrias']['young'] + ' ' + ' |   ' +
                                            'MDQ: '+ prev_cons['clinimetrias']['mdq'] + ' ' + ' |   ' +
                                            'ASRS: '+ prev_cons['clinimetrias']['asrs'] + ' ' + ' |   ' +
                                            'OTRAS: '+ prev_cons['clinimetrias']['otras_clini'] + ' ' + ' |   ' + renglon + renglon +     
                                            '##### '+ 'ANÁLISIS: ' + renglon +prev_cons['analisis'] + renglon + renglon +
                                            '##### '+ 'PLAN: ' + renglon + prev_cons['plan'] + renglon + '--- '
                                #  prev_cons['objetivo'] + renglon + 
                                #  prev_cons[''] + renglon + 
                                #  prev_cons[''] + renglon + 
                                #  prev_cons[''] + renglon + 
                                    ) #f'{consulta}{renglon}{renglon}MC: {mc}{renglon}PA: {pa}{renglon}{renglon}EXAMEN MENTAL{renglon}{renglon}{em}{renglon}{renglon}EXPLORACIÓN FÍSICA{renglon}{renglon}{somato_sv_merge}{renglon}{renglon}{ef_merge}{renglon}{alteraciones_merge}{renglon}{renglon}LABORATORIALES{renglon}- Previos: {labs_prev}{renglon}- Solicitados: {labs_nvos}{renglon}{renglon}DIAGNÓSTICO(S){renglon}{renglon}{dx}{renglon}{renglon}PRONÓSTICO: {pronostico}{renglon}{renglon}{clinimetria}{renglon}{renglon}ANÁLISIS{renglon}{renglon}{analisis}TRATAMIENTO{renglon}{renglon}{tx}'
                    # st.subheader(f'Consulta subsecuente No: {consultas_previas}')
                    # nota_revisada = st.text_area('', consulta_anterior, height=450)
                    st.markdown(consulta_anterior)
    return fechas_citas[-1]

def last_note(consultas_previas, paciente, nota):
    renglon = '\n'
    fechas_citas = []                       
    for i in range(consultas_previas):
        fechas_citas.append(paciente[0]['consultas'][i]['fecha'])
    
    return fechas_citas[-1], len(fechas_citas)


def mongo_intial(mongodb_uri):
    uri = mongodb_uri
    client = MongoClient(uri)
    db = client['expedinente_electronico'] #base de datos
    pacientes = db['pacientes'] #colección
    ensure_index('create',pacientes,'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo appelido', 1)])
    return client, pacientes

def mongo_connect(mongodb_uri):
    uri = mongodb_uri
    client = MongoClient(uri)
    db = client['expedinente_electronico'] #base de datos
    pacientes = db['pacientes'] #colección
    ensure_index('create',pacientes,'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo appelido', 1)])
    return client

# def gdrive_up(local_file, final_name):
#     g_login = GoogleAuth()
#     g_login.LocalWebserverAuth()
#     drive = GoogleDrive(g_login)
#     file_name = local_file
#     gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})
#     # Read file and set it as the content of this instance.
#     gfile.SetContentFile(file_name)
#     gfile.Upload()
#     print(file_name)
#     # gfile.GetContentFile(file_name)
#     print('---------DESPUES DE LEER ARCHIVO')
#     file_url = 'https://drive.google.com/file/d/' + gfile['id'] + '/view'
#     return file_url

def gdrive_up(local_file, final_name):
    gauth = GoogleAuth()
    scope = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/drive.appdata']
    # gauth.credentials = ServiceAccountCredentials.from_json_keyfile_name('./service_account.json',scope)
    gauth.service_account_json = 'service_account.json'
    print(gauth)
    drive = GoogleDrive(gauth)
    file_name = local_file
    gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})
    # Read file and set it as the content of this instance.
    gfile.SetContentFile(file_name)
    gfile.Upload()
    print(file_name)
    # gfile.GetContentFile(file_name)
    print('---------DESPUES DE LEER ARCHIVO')
    file_url = 'https://drive.google.com/file/d/' + gfile['id'] + '/view'
    return file_url

# def chatgpt(data, summary_lenght, model = 'chat'):
#     prompt = f'Actúa como un experto médico especialista en pisuiatría y ayúdame a hacer un resumen a forma de párrafo de no más de 10 líneas con los principales antecedentes del paciente y finallmente organiza en una tabla cada una de las consultas con los principales síntomas y tratamientos: {data}'
#     if model == 'chat':
#             response = openai.ChatCompletion.create(
#             model="gpt-3.5-turbo-16k",
#             messages=[{"role": "user", "content": f'{prompt}'}
#                 ])
#             return response.choices[0]['message']['content']



# Secciones Adicionales (Incluir al Final de la Descripción Principal)  
# Usa exclusivamente la información extraída de la transcripción para desarrollar lo siguiente:

# 1. ANTECEDENTES PERSONALES PATOLÓGICOS:  
#    - Historial de alergias, cirugías, fracturas, trauma craneoencefálico (con pérdida de conciencia), convulsiones, transfusiones, enfermedades crónicas (ej. asma, diabetes, trastornos tiroideos), medicamentos actuales (nombre, dosis, duración) y estado del esquema de vacunación.
#    - PSIQUIÁTRICOS: Atenciones previas por parte de especialistas en salud mental (psicólogos y psiquiátras) incluyendo fechas de inicio, duración, síntomas que presentaban, diagnósticos dados, tratamientos y si hubo mejoría. También incluye si ha presentado hospitalizaciones en centros especializados en salud mental o adicciones así como si ha presentado conductas autolesivas (número de ocasiones, fechas, métodos). Incluye la información únicamente si se menciona en la transcripción. 
# 2. PERINATALES:  
#    - Curso del embarazo (normoevolutivo o con complicaciones como amenaza de aborto, preeclampsia, infecciones, etc.).  
#    - Tipo de nacimiento (parto o cesárea, motivo si aplica), si fue semanas de gestación (si fue pretérmino, a término o postérmino), complicaciones al nacer, peso y talla, esfuerzo respiratorio, intervenciones neonatales, alta con la madre y si en las semanas siguientes al alta existió alguna complicación como infecciones, ictericia u otras.

# 3. NEURODESARROLLO:  
#    - Desempeño de hitos (sostén cefálico, sedestación, gateo, bipedestación, deambulación, lenguaje: desde palabras simples hasta conversación fluida, control de esfínteres), especificando la edad en meses cuando se mencione. Solo utilizar la información de la transcripción si no se menciona no la incluyas.

# 4. DESARROLLO ESCOLAR:  
#    - Niveles cursados (guardería, preescolar, primaria, secundaria, preparatoria), edad de inicio por etapa, reportes escolares (tipo, existencia), desempeño académico (notas, materias reprobadas si se indican) y observaciones sobre el rendimiento o quejas actuales; incluir el grado actual
