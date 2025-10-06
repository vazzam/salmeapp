import os
import json
import base64
import asyncio
import threading
import queue
import logging
from datetime import datetime
from typing import Optional, Dict, Any, Callable
from pathlib import Path
import time

import streamlit as st
import numpy as np
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration
import websockets
from openai import OpenAI
import google.generativeai as genai
from dotenv import load_dotenv

# ==================== CONFIGURACIÓN ====================

# Configuración de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Validar variables de entorno requeridas
REQUIRED_ENV_VARS = ["ASSEMBLYAI_API", "DEEPINFRA_API", "GEMINI_API"]
for var in REQUIRED_ENV_VARS:
    if not os.getenv(var):
        st.error(f"❌ Variable de entorno {var} no configurada")
        st.stop()

# Configuración de APIs
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API")
GEMINI_API_KEY = os.getenv("GEMINI_API")

# Configurar Gemini
genai.configure(api_key=GEMINI_API_KEY)

# Cliente OpenAI para DeepInfra
deepinfra_client = OpenAI(
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
)

# Configuración WebRTC
RTC_CONFIGURATION = RTCConfiguration(
    {"iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
    ]}
)

# ==================== CLASES PRINCIPALES ====================

class AssemblyAIStreamingClient:
    """
    Cliente para manejar streaming de transcripción con AssemblyAI
    con reconexión automática y manejo de errores robusto
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.websocket = None
        self.session_id = None
        self.is_running = False
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        self.reconnect_delay = 2
        self.transcript_callback = None
        self.error_callback = None
        
    async def connect(self) -> bool:
        """Establece conexión con el WebSocket de AssemblyAI"""
        try:
            # URL del WebSocket con sample rate de 16kHz
            url = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
            
            # Headers de autenticación
            headers = {"Authorization": self.api_key}
            
            # Conectar al WebSocket
            self.websocket = await websockets.connect(
                url, 
                extra_headers=headers,
                ping_interval=20,
                ping_timeout=10
            )
            
            # Recibir mensaje de sesión
            session_msg = await self.websocket.recv()
            session_data = json.loads(session_msg)
            
            if session_data.get("message_type") == "SessionBegins":
                self.session_id = session_data.get("session_id")
                self.is_running = True
                self.reconnect_attempts = 0
                logger.info(f"✅ Conectado a AssemblyAI - Sesión: {self.session_id}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"❌ Error conectando a AssemblyAI: {e}")
            if self.error_callback:
                self.error_callback(f"Error de conexión: {e}")
            return False
    
    async def send_audio(self, audio_data: bytes) -> bool:
        """Envía datos de audio al WebSocket"""
        if not self.websocket or self.websocket.closed:
            return False
            
        try:
            # Codificar audio en base64
            audio_b64 = base64.b64encode(audio_data).decode('utf-8')
            
            # Crear mensaje JSON
            message = json.dumps({"audio_data": audio_b64})
            
            # Enviar al WebSocket
            await self.websocket.send(message)
            return True
            
        except Exception as e:
            logger.error(f"Error enviando audio: {e}")
            return False
    
    async def receive_transcripts(self):
        """Recibe transcripciones del WebSocket"""
        while self.is_running and self.websocket and not self.websocket.closed:
            try:
                # Recibir mensaje con timeout
                message = await asyncio.wait_for(
                    self.websocket.recv(), 
                    timeout=30.0
                )
                
                data = json.loads(message)
                message_type = data.get("message_type")
                
                # Procesar diferentes tipos de mensajes
                if message_type == "FinalTranscript":
                    text = data.get("text", "")
                    if text and self.transcript_callback:
                        await self.transcript_callback({
                            "type": "final",
                            "text": text,
                            "confidence": data.get("confidence", 0),
                            "timestamp": datetime.now()
                        })
                        
                elif message_type == "PartialTranscript":
                    text = data.get("text", "")
                    if text and self.transcript_callback:
                        await self.transcript_callback({
                            "type": "partial",
                            "text": text,
                            "timestamp": datetime.now()
                        })
                        
                elif message_type == "SessionTerminated":
                    logger.info("Sesión terminada por AssemblyAI")
                    break
                    
            except asyncio.TimeoutError:
                # Timeout normal, continuar
                continue
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Conexión WebSocket cerrada")
                await self.handle_reconnect()
                
            except Exception as e:
                logger.error(f"Error recibiendo transcripción: {e}")
                if self.error_callback:
                    self.error_callback(f"Error de recepción: {e}")
    
    async def handle_reconnect(self):
        """Maneja la reconexión automática"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Máximo de intentos de reconexión alcanzado")
            self.is_running = False
            return
        
        self.reconnect_attempts += 1
        wait_time = self.reconnect_delay * self.reconnect_attempts
        
        logger.info(f"Intentando reconectar ({self.reconnect_attempts}/{self.max_reconnect_attempts}) en {wait_time}s...")
        await asyncio.sleep(wait_time)
        
        if await self.connect():
            logger.info("✅ Reconexión exitosa")
        else:
            await self.handle_reconnect()
    
    async def disconnect(self):
        """Cierra la conexión limpiamente"""
        self.is_running = False
        
        if self.websocket and not self.websocket.closed:
            try:
                # Enviar mensaje de terminación
                await self.websocket.send(json.dumps({"terminate_session": True}))
                await self.websocket.close()
            except Exception as e:
                logger.error(f"Error al cerrar conexión: {e}")
        
        self.websocket = None
        self.session_id = None
        logger.info("Desconectado de AssemblyAI")


