
import os
import json
import base64
import asyncio
import threading
import queue
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path
import time
import re
from dataclasses import dataclass
from enum import Enum

import streamlit as st
import numpy as np
from streamlit_webrtc import webrtc_streamer, WebRtcMode, RTCConfiguration, AudioProcessorBase
import websockets
from openai import OpenAI
import google.generativeai as genai
from pymongo import MongoClient
from dotenv import load_dotenv

# ==================== CONFIGURACIÓN INICIAL ====================

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cargar variables de entorno
load_dotenv()

# Validar configuración
ASSEMBLYAI_API_KEY = os.getenv("ASSEMBLYAI_API")
DEEPINFRA_API_KEY = os.getenv("DEEPINFRA_API")
GEMINI_API_KEY = os.getenv("GEMINI_API")
MONGODB_URI = os.getenv("MONGODB_URI")

if not all([ASSEMBLYAI_API_KEY, DEEPINFRA_API_KEY, GEMINI_API_KEY]):
    st.error("⚠️ Configuración incompleta. Verifica las variables de entorno.")
    st.stop()

# Configurar APIs
genai.configure(api_key=GEMINI_API_KEY)

deepinfra_client = OpenAI(
    api_key=DEEPINFRA_API_KEY,
    base_url="https://api.deepinfra.com/v1/openai",
)

# WebRTC config
RTC_CONFIGURATION = RTCConfiguration({
    "iceServers": [
        {"urls": ["stun:stun.l.google.com:19302"]},
        {"urls": ["stun:stun1.l.google.com:19302"]},
    ]
})

# ==================== PROCESADOR DE AUDIO ====================

class AudioProcessor(AudioProcessorBase):
    """Procesador de audio para WebRTC sin dependencia directa de av"""
    
    def __init__(self):
        self.audio_buffer = []
        self.buffer_size = 4096
        self.sample_rate = 16000
        
    def recv(self, frame):
        """Procesa frames de audio entrantes"""
        # El frame ya viene como audio data
        if hasattr(st.session_state, 'audio_queue'):
            # Convertir el frame a bytes si es necesario
            audio_data = frame.to_ndarray() if hasattr(frame, 'to_ndarray') else frame
            
            # Normalizar a 16-bit PCM
            if isinstance(audio_data, np.ndarray):
                # Asegurar que es mono
                if len(audio_data.shape) > 1:
                    audio_data = np.mean(audio_data, axis=1)
                
                # Convertir a 16-bit
                audio_data = np.clip(audio_data * 32767, -32768, 32767)
                audio_bytes = audio_data.astype(np.int16).tobytes()
            else:
                audio_bytes = audio_data
            
            # Agregar al buffer
            self.audio_buffer.append(audio_bytes)
            
            # Enviar cuando el buffer esté lleno
            if len(self.audio_buffer) >= 8:
                combined = b''.join(self.audio_buffer)
                self.audio_buffer = []
                
                # Agregar a la cola para envío
                if hasattr(st.session_state, 'audio_queue'):
                    try:
                        st.session_state.audio_queue.put_nowait(combined)
                    except:
                        pass
        
        return frame

# ==================== CLIENTE ASSEMBLYAI ====================

