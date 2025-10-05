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
import os
from dotenv import load_dotenv
import tempfile
from pathlib import Path
import time
import assemblyai as aai
import asyncio
import websockets
import json
import base64
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import av
import numpy as np
from typing import Optional, Dict, Any
import queue
import logging
# Configuración de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear directorios necesarios
RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)

# Cargar variables de entorno
load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI")
gemini_api = os.getenv("GEMINI_API")
deepinfra_api = os.getenv("DEEPINFRA_API")
assemblyai_api = os.getenv("ASSEMBLYAI_API")

# Configuración de APIs
genai.configure(api_key=gemini_api)
aai.settings.api_key = assemblyai_api

# Cliente OpenAI para DeepInfra
openai = OpenAI(
    api_key=deepinfra_api,
    base_url="https://api.deepinfra.com/v1/openai",
)

# Configuración WebRTC para STUN/TURN servers
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]}
)

def rand_ta():
    ta = f'{random.randint(100,130)}/{random.randint(66,78)}'
    return ta

def procesar_texto(texto):
    patron = r"^```(.*?)```$"
    coincidencia = re.search(patron, texto, re.DOTALL)
    return coincidencia.group(1) if coincidencia else texto

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

client = OpenAI(
    api_key=deepinfra_api,
    base_url="https://api.deepinfra.com/v1/openai",
)