class AudioProcessor:
    """
    Procesador de audio que maneja la captura desde WebRTC
    y el envío a AssemblyAI
    """
    
    def __init__(self, assemblyai_client: AssemblyAIStreamingClient):
        self.client = assemblyai_client
        self.audio_buffer = []
        self.buffer_size = 8  # Tamaño del buffer antes de enviar
        self.sample_rate = 16000
        self.is_processing = False
        
    def process_audio_frame(self, frame: av.AudioFrame) -> av.AudioFrame:
        """
        Callback para procesar frames de audio desde WebRTC
        """
        if not self.is_processing:
            return frame
            
        try:
            # Convertir frame a numpy array
            sound = frame.to_ndarray()
            
            # Si es estéreo, convertir a mono
            if len(sound.shape) > 1:
                sound = np.mean(sound, axis=0)
            
            # Normalizar y convertir a 16-bit PCM
            sound = np.clip(sound * 32767, -32768, 32767)
            audio_bytes = sound.astype(np.int16).tobytes()
            
            # Agregar al buffer
            self.audio_buffer.append(audio_bytes)
            
            # Enviar cuando el buffer esté lleno
            if len(self.audio_buffer) >= self.buffer_size:
                self.send_buffered_audio()
                
        except Exception as e:
            logger.error(f"Error procesando frame de audio: {e}")
            
        return frame
    
    def send_buffered_audio(self):
        """Envía el audio almacenado en el buffer"""
        if not self.audio_buffer:
            return
            
        # Combinar todos los chunks del buffer
        combined_audio = b''.join(self.audio_buffer)
        self.audio_buffer = []
        
        # Enviar de forma asíncrona
        asyncio.create_task(self.client.send_audio(combined_audio))
    
    def start(self):
        """Inicia el procesamiento de audio"""
        self.is_processing = True
        logger.info("Procesamiento de audio iniciado")
    
    def stop(self):
        """Detiene el procesamiento de audio"""
        self.is_processing = False
        # Enviar cualquier audio restante en el buffer
        self.send_buffered_audio()
        logger.info("Procesamiento de audio detenido")


