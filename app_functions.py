
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
import pyaudio
import queue

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
assemblyai_api = os.getenv("ASSEMBLYAI_API")  # Nueva variable para AssemblyAI

genai.configure(api_key=gemini_api)
aai.settings.api_key = assemblyai_api  # Configurar AssemblyAI

# Configurar cliente OpenAI compatible con deepinfra
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
def audio_recorder_transcriber(nota: str):
    """
    Función para transcripción en tiempo real usando WebRTC y AssemblyAI Streaming.
    Compatible con entornos web sin acceso directo al micrófono del sistema.
    """
    
    # Inicializar claves de estado
    streaming_key = f"streaming_{nota}"
    transcription_key = f"transcripcion_{nota}"
    is_recording_key = f"is_recording_{nota}"
    full_transcript_key = f"full_transcript_{nota}"
    processor_key = f"processor_{nota}"
    audio_queue_key = f"audio_queue_{nota}"
    websocket_key = f"websocket_{nota}"
    session_id_key = f"session_id_{nota}"
    
    # Inicializar session state
    if streaming_key not in st.session_state:
        st.session_state[streaming_key] = None
    if transcription_key not in st.session_state:
        st.session_state[transcription_key] = None
    if is_recording_key not in st.session_state:
        st.session_state[is_recording_key] = False
    if full_transcript_key not in st.session_state:
        st.session_state[full_transcript_key] = ""
    if processor_key not in st.session_state:
        st.session_state[processor_key] = None
    if audio_queue_key not in st.session_state:
        st.session_state[audio_queue_key] = queue.Queue()
    if websocket_key not in st.session_state:
        st.session_state[websocket_key] = None
    if session_id_key not in st.session_state:
        st.session_state[session_id_key] = None
    
    # Contenedor para mostrar transcripción en tiempo real
    transcript_placeholder = st.empty()
    status_placeholder = st.empty()
    
    async def connect_assemblyai():
        """Conecta al WebSocket de AssemblyAI"""
        try:
            url = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
            headers = {"Authorization": assemblyai_api}
            
            ws = await websockets.connect(url, extra_headers=headers)
            
            # Recibir mensaje de sesión
            session_msg = await ws.recv()
            session_data = json.loads(session_msg)
            
            if session_data.get("message_type") == "SessionBegins":
                session_id = session_data.get("session_id")
                st.session_state[session_id_key] = session_id
                st.session_state[websocket_key] = ws
                status_placeholder.success(f"🎙️ Sesión iniciada - ID: {session_id[:12]}...")
                return ws
            
        except Exception as e:
            status_placeholder.error(f"❌ Error conectando: {e}")
            return None
    
    async def send_audio_chunk(ws, audio_data):
        """Envía chunk de audio al WebSocket"""
        if ws and not ws.closed:
            try:
                audio_b64 = base64.b64encode(audio_data).decode('utf-8')
                await ws.send(json.dumps({"audio_data": audio_b64}))
            except Exception as e:
                logger.error(f"Error enviando audio: {e}")
    
    async def receive_transcripts(ws):
        """Recibe transcripciones del WebSocket"""
        while st.session_state[is_recording_key] and ws and not ws.closed:
            try:
                message = await asyncio.wait_for(ws.recv(), timeout=1.0)
                data = json.loads(message)
                
                message_type = data.get("message_type")
                text = data.get("text", "")
                
                if not text:
                    continue
                
                if message_type == "FinalTranscript":
                    # Transcripción final de un segmento
                    st.session_state[full_transcript_key] += text + " "
                    transcript_placeholder.text_area(
                        "📝 Transcripción en tiempo real:",
                        st.session_state[full_transcript_key],
                        height=300,
                        key=f"live_transcript_{nota}_{time.time()}"
                    )
                    
                elif message_type == "PartialTranscript":
                    # Transcripción parcial (mientras el usuario habla)
                    temp_text = st.session_state[full_transcript_key] + f"[{text}]"
                    transcript_placeholder.text_area(
                        "📝 Transcripción en tiempo real:",
                        temp_text,
                        height=300,
                        key=f"live_transcript_temp_{nota}_{time.time()}"
                    )
                    
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if st.session_state[is_recording_key]:
                    logger.error(f"Error recibiendo: {e}")
    
    async def process_audio_queue(ws):
        """Procesa la cola de audio y envía al WebSocket"""
        while st.session_state[is_recording_key]:
            try:
                # Obtener audio de la cola
                audio_data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    st.session_state[audio_queue_key].get,
                    True,
                    0.1
                )
                
                # Enviar al WebSocket
                await send_audio_chunk(ws, audio_data)
                
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error procesando cola: {e}")
    
    def audio_frame_callback(frame):
        """Callback para procesar frames de audio desde WebRTC"""
        if not st.session_state[is_recording_key]:
            return frame
        
        try:
            # Convertir frame a numpy array
            sound = frame.to_ndarray() if hasattr(frame, 'to_ndarray') else frame
            
            # Si es estéreo, convertir a mono
            if isinstance(sound, np.ndarray) and len(sound.shape) > 1:
                sound = np.mean(sound, axis=1)
            
            # Convertir a 16-bit PCM
            if isinstance(sound, np.ndarray):
                sound = np.clip(sound * 32767, -32768, 32767)
                audio_bytes = sound.astype(np.int16).tobytes()
            else:
                audio_bytes = sound
            
            # Agregar a la cola
            try:
                st.session_state[audio_queue_key].put_nowait(audio_bytes)
            except queue.Full:
                pass
                
        except Exception as e:
            logger.error(f"Error en callback de audio: {e}")
        
        return frame
    
    async def streaming_handler():
        """Manejador principal del streaming"""
        ws = await connect_assemblyai()
        if not ws:
            st.session_state[is_recording_key] = False
            return
        
        try:
            # Crear tareas paralelas
            receive_task = asyncio.create_task(receive_transcripts(ws))
            process_task = asyncio.create_task(process_audio_queue(ws))
            
            # Esperar mientras se está grabando
            while st.session_state[is_recording_key]:
                await asyncio.sleep(0.1)
            
            # Cancelar tareas
            receive_task.cancel()
            process_task.cancel()
            
        finally:
            # Cerrar WebSocket
            if ws and not ws.closed:
                await ws.send(json.dumps({"terminate_session": True}))
                await ws.close()
            
            status_placeholder.info("🛑 Sesión de grabación finalizada")
    
    # Interfaz de usuario
    st.subheader("🎙️ Transcripción en Streaming con AssemblyAI")
    
    col1, col2, col3 = st.columns([2, 2, 2])
    
    with col1:
        start_button = st.button(
            "🎙️ Iniciar Grabación",
            disabled=st.session_state[is_recording_key],
            use_container_width=True,
            type="primary",
            key=f"start_{nota}"
        )
    
    with col2:
        stop_button = st.button(
            "⏹️ Detener Grabación",
            disabled=not st.session_state[is_recording_key],
            use_container_width=True,
            type="secondary",
            key=f"stop_{nota}"
        )
    
    with col3:
        clear_button = st.button(
            "🗑️ Limpiar",
            use_container_width=True,
            key=f"clear_{nota}"
        )
    
    # Lógica de botones
    if start_button:
        st.session_state[is_recording_key] = True
        st.session_state[full_transcript_key] = ""
        st.session_state[audio_queue_key] = queue.Queue()
        
        try:
            # Iniciar streaming handler en thread separado
            def run_async_handler():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(streaming_handler())
            
            streaming_thread = threading.Thread(target=run_async_handler, daemon=True)
            streaming_thread.start()
            st.session_state[streaming_key] = streaming_thread
            
            status_placeholder.success("✅ Conectando con AssemblyAI...")
            
        except Exception as e:
            st.error(f"Error al iniciar la grabación: {str(e)}")
            st.session_state[is_recording_key] = False
    
    if stop_button:
        st.session_state[is_recording_key] = False
        if st.session_state[websocket_key]:
            # El websocket se cerrará en el handler
            st.session_state[websocket_key] = None
        status_placeholder.info("⏹️ Grabación detenida")
    
    if clear_button:
        st.session_state[is_recording_key] = False
        st.session_state[full_transcript_key] = ""
        st.session_state[transcription_key] = None
        st.session_state[audio_queue_key] = queue.Queue()
        
        if st.session_state[websocket_key]:
            st.session_state[websocket_key] = None
        
        transcript_placeholder.empty()
        status_placeholder.empty()
        st.success("✅ Transcripción limpiada")
    
    # WebRTC Streamer para captura de audio
    if st.session_state[is_recording_key]:
        st.info("🔴 Grabando... Hable claramente hacia el micrófono")
        
        # Configuración WebRTC
        rtc_config = RTCConfiguration({
            "iceServers": [
                {"urls": ["stun:stun.l.google.com:19302"]},
                {"urls": ["stun:stun1.l.google.com:19302"]},
            ]
        })
        
        # Iniciar WebRTC streamer
        webrtc_ctx = webrtc_streamer(
            key=f"speech_{nota}",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration=rtc_config,
            media_stream_constraints={
                "video": False,
                "audio": {
                    "echoCancellation": True,
                    "noiseSuppression": True,
                    "autoGainControl": True,
                }
            },
            audio_frame_callback=audio_frame_callback,
            async_processing=True,
        )
    
    # Mostrar transcripción acumulada
    if st.session_state[full_transcript_key] and not st.session_state[is_recording_key]:
        st.divider()
        
        col_process1, col_process2, col_process3 = st.columns([2, 2, 1])
        
        with col_process1:
            model_option = st.selectbox(
                "Modelo LLM:",
                ["Gemini", "DeepInfra"],
                key=f"model_{nota}"
            )
        
        with col_process2:
            process_button = st.button(
                "🔮 Procesar con LLM",
                use_container_width=True,
                type="primary",
                key=f"process_{nota}"
            )
        
        with col_process3:
            copy_button = st.button(
                "📋 Copiar",
                use_container_width=True,
                key=f"copy_{nota}"
            )
        
        if process_button and st.session_state[full_transcript_key]:
            with st.spinner(f"🤖 Procesando transcripción con {model_option}..."):
                try:
                    # Procesar según el modelo seleccionado
                    if model_option == "Gemini":
                        processed_text = process_transcription_with_gemini(
                            st.session_state[full_transcript_key],
                            nota
                        )
                    else:
                        processed_text = process_transcription_with_deepinfra(
                            st.session_state[full_transcript_key],
                            nota
                        )
                    
                    st.session_state[transcription_key] = processed_text
                    st.success("✅ Transcripción procesada exitosamente")
                    
                except Exception as e:
                    st.error(f"Error al procesar con LLM: {str(e)}")
        
        if copy_button:
            st.code(st.session_state[full_transcript_key], language=None)
    
    # Mostrar resultado procesado
    if st.session_state[transcription_key]:
        st.divider()
        st.subheader("📄 Resultado Procesado por IA")
        
        with st.expander("Ver resultado completo", expanded=True):
            st.text_area(
                "Nota Clínica Procesada:",
                st.session_state[transcription_key],
                height=400,
                key=f"processed_result_{nota}"
            )
        
        # Botón de descarga
        st.download_button(
            label="💾 Descargar Nota Procesada",
            data=st.session_state[transcription_key],
            file_name=f"nota_{nota}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            key=f"download_{nota}"
        )
    
    return st.session_state[transcription_key]