class AssemblyAIClient:
    """Cliente WebSocket simplificado para AssemblyAI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.ws = None
        self.session_id = None
        self.is_connected = False
        
    async def connect(self):
        """Conecta al WebSocket de AssemblyAI"""
        try:
            url = "wss://api.assemblyai.com/v2/realtime/ws?sample_rate=16000"
            headers = {"Authorization": self.api_key}
            
            self.ws = await websockets.connect(url, extra_headers=headers)
            
            # Recibir mensaje de inicio
            msg = await self.ws.recv()
            data = json.loads(msg)
            
            if data.get("message_type") == "SessionBegins":
                self.session_id = data.get("session_id")
                self.is_connected = True
                logger.info(f"Conectado - Sesión: {self.session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error conectando: {e}")
            
        return False
    
    async def send_audio(self, audio_bytes: bytes):
        """Envía audio al WebSocket"""
        if not self.is_connected or not self.ws:
            return False
            
        try:
            audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
            await self.ws.send(json.dumps({"audio_data": audio_b64}))
            return True
        except Exception as e:
            logger.error(f"Error enviando audio: {e}")
            return False
    
    async def receive_transcript(self):
        """Recibe transcripciones"""
        if not self.ws:
            return None
            
        try:
            msg = await asyncio.wait_for(self.ws.recv(), timeout=1.0)
            data = json.loads(msg)
            
            if data.get("message_type") == "FinalTranscript":
                return data.get("text", "")
            elif data.get("message_type") == "PartialTranscript":
                return f"[parcial] {data.get('text', '')}"
                
        except asyncio.TimeoutError:
            pass
        except Exception as e:
            logger.error(f"Error recibiendo: {e}")
            
        return None
    
    async def close(self):
        """Cierra la conexión"""
        self.is_connected = False
        if self.ws:
            try:
                await self.ws.send(json.dumps({"terminate_session": True}))
                await self.ws.close()
            except:
                pass
        self.ws = None

# ==================== SISTEMA DE TRANSCRIPCIÓN ====================

class TranscriptionSystem:
    """Sistema principal de transcripción"""
    
    def __init__(self):
        self.client = AssemblyAIClient(ASSEMBLYAI_API_KEY)
        self.transcripts = []
        self.is_running = False
        self.audio_queue = queue.Queue()
        
    async def start(self):
        """Inicia el sistema"""
        if await self.client.connect():
            self.is_running = True
            # Iniciar procesamiento en background
            asyncio.create_task(self.process_audio())
            asyncio.create_task(self.receive_transcripts())
            return True
        return False
    
    async def process_audio(self):
        """Procesa audio de la cola"""
        while self.is_running:
            try:
                # Obtener audio de la cola
                audio = await asyncio.get_event_loop().run_in_executor(
                    None, self.audio_queue.get, True, 0.1
                )
                
                # Enviar a AssemblyAI
                await self.client.send_audio(audio)
                
            except queue.Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.error(f"Error procesando audio: {e}")
    
    async def receive_transcripts(self):
        """Recibe transcripciones"""
        while self.is_running:
            transcript = await self.client.receive_transcript()
            if transcript:
                self.transcripts.append(transcript)
                
                # Actualizar UI
                if 'live_transcript' not in st.session_state:
                    st.session_state.live_transcript = []
                st.session_state.live_transcript.append(transcript)
            
            await asyncio.sleep(0.1)
    
    async def stop(self):
        """Detiene el sistema"""
        self.is_running = False
        await self.client.close()
    
    def get_full_transcript(self):
        """Obtiene transcripción completa"""
        # Filtrar solo transcripciones finales
        final_transcripts = [t for t in self.transcripts if not t.startswith("[parcial]")]
        return " ".join(final_transcripts)

# ==================== PROCESAMIENTO LLM ====================

class LLMProcessor:
    """Procesador de texto con LLM"""
    
    @staticmethod
    async def process_with_gemini(text: str, prompt_type: str = "nota"):
        """Procesa con Gemini"""
        try:
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            prompts = {
                "nota": f"Genera una nota médica estructurada basada en esta transcripción:\n{text}",
                "resumen": f"Resume los puntos clave de esta consulta:\n{text}"
            }
            
            prompt = prompts.get(prompt_type, prompts["nota"])
            response = model.generate_content(prompt)
            
            return response.text
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    @staticmethod
    async def process_with_deepinfra(text: str, prompt_type: str = "nota"):
        """Procesa con DeepInfra"""
        try:
            prompts = {
                "nota": f"Genera una nota médica estructurada basada en esta transcripción:\n{text}",
                "resumen": f"Resume los puntos clave de esta consulta:\n{text}"
            }
            
            response = deepinfra_client.chat.completions.create(
                model='Qwen/Qwen2.5-72B-Instruct',
                messages=[
                    {"role": "system", "content": "Eres un médico especializado."},
                    {"role": "user", "content": prompts.get(prompt_type, prompts["nota"])}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"Error: {str(e)}"

# ==================== INTERFAZ PRINCIPAL ====================

def init_session_state():
    """Inicializa estado de sesión"""
    if 'system' not in st.session_state:
        st.session_state.system = None
    if 'is_recording' not in st.session_state:
        st.session_state.is_recording = False
    if 'live_transcript' not in st.session_state:
        st.session_state.live_transcript = []
    if 'audio_queue' not in st.session_state:
        st.session_state.audio_queue = queue.Queue()
    if 'processed_notes' not in st.session_state:
        st.session_state.processed_notes = []

def main():
    """Aplicación principal"""
    
    init_session_state()
    
    st.title("🎙️ Sistema de Transcripción Médica")
    
    # Controles
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("▶️ Iniciar", disabled=st.session_state.is_recording):
            st.session_state.system = TranscriptionSystem()
            st.session_state.system.audio_queue = st.session_state.audio_queue
            
            # Iniciar sistema
            loop = asyncio.new_event_loop()
            if loop.run_until_complete(st.session_state.system.start()):
                st.session_state.is_recording = True
                st.success("✅ Grabación iniciada")
                st.rerun()
            else:
                st.error("❌ Error al iniciar")
    
    with col2:
        if st.button("⏹️ Detener", disabled=not st.session_state.is_recording):
            if st.session_state.system:
                loop = asyncio.new_event_loop()
                loop.run_until_complete(st.session_state.system.stop())
            
            st.session_state.is_recording = False
            st.info("Grabación detenida")
            st.rerun()
    
    with col3:
        if st.button("🗑️ Limpiar"):
            st.session_state.live_transcript = []
            st.session_state.processed_notes = []
            st.session_state.audio_queue = queue.Queue()
            if st.session_state.system:
                st.session_state.system = None
            st.rerun()
    
    # WebRTC Streamer
    if st.session_state.is_recording:
        st.info("🔴 Grabando... Hable cerca del micrófono")
        
        webrtc_ctx = webrtc_streamer(
            key="speech",
            mode=WebRtcMode.SENDONLY,
            rtc_configuration=RTC_CONFIGURATION,
            media_stream_constraints={"video": False, "audio": True},
            audio_processor_factory=AudioProcessor,
            async_processing=True,
        )
    
    # Mostrar transcripción
    if st.session_state.live_transcript:
        st.text_area(
            "📝 Transcripción:",
            "\n".join(st.session_state.live_transcript[-20:]),
            height=300
        )
        
        # Procesar con LLM
        col1, col2 = st.columns([3, 1])
        
        with col1:
            model = st.selectbox("Modelo:", ["Gemini", "DeepInfra", "Ambos"])
        
        with col2:
            if st.button("🔮 Procesar"):
                text = st.session_state.system.get_full_transcript() if st.session_state.system else ""
                
                if text:
                    with st.spinner("Procesando..."):
                        loop = asyncio.new_event_loop()
                        
                        if model == "Ambos":
                            gem_result = loop.run_until_complete(
                                LLMProcessor.process_with_gemini(text)
                            )
                            deep_result = loop.run_until_complete(
                                LLMProcessor.process_with_deepinfra(text)
                            )
                            
                            col1, col2 = st.columns(2)
                            with col1:
                                st.text_area("Gemini:", gem_result, height=300)
                            with col2:
                                st.text_area("DeepInfra:", deep_result, height=300)
                        else:
                            if model == "Gemini":
                                result = loop.run_until_complete(
                                    LLMProcessor.process_with_gemini(text)
                                )
                            else:
                                result = loop.run_until_complete(
                                    LLMProcessor.process_with_deepinfra(text)
                                )
                            
                            st.text_area("Resultado:", result, height=400)
                            
                            # Botón de descarga
                            st.download_button(
                                "💾 Descargar",
                                data=result,
                                file_name=f"nota_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                                mime="text/plain"
                            )

if __name__ == "__main__":
    main()