class TranscriptionManager:
    """
    Gestor principal de transcripciones que coordina
    la captura de audio, transcripción y procesamiento con LLM
    """
    
    def __init__(self):
        self.assemblyai_client = AssemblyAIStreamingClient(ASSEMBLYAI_API_KEY)
        self.audio_processor = AudioProcessor(self.assemblyai_client)
        self.transcript_queue = queue.Queue()
        self.full_transcript = []
        self.is_active = False
        self.stream_task = None
        
        # Configurar callbacks
        self.assemblyai_client.transcript_callback = self.on_transcript_received
        self.assemblyai_client.error_callback = self.on_error
    
    async def on_transcript_received(self, transcript_data: Dict[str, Any]):
        """Callback cuando se recibe una transcripción"""
        self.transcript_queue.put(transcript_data)
        
        # Si es transcripción final, agregarla al texto completo
        if transcript_data["type"] == "final":
            self.full_transcript.append(transcript_data["text"])
            
            # Procesar con LLM si está configurado para hacerlo
            if st.session_state.get("auto_process_llm", False):
                asyncio.create_task(self.process_with_llm(transcript_data["text"]))
    
    def on_error(self, error_msg: str):
        """Callback para errores"""
        st.error(f"⚠️ {error_msg}")
    
    async def start_streaming(self):
        """Inicia el streaming de transcripción"""
        try:
            # Conectar a AssemblyAI
            if not await self.assemblyai_client.connect():
                st.error("No se pudo conectar a AssemblyAI")
                return False
            
            self.is_active = True
            self.audio_processor.start()
            
            # Iniciar recepción de transcripciones
            self.stream_task = asyncio.create_task(
                self.assemblyai_client.receive_transcripts()
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Error iniciando streaming: {e}")
            st.error(f"Error: {e}")
            return False
    
    async def stop_streaming(self):
        """Detiene el streaming de transcripción"""
        self.is_active = False
        self.audio_processor.stop()
        
        # Cancelar tarea de streaming
        if self.stream_task:
            self.stream_task.cancel()
        
        # Desconectar de AssemblyAI
        await self.assemblyai_client.disconnect()
    
    async def process_with_llm(self, text: str, model: str = "gemini"):
        """
        Procesa el texto transcrito con un modelo LLM
        """
        try:
            if model == "gemini":
                result = await self.process_with_gemini(text)
            else:
                result = await self.process_with_deepinfra(text)
            
            # Agregar resultado a la cola de respuestas
            if "llm_responses" not in st.session_state:
                st.session_state.llm_responses = []
            st.session_state.llm_responses.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error procesando con LLM: {e}")
            return None
    
    async def process_with_gemini(self, text: str) -> str:
        """Procesa texto con Gemini"""
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompt = f"""
        Analiza el siguiente fragmento de transcripción de una consulta médica 
        y extrae los puntos clave relevantes:
        
        {text}
        
        Proporciona un resumen breve y estructurado.
        """
        
        response = await asyncio.to_thread(
            model.generate_content, 
            prompt
        )
        
        return response.text
    
    async def process_with_deepinfra(self, text: str) -> str:
        """Procesa texto con DeepInfra"""
        
        response = await asyncio.to_thread(
            deepinfra_client.chat.completions.create,
            model='Qwen/Qwen2.5-72B-Instruct',
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un asistente médico especializado en análisis de consultas."
                },
                {
                    "role": "user", 
                    "content": f"Analiza: {text}"
                }
            ],
            temperature=0.7,
            max_tokens=500
        )
        
        return response.choices[0].message.content
    
    def get_full_transcript(self) -> str:
        """Obtiene la transcripción completa"""
        return " ".join(self.full_transcript)
    
    def clear(self):
        """Limpia todos los datos"""
        self.full_transcript = []
        while not self.transcript_queue.empty():
            self.transcript_queue.get()


# ==================== INTERFAZ DE USUARIO ====================

def initialize_session_state():
    """Inicializa el estado de la sesión"""
    if "transcription_manager" not in st.session_state:
        st.session_state.transcription_manager = None
    
    if "is_recording" not in st.session_state:
        st.session_state.is_recording = False
    
    if "transcripts" not in st.session_state:
        st.session_state.transcripts = []
    
    if "llm_responses" not in st.session_state:
        st.session_state.llm_responses = []
    
    if "auto_process_llm" not in st.session_state:
        st.session_state.auto_process_llm = False