def process_transcription_with_gemini(text: str, nota: str) -> str:
    """
    Procesa la transcripción usando Gemini
    """
    prompts = {
        "primera": """Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento 
        de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción 
        es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente 
        quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.
        
        TRANSCRIPCIÓN:
        {transcription}""",
        
        "primera_paido": """Asume el rol de un psiquiatra infantil especializado. Con base únicamente en la 
        transcripción de consulta (que incluye intervenciones del médico, el paciente y uno de los padres), 
        redacta la evolución detallada del padecimiento del paciente.
        
        TRANSCRIPCIÓN:
        {transcription}""",
        
        "subsecuente": """Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución 
        clínica del paciente entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción 
        de la consulta proporcionada.
        
        TRANSCRIPCIÓN:
        {transcription}"""
    }
    
    prompt = prompts.get(nota, prompts["subsecuente"]).format(transcription=text)
    
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logger.error(f"Error con Gemini: {e}")
        raise e


def process_transcription_with_deepinfra(text: str, nota: str) -> str:
    """
    Procesa la transcripción usando DeepInfra
    """
    prompts = {
        "primera": """Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento 
        basándote en la transcripción proporcionada. Identifica correctamente quién habla en cada intervención.
        
        TRANSCRIPCIÓN:
        {transcription}""",
        
        "primera_paido": """Asume el rol de un psiquiatra infantil. Con base en la transcripción de consulta, 
        redacta la evolución detallada del padecimiento del paciente.
        
        TRANSCRIPCIÓN:
        {transcription}""",
        
        "subsecuente": """Redacta una nota de evolución clínica basándote en la transcripción de la consulta.
        
        TRANSCRIPCIÓN:
        {transcription}"""
    }
    
    prompt = prompts.get(nota, prompts["subsecuente"]).format(transcription=text)
    
    try:
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
        logger.error(f"Error con DeepInfra: {e}")
        raise e