html_ex = """
```html
<!DOCTYPE html>
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
            background: rgba(119, 119, 119, 0.9);
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
</html>```"""

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
                                        La escala de cada gráfica debe comenzar en 0 y terminar en el valor máximo de la                                         escala correspondiente.
                                        Si faltan valores entre dos mediciones registradas, la línea debe unir directamente los puntos existentes sin considerar los valores ausentes como 0.
                                        Evita explicaciones adicionales sobre el código html o las gráficas generadas.
                                        Usa la siguiente plantilla HTML como base:
                                        {html_ex}
                                        '''
                                    )
    html_code = re.search(r'```html(.*?)```', response.text, re.DOTALL)
    if html_code:
        html_code = html_code.group(1).strip()
    else:
        html_code = ""

    resumen = re.sub(r'```html(.*?)```', '', response.text, flags=re.DOTALL).strip()
    resumen = re.sub(r'```markdown(.*?)', '', resumen, flags=re.DOTALL).strip()

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


# ==================== NUEVA FUNCIÓN DE STREAMING CON ASSEMBLYAI ====================
class AudioStreamProcessor:
    """Procesador de audio para streaming con AssemblyAI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.transcriber = None
        self.audio_queue = queue.Queue()
        self.transcript_queue = queue.Queue()
        self.is_running = False
        self.websocket = None
        self.session_id = None
        
    async def connect_websocket(self):
        """Conecta al websocket de AssemblyAI para streaming"""
        url = f"wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
        
        extra_headers = {
            "Authorization": self.api_key
        }
        
        try:
            self.websocket = await websockets.connect(url, extra_headers=extra_headers)
            
            # Recibir mensaje de bienvenida
            session_begins = await self.websocket.recv()
            session_data = json.loads(session_begins)
            self.session_id = session_data.get('session_id')
            logger.info(f"Sesión iniciada: {self.session_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error conectando al websocket: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes):
        """Envía audio al websocket de AssemblyAI"""
        if self.websocket and not self.websocket.closed:
            # Convertir audio a base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Crear mensaje JSON
            message = json.dumps({
                "audio_data": audio_b64
            })
            
            try:
                await self.websocket.send(message)
            except Exception as e:
                logger.error(f"Error enviando audio: {e}")
    
    async def receive_transcripts(self):
        """Recibe transcripciones del websocket"""
        while self.is_running and self.websocket and not self.websocket.closed:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=0.5)
                data = json.loads(message)
                
                if data.get('message_type') == 'FinalTranscript':
                    text = data.get('text', '')
                    if text:
                        self.transcript_queue.put({
                            'type': 'final',
                            'text': text,
                            'timestamp': datetime.now()
                        })
                        
                elif data.get('message_type') == 'PartialTranscript':
                    text = data.get('text', '')
                    if text:
                        self.transcript_queue.put({
                            'type': 'partial',
                            'text': text,
                            'timestamp': datetime.now()
                        })
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error recibiendo transcripción: {e}")
                break
    
    async def close(self):
        """Cierra la conexión websocket"""
        self.is_running = False
        
        if self.websocket and not self.websocket.closed:
            # Enviar mensaje de finalización
            await self.websocket.send(json.dumps({"terminate_session": True}))
            await self.websocket.close()
            
        self.websocket = None
        self.session_id = None

def audio_streaming_transcriber(nota: str):
    """
    Función principal para transcripción en tiempo real usando AssemblyAI
    con captura de audio desde el navegador.
    """
    
    # Inicializar claves de estado
    streaming_key = f"streaming_{nota}"
    transcription_key = f"transcripcion_{nota}"
    is_recording_key = f"is_recording_{nota}"
    full_transcript_key = f"full_transcript_{nota}"
    processor_key = f"processor_{nota}"
    audio_buffer_key = f"audio_buffer_{nota}"
    
    # Inicializar session state
    if processor_key not in st.session_state:
        st.session_state[processor_key] = None
    if transcription_key not in st.session_state:
        st.session_state[transcription_key] = None
    if is_recording_key not in st.session_state:
        st.session_state[is_recording_key] = False
    if full_transcript_key not in st.session_state:
        st.session_state[full_transcript_key] = ""
    if audio_buffer_key not in st.session_state:
        st.session_state[audio_buffer_key] = []
    
    st.subheader("🎙️ Transcripción en Streaming con AssemblyAI")
    
    # Contenedores para la UI
    status_container = st.container()
    transcript_container = st.container()
    controls_container = st.container()
    
    with controls_container:
        col1, col2, col3 = st.columns([2, 2, 2])
        
        with col1:
            start_btn = st.button(
                "🎙️ Iniciar Grabación",
                use_container_width=True,
                type="primary",
                disabled=st.session_state[is_recording_key]
            )
        
        with col2:
            stop_btn = st.button(
                "⏹️ Detener Grabación",
                use_container_width=True,
                type="secondary",
                disabled=not st.session_state[is_recording_key]
            )
        
        with col3:
            clear_btn = st.button(
                "🗑️ Limpiar",
                use_container_width=True
            )
    
    # Callback para procesar audio desde WebRTC
    def audio_frame_callback(frame: av.AudioFrame) -> av.AudioFrame:
        """Procesa frames de audio desde WebRTC"""
        if st.session_state[is_recording_key]:
            # Convertir frame a numpy array
            sound = frame.to_ndarray()
            
            # Si es estéreo, convertir a mono
            if len(sound.shape) > 1:
                sound = np.mean(sound, axis=1)
            
            # Convertir a bytes (16-bit PCM)
            audio_bytes = (sound * 32767).astype(np.int16).tobytes()
            
            # Agregar al buffer
            st.session_state[audio_buffer_key].append(audio_bytes)
            
            # Si el buffer es suficientemente grande, procesar
            if len(st.session_state[audio_buffer_key]) >= 10:  # ~100ms de audio
                combined_audio = b''.join(st.session_state[audio_buffer_key])
                st.session_state[audio_buffer_key] = []
                
                # Enviar al procesador si está activo
                if st.session_state[processor_key]:
                    asyncio.create_task(
                        st.session_state[processor_key].send_audio(combined_audio)
                    )
        
        return frame
    
    # Iniciar grabación
    if start_btn:
        st.session_state[is_recording_key] = True
        st.session_state[full_transcript_key] = ""
        st.session_state[audio_buffer_key] = []
        
        # Crear procesador de audio
        processor = AudioStreamProcessor(assemblyai_api)
        st.session_state[processor_key] = processor
        
        # Iniciar conexión asíncrona
        async def start_streaming():
            processor.is_running = True
            
            # Conectar al websocket
            if await processor.connect_websocket():
                with status_container:
                    st.success(f"✅ Conectado - Sesión: {processor.session_id}")
                
                # Iniciar recepción de transcripciones
                await processor.receive_transcripts()
            else:
                with status_container:
                    st.error("❌ Error al conectar con AssemblyAI")
                st.session_state[is_recording_key] = False
        
        # Ejecutar en thread separado
        threading.Thread(
            target=lambda: asyncio.run(start_streaming()),
            daemon=True
        ).start()
    
    # Detener grabación
    if stop_btn:
        st.session_state[is_recording_key] = False
        
        if st.session_state[processor_key]:
            processor = st.session_state[processor_key]
            
            # Cerrar conexión
            async def stop_streaming():
                await processor.close()
            
            asyncio.run(stop_streaming())
            st.session_state[processor_key] = None
            
        with status_container:
            st.info("⏹️ Grabación detenida")
    
    # Limpiar
    if clear_btn:
        st.session_state[is_recording_key] = False
        st.session_state[full_transcript_key] = ""
        st.session_state[transcription_key] = None
        st.session_state[audio_buffer_key] = []
        
        if st.session_state[processor_key]:
            processor = st.session_state[processor_key]
            asyncio.run(processor.close())
            st.session_state[processor_key] = None
        
        with status_container:
            st.success("✅ Limpiado")
        st.rerun()
    
    # WebRTC Streamer para captura de audio
    if st.session_state[is_recording_key]:
        webrtc_ctx = webrtc_streamer(
            key=f"speech-{nota}",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": False, "audio": True},
            audio_frame_callback=audio_frame_callback,
            async_processing=True,
        )
        
        # Actualizar transcripción en tiempo real
        if st.session_state[processor_key]:
            processor = st.session_state[processor_key]
            
            # Verificar cola de transcripciones
            while not processor.transcript_queue.empty():
                try:
                    transcript_data = processor.transcript_queue.get_nowait()
                    
                    if transcript_data['type'] == 'final':
                        st.session_state[full_transcript_key] += transcript_data['text'] + " "
                    
                    # Actualizar visualización
                    with transcript_container:
                        st.text_area(
                            "📝 Transcripción en tiempo real:",
                            st.session_state[full_transcript_key],
                            height=300,
                            key=f"live_{nota}_{time.time()}"
                        )
                        
                except queue.Empty:
                    break
    
    # Mostrar transcripción acumulada
    if st.session_state[full_transcript_key] and not st.session_state[is_recording_key]:
        st.divider()
        
        # Opciones de procesamiento
        col_model1, col_model2 = st.columns([2, 2])
        
        with col_model1:
            model_choice = st.radio(
                "Seleccionar modelo:",
                ["Gemini", "DeepInfra", "Ambos"],
                horizontal=True,
                key=f"model_{nota}"
            )
        
        with col_model2:
            process_btn = st.button(
                "🔮 Procesar con IA",
                use_container_width=True,
                type="primary",
                key=f"process_{nota}"
            )
        
        if process_btn:
            with st.spinner("Procesando..."):
                try:
                    if model_choice == "Ambos":
                        # Procesar con ambos modelos
                        gemini_result = process_transcription_with_llm(
                            st.session_state[full_transcript_key],
                            nota,
                            use_gemini=True
                        )
                        
                        deepinfra_result = process_transcription_with_llm(
                            st.session_state[full_transcript_key],
                            nota,
                            use_gemini=False
                        )
                        
                        # Mostrar en tabs
                        tab1, tab2 = st.tabs(["Gemini", "DeepInfra"])
                        
                        with tab1:
                            st.text_area("Resultado Gemini:", gemini_result, height=400)
                        
                        with tab2:
                            st.text_area("Resultado DeepInfra:", deepinfra_result, height=400)
                        
                        st.session_state[transcription_key] = f"### Gemini:\n{gemini_result}\n\n### DeepInfra:\n{deepinfra_result}"
                        
                    else:
                        use_gemini = model_choice == "Gemini"
                        result = process_transcription_with_llm(
                            st.session_state[full_transcript_key],
                            nota,
                            use_gemini=use_gemini
                        )
                        
                        st.session_state[transcription_key] = result
                        st.text_area("Resultado procesado:", result, height=400)
                    
                    st.success("✅ Procesamiento completado")
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
        
        # Botón de descarga
        if st.session_state[transcription_key]:
            st.download_button(
                label="💾 Descargar resultado",
                data=st.session_state[transcription_key],
                file_name=f"nota_{nota}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
    
    return st.session_state[transcription_key]

def process_transcription_with_llm(transcription_text: str, nota: str, use_gemini: bool = True):
    """
    Procesa la transcripción usando el modelo LLM seleccionado.
    """
    
    # Definir prompts según tipo de nota
    prompts = {
        "primera": """Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento 
        de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción 
        es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente 
        quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.
        
        TRANSCRIPCIÓN:
        {transcription}""",
        
        "primera_paido": """Asume el rol de un psiquiatra infantil especializado. Con base únicamente en la 
        transcripción de consulta (que incluye intervenciones del médico, el paciente y uno de los padres), 
        redacta la evolución detallada del padecimiento del paciente. La transcripción debe permitir identificar 
        claramente quién interviene en cada turno, por lo que se debe realizar una reconstrucción precisa y 
        coherente del relato clínico.
        
        TRANSCRIPCIÓN:
        {transcription}""",
        
        "subsecuente": """Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución 
        clínica del paciente entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción 
        de la consulta proporcionada. Considera que dicha transcripción corresponde a una conversación entre el 
        médico y el paciente, por lo que deberás identificar con claridad quién interviene en cada momento, 
        extrayendo exclusivamente la información clínica relevante que proviene del testimonio del paciente para 
        asegurar una redacción precisa y coherente.
        
        TRANSCRIPCIÓN:
        {transcription}"""
    }
    
    prompt = prompts.get(nota, prompts["subsecuente"]).format(transcription=transcription_text)
    
    try:
        if use_gemini:
            # Usar Gemini
            model = genai.GenerativeModel('gemini-1.5-flash')
            response = model.generate_content(prompt)
            result = response.text
            
        else:
            # Usar DeepInfra
            response = openai.chat.completions.create(
                model='Qwen/Qwen2.5-72B-Instruct',
                messages=[
                    {"role": "system", "content": "Eres un psiquiatra especializado con experiencia en redacción de notas clínicas."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            
            result = response.choices[0].message.content
            # Limpiar tags de pensamiento si existen
            result = re.sub(r'<think>[\s\S]*?</think>', '', result).strip()
        
        return result
        
    except Exception as e:
        logger.error(f"Error al procesar con LLM: {str(e)}")
        raise e

# Función alternativa sin WebRTC (usando upload de archivo)
def audio_file_transcriber(nota: str):
    """
    Alternativa para transcribir archivos de audio cuando WebRTC no está disponible.
    """
    st.subheader("📁 Transcripción de Archivo de Audio")
    
    uploaded_file = st.file_uploader(
        "Subir archivo de audio",
        type=['wav', 'mp3', 'webm', 'm4a', 'ogg'],
        key=f"upload_{nota}"
    )
    
    if uploaded_file:
        # Guardar archivo temporal
        with tempfile.NamedTemporaryFile(delete=False, suffix=Path(uploaded_file.name).suffix) as tmp_file:
            tmp_file.write(uploaded_file.getbuffer())
            temp_path = Path(tmp_file.name)
        
        try:
            # Convertir a WAV si es necesario
            audio = AudioSegment.from_file(temp_path)
            audio = audio.set_channels(1).set_frame_rate(16000)
            
            wav_path = temp_path.with_suffix('.wav')
            audio.export(wav_path, format='wav')
            
            # Transcribir con AssemblyAI
            with st.spinner("Transcribiendo audio..."):
                transcriber = aai.Transcriber()
                transcript = transcriber.transcribe(str(wav_path))
                
                if transcript.status == aai.TranscriptStatus.error:
                    st.error(f"Error en transcripción: {transcript.error}")
                    return None
                
                st.success("✅ Transcripción completada")
                
                # Mostrar transcripción
                st.text_area(
                    "Transcripción:",
                    transcript.text,
                    height=300
                )
                
                # Procesar con LLM
                if st.button("🔮 Procesar con IA", key=f"process_file_{nota}"):
                    with st.spinner("Procesando..."):
                        result = process_transcription_with_llm(
                            transcript.text,
                            nota,
                            use_gemini=True
                        )
                        
                        st.text_area(
                            "Resultado procesado:",
                            result,
                            height=400
                        )
                        
                        return result
                
        finally:
            # Limpiar archivos temporales
            temp_path.unlink(missing_ok=True)
            if wav_path.exists():
                wav_path.unlink()
    
    return None

# Función de reconexión automática
async def maintain_connection(processor: AudioStreamProcessor):
    """
    Mantiene la conexión con AssemblyAI y maneja reconexiones automáticas.
    """
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            if not processor.websocket or processor.websocket.closed:
                logger.info(f"Intento de reconexión {attempt + 1}/{max_retries}")
                
                if await processor.connect_websocket():
                    logger.info("Reconexión exitosa")
                    return True
                    
                await asyncio.sleep(retry_delay)
                retry_delay *= 2  # Backoff exponencial
                
        except Exception as e:
            logger.error(f"Error en reconexión: {e}")
            
    return False

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

def ensure_index(action, collection, index_name, index_key):
    """
    Ensure that a specified index exists on a collection. If the index does not
    exist, create it using the specified index key.
    """
    if action == 'create':
        if index_name not in [idx['name'] for idx in collection.list_indexes()]:
            collection.create_index(index_key, name=index_name)
            print(f"Created index '{index_name}' on collection '{collection.name}'")
        else:
            print(f"Index '{index_name}' already exists on collection '{collection.name}'")
    else:
        collection.drop_index(index_name)
        print(f'Index {index_name} has been deleted')

def search_collection(collection, criteria, all_info = True):
    """
    Search a MongoDB collection for documents that match a set of criteria.
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

def unidecode_except(string):
    exceptions = ['ñ','1','2','3','4','5','6','7','8','9','0',]
    replaced_string = ''
    for c in string:
        if c in exceptions:
            replaced_string += c
        else:
            replaced_string += un            replaced_string += unidecode(c)

            return replaced_string
        
        def data_format(field, val):
            """
            :param field: Debe ser array
            :param val: Debe ser array
            """
            for i in range(len(val)):
                val[i]= unidecode_except(val[i])
        
            temp_ar = {}
            for i in range(len(field)):
                temp_ar[field[i]] = {"$regex": val[i],"$options": "i"}
            return temp_ar
        
        def doc_field(database_name, collection_name, filter, projection):
            db = database_name
            collection = db[collection_name]
            documents = collection.find(filter, projection)
        
            results = []
            for document in documents:
                result = {}
                for field in projection:
                    result[field] = document[field]
                results.append(result)
            return results
        
        def buscar_clientes(nombre, apellido_paterno, apellido_materno):
            db = ['expedinente electronico']
            collection = db['pacientes']
        
            resultados = collection.find({
                'nombre': nombre,
                'apellido_paterno': apellido_paterno,
                'apellido_materno': apellido_materno
            }, {
                '_id': 0,
                'generales.fecha_nacimiento': 1
            })
        
            return [r for r in resultados]
        
        def check_ef(var):
            if var == "":
                var = 'sin alteraciones'
            return var
        
        def note_show(consultas_previas, paciente, nota):
            renglon = '\n'
            evol = st.expander('CONSULTAS PREVIAS', expanded=True)
            with evol:
                fechas_citas = []
                for i in range(consultas_previas):
                    fechas_citas.insert(0,paciente[0]['consultas'][i]['fecha'])
                fecha_nota_prev = st.selectbox('Seleccione fecha de citas previas:', fechas_citas)
                for consulta in paciente[0]["consultas"]:
                    if consulta["fecha"] == fecha_nota_prev:
                        if consulta['fecha'] == fechas_citas[-1]:
                            st.subheader('Consulta de primera vez')
                            st.text_area('', nota, height=300)
                        else:
                            prev_cons = consulta
        
                            consulta_anterior = ('##### '+prev_cons['fecha'] + renglon + renglon +
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
            db = client['expedinente_electronico']
            pacientes = db['pacientes']
            ensure_index('create',pacientes,'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo appelido', 1)])
            return client, pacientes
        
        def mongo_connect(mongodb_uri):
            uri = mongodb_uri
            client = MongoClient(uri)
            db = client['expedinente_electronico']
            pacientes = db['pacientes']
            ensure_index('create',pacientes,'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo appelido', 1)])
            return client
        
        def gdrive_up(local_file, final_name):
            gauth = GoogleAuth()
            scope = ['https://www.googleapis.com/auth/drive','https://www.googleapis.com/auth/drive.file','https://www.googleapis.com/auth/drive.appdata']
            gauth.service_account_json = 'service_account.json'
            print(gauth)
            drive = GoogleDrive(gauth)
            file_name = local_file
            gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})
            gfile.SetContentFile(file_name)
            gfile.Upload()
            print(file_name)
            print('---------DESPUES DE LEER ARCHIVO')
            file_url = 'https://drive.google.com/file/d/' + gfile['id'] + '/view'
            return file_url