def render_controls():
    """Renderiza los controles de la aplicación"""
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        start_btn = st.button(
            "🎙️ Iniciar Grabación",
            use_container_width=True,
            type="primary",
            disabled=st.session_state.is_recording
        )
    
    with col2:
        stop_btn = st.button(
            "⏹️ Detener",
            use_container_width=True,
            type="secondary",
            disabled=not st.session_state.is_recording
        )
    
    with col3:
        clear_btn = st.button(
            "🗑️ Limpiar",
            use_container_width=True
        )
    
    with col4:
        st.session_state.auto_process_llm = st.checkbox(
            "Auto-procesar con IA",
            value=st.session_state.auto_process_llm
        )
    
    return start_btn, stop_btn, clear_btn


def render_transcript_display():
    """Renderiza el área de visualización de transcripciones"""
    
    # Contenedor para transcripción en tiempo real
    with st.container():
        if st.session_state.is_recording:
            st.info("🎙️ Grabando... Hable cerca del micrófono")
        
        # Mostrar transcripciones parciales y finales
        if st.session_state.transcription_manager:
            manager = st.session_state.transcription_manager
            
            # Obtener transcripciones de la cola
            transcripts = []
            while not manager.transcript_queue.empty():
                try:
                    transcript = manager.transcript_queue.get_nowait()
                    transcripts.append(transcript)
                    st.session_state.transcripts.append(transcript)
                except queue.Empty:
                    break
            
            # Mostrar transcripción completa
            if manager.full_transcript:
                st.text_area(
                    "📝 Transcripción:",
                    manager.get_full_transcript(),
                    height=200,
                    key=f"transcript_{time.time()}"
                )
    
    # Mostrar respuestas del LLM si existen
    if st.session_state.llm_responses:
        st.divider()
        st.subheader("🤖 Análisis IA")
        
        for i, response in enumerate(st.session_state.llm_responses[-3:], 1):
            with st.expander(f"Respuesta {i}", expanded=(i == len(st.session_state.llm_responses[-3:]))):
                st.write(response)