# Función alternativa que mantiene compatibilidad con código anterior
def resumen_transcripcion_gemini(transcripcion, nota):
    """
    Función de compatibilidad que usa Gemini directamente.
    Mantiene la interfaz original para código legacy.
    """
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    if nota == "primera":
        prompt = f'''INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.

TEXTO A RESUMIR:
{transcripcion}'''
    
    elif nota == 'primera_paido':
        prompt = f'''Instrucciones Generales
Asume el rol de un psiquiatra infantil especializado. Con base únicamente en la transcripción de consulta (que incluye intervenciones del médico, el paciente y uno de los padres), redacta la evolución detallada del padecimiento del paciente. La transcripción debe permitir identificar claramente quién interviene en cada turno, por lo que se debe realizar una reconstrucción precisa y coherente del relato clínico.

TEXTO A RESUMIR:
{transcripcion}'''
    
    else:
        prompt = f'''INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución clínica del paciente entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción de la consulta proporcionada. Considera que dicha transcripción corresponde a una conversación entre el médico y el paciente, por lo que deberás identificar con claridad quién interviene en cada momento, extrayendo exclusivamente la información clínica relevante que proviene del testimonio del paciente para asegurar una redacción precisa y coherente.

TEXTO A RESUMIR:
{transcripcion}'''
    
    response = model.generate_content(prompt)
    return response.text


def resumen_transcripcion_deepinfra(transcripcion, nota):
    """
    Función de compatibilidad que usa DeepInfra directamente.
    Mantiene la interfaz original para código legacy.
    """
    llm_model = 'Qwen/Qwen3-32B'
    
    if nota == "primera":
        prompt = f'''INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.

TEXTO A RESUMIR:
{transcripcion}'''
    
    elif nota == 'primera_paido':
        prompt = f'''Instrucciones Generales
Asume el rol de un psiquiatra infantil especializado. Con base únicamente en la transcripción de consulta (que incluye intervenciones del médico, el paciente y uno de los padres), redacta la evolución detallada del padecimiento del paciente. La transcripción debe permitir identificar claramente quién interviene en cada turno, por lo que se debe realizar una reconstrucción precisa y coherente del relato clínico.

TEXTO A RESUMIR:
{transcripcion}'''
    
    else:
        prompt = f'''INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución clínica del paciente entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción de la consulta proporcionada. Considera que dicha transcripción corresponde a una conversación entre el médico y el paciente, por lo que deberás identificar con claridad quién interviene en cada momento, extrayendo exclusivamente la información clínica relevante que proviene del testimonio del paciente para asegurar una redacción precisa y coherente.

TEXTO A RESUMIR:
{transcripcion}'''
    
    response = openai.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=4000
    )
    
    output_text = response.choices[0].message.content
    output_text = re.sub(r'<think>[\s\S]*?</think>', '', output_text).strip()
    return output_text


# Función wrapper para mantener compatibilidad con código antiguo
def resumen_transcripcion(transcripcion, nota, modelo="gemini"):
    """
    Función wrapper para mantener compatibilidad con código existente.
    
    Args:
        transcripcion: Texto a procesar
        nota: Tipo de nota
        modelo: "gemini" o "deepinfra"
    """
    if modelo.lower() == "gemini":
        return resumen_transcripcion_gemini(transcripcion, nota)
    else:
        return resumen_transcripcion_deepinfra(transcripcion, nota)


# Función auxiliar para comparar resultados
def compare_llm_results(transcription_text: str, nota: str):
    """
    Función auxiliar para comparar resultados de ambos modelos lado a lado.
    
    Returns:
        Diccionario con resultados de ambos modelos
    """
    results = {}
    
    with st.spinner("Procesando con Gemini..."):
        try:
            results['gemini'] = process_transcription_with_llm(
                transcription_text, 
                nota, 
                use_gemini=True
            )
            results['gemini_status'] = 'success'
        except Exception as e:
            results['gemini'] = f"Error: {str(e)}"
            results['gemini_status'] = 'error'
    
    with st.spinner("Procesando con DeepInfra..."):
        try:
            results['deepinfra'] = process_transcription_with_llm(
                transcription_text, 
                nota, 
                use_gemini=False
            )
            results['deepinfra_status'] = 'success'
        except Exception as e:
            results['deepinfra'] = f"Error: {str(e)}"
            results['deepinfra_status'] = 'error'
    
    return results


# Mantener la función original como respaldo
def audio_recorder_transcriber_backup(nota: str):
    """Función de respaldo usando el método anterior con mic_recorder."""
    # ... [código original de audio_recorder_transcriber]
    pass


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