def render_processing_options():
    """Renderiza opciones de procesamiento con LLM"""
    
    if st.session_state.transcription_manager and st.session_state.transcription_manager.full_transcript:
        st.divider()
        st.subheader("🔮 Procesamiento con IA")
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            model_choice = st.selectbox(
                "Seleccionar modelo:",
                ["Gemini", "DeepInfra", "Ambos"],
                key="model_choice"
            )
        
        with col2:
            process_btn = st.button(
                "Procesar",
                use_container_width=True,
                type="primary"
            )
        
        if process_btn:
            with st.spinner("Procesando..."):
                manager = st.session_state.transcription_manager
                full_text = manager.get_full_transcript()
                
                if model_choice == "Ambos":
                    # Procesar con ambos modelos
                    gemini_task = asyncio.create_task(
                        manager.process_with_gemini(full_text)
                    )
                    deepinfra_task = asyncio.create_task(
                        manager.process_with_deepinfra(full_text)
                    )
                    
                    gemini_result = asyncio.run(gemini_task)
                    deepinfra_result = asyncio.run(deepinfra_task)
                    
                    # Mostrar resultados en tabs
                    tab1, tab2 = st.tabs(["Gemini", "DeepInfra"])
                    
                    with tab1:
                        st.text_area("Resultado Gemini:", gemini_result, height=300)
                    
                    with tab2:
                        st.text_area("Resultado DeepInfra:", deepinfra_result, height=300)
                
                else:
                    model = "gemini" if model_choice == "Gemini" else "deepinfra"
                    result = asyncio.run(
                        manager.process_with_llm(full_text, model)
                    )
                    
                    st.text_area("Resultado:", result, height=300)
                
                st.success("✅ Procesamiento completado")
        
        # Botón de descarga
        st.download_button(
            label="💾 Descargar transcripción",
            data=manager.get_full_transcript(),
            file_name=f"transcripcion_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )


async def handle_start_recording():
    """Maneja el inicio de la grabación"""
    st.session_state.is_recording = True
    
    # Crear nuevo gestor de transcripción
    manager = TranscriptionManager()
    st.session_state.transcription_manager = manager
    
    # Iniciar streaming
    success = await manager.start_streaming()
    
    if success:
        st.success("✅ Grabación iniciada")
    else:
        st.session_state.is_recording = False
        st.error("❌ No se pudo iniciar la grabación")


async def handle_stop_recording():
    """Maneja la detención de la grabación"""
    st.session_state.is_recording = False
    
    if st.session_state.transcription_manager:
        await st.session_state.transcription_manager.stop_streaming()
        st.info("⏹️ Grabación detenida")


def handle_clear():
    """Maneja la limpieza de datos"""
    st.session_state.is_recording = False
    st.session_state.transcripts = []
    st.session_state.llm_responses = []
    
    if st.session_state.transcription_manager:
        asyncio.run(st.session_state.transcription_manager.stop_streaming())
        st.session_state.transcription_manager = None
    
    st.success("✅ Datos limpiados")
    st.rerun()


# ==================== APLICACIÓN PRINCIPAL ====================

def main():
    """Función principal de la aplicación"""
    
    # Configuración de la página
    st.set_page_config(
        page_title="Transcripción en Tiempo Real",
        page_icon="🎙️",
        layout="wide"
    )
    
    # Título y descripción
    st.title("🎙️ Transcripción en Tiempo Real")
    st.markdown("""
    **Captura y transcribe audio en tiempo real usando WebRTC + AssemblyAI + IA**
    - ✅ Streaming de audio desde el navegador
    - ✅ Transcripción en tiempo real con AssemblyAI
    - ✅ Procesamiento con Gemini o DeepInfra
    - ✅ Reconexión automática en caso de fallas
    """)
    
    # Inicializar estado
    initialize_session_state()
    
    # Renderizar controles
    start_btn, stop_btn, clear_btn = render_controls()
    
    # Manejar acciones de botones
    if start_btn:
        asyncio.run(handle_start_recording())
        st.rerun()
    
    if stop_btn:
        asyncio.run(handle_stop_recording())
        st.rerun()
    
    if clear_btn:
        handle_clear()
    
    # WebRTC Streamer para captura de audio
    if st.session_state.is_recording and st.session_state.transcription_manager:
        manager = st.session_state.transcription_manager
        
        webrtc_ctx = webrtc_streamer(
            key="speech-to-text",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={
                "video": False,
                "audio": {
                    "echoCancellation": True,
                    "noiseSuppression": True,
                    "autoGainControl": True,
                    "sampleRate": 16000
                }
            },
            audio_frame_callback=manager.audio_processor.process_audio_frame,
            async_processing=True,
        )
    
    # Mostrar transcripciones
    render_transcript_display()
    
    # Opciones de procesamiento
    render_processing_options()
    
    # Información del sistema
    with st.sidebar:
        st.header("ℹ️ Información del Sistema")
        
        if st.session_state.transcription_manager:
            manager = st.session_state.transcription_manager
            
            st.metric(
                "Estado",
                "🔴 Grabando" if st.session_state.is_recording else "⚪ Detenido"
            )
            
            if manager.assemblyai_client.session_id:
                st.text(f"Sesión: {manager.assemblyai_client.session_id[:8]}...")
            
            st.metric(
                "Transcripciones",
                len(manager.full_transcript)
            )
            
            st.metric(
                "Respuestas IA",
                len(st.session_state.llm_responses)
            )
        
        st.divider()
        
        st.header("⚙️ Configuración")
        
        # Selector de modelo por defecto
        default_model = st.selectbox(
            "Modelo por defecto:",
            ["Gemini", "DeepInfra"],
            key="default_model"
        )
        
        # Opciones de audio
        st.subheader("Audio")
        
        buffer_size = st.slider(
            "Tamaño del buffer:",
            min_value=1,
            max_value=20,
            value=8,
            help="Frames de audio antes de enviar"
        )
        
        if st.session_state.transcription_manager:
            st.session_state.transcription_manager.audio_processor.buffer_size = buffer_size
