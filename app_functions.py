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
import time

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)

def save_audio_bytes_to_file(audio_bytes: bytes, suffix: str = ".webm") -> Path:
    """Guarda bytes de audio a un archivo en disco con nombre único."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = RECORDINGS_DIR / f"rec_{ts}{suffix}"
    with open(file_path, "wb") as f:
        f.write(audio_bytes)
    return file_path

def get_audio_recorder_html():
    """
    Componente HTML/JS para grabación de audio compatible con móvil y desktop.
    Utiliza MediaRecorder API con fallbacks y optimizaciones.
    """
    return """
    <div id="audioRecorder">
        <style>
            .recorder-container {
                padding: 20px;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 15px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.2);
                margin: 20px 0;
            }
            .recorder-controls {
                display: flex;
                gap: 15px;
                justify-content: center;
                align-items: center;
                flex-wrap: wrap;
            }
            .recorder-btn {
                padding: 12px 24px;
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 25px;
                cursor: pointer;
                transition: all 0.3s ease;
                min-width: 120px;
            }
            .record-btn {
                background: #28a745;
                color: white;
            }
            .record-btn:hover:not(:disabled) {
                background: #218838;
                transform: scale(1.05);
            }
            .stop-btn {
                background: #dc3545;
                color: white;
            }
            .stop-btn:hover:not(:disabled) {
                background: #c82333;
                transform: scale(1.05);
            }
            .recorder-btn:disabled {
                opacity: 0.5;
                cursor: not-allowed;
            }
            .status-display {
                text-align: center;
                margin: 15px 0;
                font-size: 18px;
                color: white;
                font-weight: 500;
            }
            .timer {
                font-family: 'Courier New', monospace;
                font-size: 24px;
                color: #ffd700;
                margin: 10px 0;
            }
            .audio-preview {
                width: 100%;
                margin: 15px 0;
                border-radius: 10px;
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0.7); }
                70% { box-shadow: 0 0 0 10px rgba(255, 0, 0, 0); }
                100% { box-shadow: 0 0 0 0 rgba(255, 0, 0, 0); }
            }
            .recording {
                animation: pulse 1.5s infinite;
            }
        </style>
        
        <div class="recorder-container">
            <div class="status-display" id="status">🎙️ Listo para grabar</div>
            <div class="timer" id="timer">00:00</div>
            
            <div class="recorder-controls">
                <button id="recordBtn" class="recorder-btn record-btn">
                    🔴 Iniciar Grabación
                </button>
                <button id="stopBtn" class="recorder-btn stop-btn" disabled>
                    ⏹️ Detener
                </button>
            </div>
            
            <audio id="audioPreview" class="audio-preview" controls style="display:none;"></audio>
        </div>
    </div>
    
    <script>
    (function() {
        let mediaRecorder;
        let audioChunks = [];
        let isRecording = false;
        let startTime;
        let timerInterval;
        let stream;
        
        const recordBtn = document.getElementById('recordBtn');
        const stopBtn = document.getElementById('stopBtn');
        const statusDiv = document.getElementById('status');
        const timerDiv = document.getElementById('timer');
        const audioPreview = document.getElementById('audioPreview');
        
        // Configuración de audio optimizada para voz
        const constraints = {
            audio: {
                echoCancellation: true,
                noiseSuppression: true,
                autoGainControl: true,
                sampleRate: 16000,
                channelCount: 1
            }
        };
        
        // Detectar el mejor formato de audio soportado
        function getSupportedMimeType() {
            const types = [
                'audio/webm;codecs=opus',
                'audio/webm',
                'audio/ogg;codecs=opus',
                'audio/mp4',
                'audio/mpeg'
            ];
            
            for (let type of types) {
                if (MediaRecorder.isTypeSupported(type)) {
                    return type;
                }
            }
            return 'audio/webm'; // fallback
        }
        
        // Actualizar timer
        function updateTimer() {
            if (!startTime) return;
            const elapsed = Date.now() - startTime;
            const seconds = Math.floor(elapsed / 1000);
            const minutes = Math.floor(seconds / 60);
            const displaySeconds = seconds % 60;
            timerDiv.textContent = 
                String(minutes).padStart(2, '0') + ':' + 
                String(displaySeconds).padStart(2, '0');
        }
        
        // Iniciar grabación
        async function startRecording() {
            try {
                // Solicitar permisos de micrófono
                stream = await navigator.mediaDevices.getUserMedia(constraints);
                
                const mimeType = getSupportedMimeType();
                const options = {
                    mimeType: mimeType,
                    audioBitsPerSecond: 128000
                };
                
                mediaRecorder = new MediaRecorder(stream, options);
                audioChunks = [];
                
                mediaRecorder.ondataavailable = (event) => {
                    if (event.data.size > 0) {
                        audioChunks.push(event.data);
                    }
                };
                
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: mimeType });
                    const audioUrl = URL.createObjectURL(audioBlob);
                    
                    // Mostrar preview
                    audioPreview.src = audioUrl;
                    audioPreview.style.display = 'block';
                    
                    // Convertir a base64 y enviar a Streamlit
                    const reader = new FileReader();
                    reader.onloadend = () => {
                        const base64Audio = reader.result.split(',')[1];
                        
                        // Enviar a Streamlit usando el componente
                        window.parent.postMessage({
                            type: 'streamlit:setComponentValue',
                            data: {
                                audio_data: base64Audio,
                                mime_type: mimeType,
                                duration: (Date.now() - startTime) / 1000,
                                size: audioBlob.size
                            }
                        }, '*');
                    };
                    reader.readAsDataURL(audioBlob);
                    
                    // Limpiar stream
                    if (stream) {
                        stream.getTracks().forEach(track => track.stop());
                    }
                };
                
                // Comenzar grabación
                mediaRecorder.start(1000); // Chunks cada segundo
                isRecording = true;
                startTime = Date.now();
                
                // UI updates
                recordBtn.disabled = true;
                stopBtn.disabled = false;
                recordBtn.classList.add('recording');
                statusDiv.textContent = '🔴 Grabando...';
                
                // Iniciar timer
                timerInterval = setInterval(updateTimer, 100);
                
            } catch (error) {
                console.error('Error al iniciar grabación:', error);
                statusDiv.textContent = '❌ Error: ' + error.message;
                
                // Mensajes específicos para errores comunes
                if (error.name === 'NotAllowedError') {
                    alert('Por favor, permite el acceso al micrófono para continuar.');
                } else if (error.name === 'NotFoundError') {
                    alert('No se encontró ningún micrófono. Verifica tu dispositivo.');
                } else if (error.name === 'NotReadableError') {
                    alert('El micrófono está siendo usado por otra aplicación.');
                }
            }
        }
        
        // Detener grabación
        function stopRecording() {
            if (mediaRecorder && isRecording) {
                mediaRecorder.stop();
                isRecording = false;
                
                // UI updates
                recordBtn.disabled = false;
                stopBtn.disabled = true;
                recordBtn.classList.remove('recording');
                statusDiv.textContent = '✅ Grabación completada';
                
                // Detener timer
                clearInterval(timerInterval);
            }
        }
        
        // Event listeners
        recordBtn.addEventListener('click', startRecording);
        stopBtn.addEventListener('click', stopRecording);
        
        // Cleanup al salir
        window.addEventListener('beforeunload', () => {
            if (isRecording) {
                stopRecording();
            }
        });
    })();
    </script>
    """

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

import asyncio
from typing import Optional, List
import aiohttp
import backoff
from openai import OpenAI
import streamlit as st

class WhisperTranscriber:
    """Cliente robusto para transcripción con Whisper API."""
    
    def __init__(
        self, 
        api_key: str,
        base_url: str = "https://api.deepinfra.com/v1/openai",
        model: str = "openai/whisper-large-v3-turbo",
        max_retries: int = 3,
        timeout: int = 300
    ):
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        
    @backoff.on_exception(
        backoff.expo,
        (Exception,),
        max_tries=3,
        max_time=300,
        on_backoff=lambda details: st.info(f"Reintentando... Intento {details['tries']}")
    )
    def transcribe_chunk(
        self, 
        audio_bytes: bytes,
        language: str = "es",
        prompt: Optional[str] = None
    ) -> Optional[str]:
        """
        Transcribe un chunk de audio con reintentos exponenciales.
        
        Args:
            audio_bytes: Audio en formato WAV
            language: Código de idioma
            prompt: Prompt opcional para mejorar la transcripción
        
        Returns:
            Texto transcrito o None si falla
        """
        try:
            # Crear archivo temporal para el audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_file.write(audio_bytes)
                tmp_file_path = tmp_file.name
            
            # Preparar parámetros
            params = {
                "model": self.model,
                "language": language,
                "response_format": "text",
                "temperature": 0.2
            }
            
            if prompt:
                params["prompt"] = prompt
            
            # Realizar transcripción
            with open(tmp_file_path, "rb") as audio_file:
                response = self.client.audio.transcriptions.create(
                    file=audio_file,
                    **params
                )
            
            # Limpiar archivo temporal
            os.unlink(tmp_file_path)
            
            return response.text if hasattr(response, 'text') else str(response)
            
        except Exception as e:
            st.error(f"Error en transcripción: {str(e)}")
            
            # Limpiar archivo temporal si existe
            if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
            
            raise  # Re-raise para que backoff lo maneje
    
    def transcribe_with_chunks(
        self,
        audio_chunks: List[bytes],
        language: str = "es",
        show_progress: bool = True
    ) -> str:
        """
        Transcribe múltiples chunks y los une.
        
        Args:
            audio_chunks: Lista de chunks de audio
            language: Código de idioma
            show_progress: Mostrar barra de progreso
        
        Returns:
            Transcripción completa
        """
        transcriptions = []
        
        if show_progress:
            progress_bar = st.progress(0)
            status_text = st.empty()
        
        # Contexto para mejorar la continuidad entre chunks
        context = "Transcripción de consulta médica en español. "
        
        for i, chunk in enumerate(audio_chunks):
            if show_progress:
                progress = (i + 1) / len(audio_chunks)
                progress_bar.progress(progress)
                status_text.text(f"Transcribiendo parte {i+1} de {len(audio_chunks)}...")
            
            # Usar el final de la transcripción anterior como contexto
            if transcriptions:
                # Tomar las últimas 50 palabras como contexto
                last_words = ' '.join(transcriptions[-1].split()[-50:])
                prompt = context + last_words
            else:
                prompt = context
            
            try:
                transcription = self.transcribe_chunk(chunk, language, prompt)
                if transcription:
                    transcriptions.append(transcription.strip())
            except Exception as e:
                st.warning(f"Fallo en chunk {i+1}: {str(e)}")
                continue
        
        if show_progress:
            progress_bar.empty()
            status_text.empty()
        
        # Unir transcripciones eliminando posibles duplicados en los bordes
        if not transcriptions:
            return ""
        
        full_text = transcriptions[0]
        for i in range(1, len(transcriptions)):
            # Buscar overlap entre el final del texto anterior y el inicio del siguiente
            overlap = self._find_overlap(full_text, transcriptions[i])
            if overlap > 0:
                full_text += transcriptions[i][overlap:]
            else:
                full_text += " " + transcriptions[i]
        
        return full_text
    
    def _find_overlap(self, text1: str, text2: str, max_overlap: int = 100) -> int:
        """Encuentra el overlap entre dos textos."""
        words1 = text1.split()
        words2 = text2.split()
        
        max_check = min(max_overlap, len(words1), len(words2))
        
        for i in range(max_check, 0, -1):
            if words1[-i:] == words2[:i]:
                return len(' '.join(words2[:i])) + 1  # +1 for space
        
        return 0
import base64
import tempfile
from typing import Optional, Tuple, List
import numpy as np
from pydub import AudioSegment
from pydub.exceptions import CouldntDecodeError
import io
import time
import streamlit as st

def process_audio_data(
    base64_audio: str, 
    mime_type: str = "audio/webm",
    max_size_mb: float = 25.0,
    chunk_duration_ms: int = 600000  # 10 minutos
) -> Tuple[Optional[bytes], Optional[List[bytes]], dict]:
    """
    Procesa audio base64, convierte a formato compatible y divide en chunks si es necesario.
    
    Args:
        base64_audio: Audio en formato base64
        mime_type: Tipo MIME del audio
        max_size_mb: Tamaño máximo por chunk en MB
        chunk_duration_ms: Duración máxima por chunk en milisegundos
    
    Returns:
        Tupla (audio_completo, lista_chunks, metadata)
    """
    metadata = {
        'original_size': 0,
        'processed_size': 0,
        'duration_ms': 0,
        'num_chunks': 0,
        'format': 'wav',
        'sample_rate': 16000,
        'channels': 1,
        'errors': []
    }
    
    try:
        # Decodificar base64
        audio_bytes = base64.b64decode(base64_audio)
        metadata['original_size'] = len(audio_bytes)
        
        # Crear objeto AudioSegment
        audio_io = io.BytesIO(audio_bytes)
        
        # Intentar decodificar con diferentes formatos
        audio = None
        for fmt in ['webm', 'ogg', 'mp4', 'mp3', 'wav']:
            try:
                audio = AudioSegment.from_file(audio_io, format=fmt)
                break
            except:
                audio_io.seek(0)
                continue
        
        if audio is None:
            raise CouldntDecodeError("No se pudo decodificar el audio")
        
        # Normalizar audio para Whisper (mono, 16kHz)
        audio = audio.set_channels(1)
        audio = audio.set_frame_rate(16000)
        
        # Normalizar volumen
        target_dBFS = -20
        change_in_dBFS = target_dBFS - audio.dBFS
        if abs(change_in_dBFS) > 0.5:
            audio = audio.apply_gain(change_in_dBFS)
        
        metadata['duration_ms'] = len(audio)
        
        # Exportar audio completo a WAV
        audio_buffer = io.BytesIO()
        audio.export(audio_buffer, format="wav")
        audio_buffer.seek(0)
        complete_audio = audio_buffer.getvalue()
        metadata['processed_size'] = len(complete_audio)
        
        # Verificar si necesita chunking
        size_mb = len(complete_audio) / (1024 * 1024)
        
        chunks = []
        if size_mb > max_size_mb or metadata['duration_ms'] > chunk_duration_ms:
            # Dividir en chunks
            num_chunks = max(
                int(np.ceil(size_mb / max_size_mb)),
                int(np.ceil(metadata['duration_ms'] / chunk_duration_ms))
            )
            
            chunk_duration = metadata['duration_ms'] // num_chunks
            
            for i in range(num_chunks):
                start_ms = i * chunk_duration
                end_ms = min((i + 1) * chunk_duration, metadata['duration_ms'])
                
                chunk = audio[start_ms:end_ms]
                
                # Añadir overlap de 500ms para evitar cortes en palabras
                if i > 0:
                    overlap_start = max(0, start_ms - 500)
                    chunk = audio[overlap_start:end_ms]
                
                chunk_buffer = io.BytesIO()
                chunk.export(chunk_buffer, format="wav")
                chunk_buffer.seek(0)
                chunks.append(chunk_buffer.getvalue())
            
            metadata['num_chunks'] = len(chunks)
        
        return complete_audio, chunks if chunks else None, metadata
        
    except Exception as e:
        metadata['errors'].append(str(e))
        st.error(f"Error procesando audio: {str(e)}")
        return None, None, metadata

import streamlit.components.v1 as components
import json
from datetime import datetime
import hashlib

def audio_recorder_transcriber_v2(
    nota: str,
    api_key: str,
    base_url: str = "https://api.deepinfra.com/v1/openai"
) -> Optional[str]:
    """
    Sistema completo de grabación y transcripción de audio con soporte móvil.
    
    Args:
        nota: Tipo de nota ('primera', 'primera_paido', 'subsecuente')
        api_key: API key para el servicio de transcripción
        base_url: URL base de la API
    
    Returns:
        Transcripción procesada o None
    """
    
    # Inicializar session state con keys únicas
    state_keys = {
        'audio_data': f'audio_data_{nota}',
        'audio_metadata': f'audio_metadata_{nota}',
        'transcription': f'transcription_{nota}',
        'is_processing': f'is_processing_{nota}',
        'audio_hash': f'audio_hash_{nota}',
        'show_recorder': f'show_recorder_{nota}'
    }
    
    # Inicializar estados
    for key, state_key in state_keys.items():
        if state_key not in st.session_state:
            if key in ['is_processing', 'show_recorder']:
                st.session_state[state_key] = False if key == 'is_processing' else True
            else:
                st.session_state[state_key] = None
    
    # UI Principal
    st.markdown("### 🎙️ Sistema de Grabación y Transcripción")
    
    # Contenedor para el grabador
    if st.session_state[state_keys['show_recorder']]:
        with st.container():
            # Insertar componente HTML del grabador
            audio_component = components.html(
                get_audio_recorder_html(),
                height=400,
                scrolling=False
            )
    
    # Sección de controles
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        # Simulación de recepción de datos (en producción, usar JavaScript postMessage)
        uploaded_audio = st.file_uploader(
            "O sube un archivo de audio",
            type=['wav', 'mp3', 'webm', 'ogg', 'mp4'],
            key=f"uploader_{nota}",
            help="Formatos soportados: WAV, MP3, WebM, OGG, MP4"
        )
        
        if uploaded_audio:
            audio_bytes = uploaded_audio.read()
            audio_b64 = base64.b64encode(audio_bytes).decode()
            
            # Calcular hash para detectar cambios
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            if audio_hash != st.session_state[state_keys['audio_hash']]:
                st.session_state[state_keys['audio_data']] = audio_b64
                st.session_state[state_keys['audio_hash']] = audio_hash
                st.session_state[state_keys['audio_metadata']] = {
                    'mime_type': uploaded_audio.type,
                    'size': len(audio_bytes),
                    'name': uploaded_audio.name
                }
                st.success("✅ Audio cargado correctamente")
    
    with col2:
        if st.button(
            "🔄 Nuevo Audio",
            use_container_width=True,
            disabled=st.session_state[state_keys['is_processing']]
        ):
            # Limpiar audio actual
            st.session_state[state_keys['audio_data']] = None
            st.session_state[state_keys['audio_metadata']] = None
            st.session_state[state_keys['audio_hash']] = None
            st.session_state[state_keys['show_recorder']] = True
            st.rerun()
    
    with col3:
        # Botón de transcripción
        can_transcribe = (
            st.session_state[state_keys['audio_data']] is not None and 
            not st.session_state[state_keys['is_processing']]
        )
        
        if st.button(
            "📝 Transcribir",
            use_container_width=True,
            disabled=not can_transcribe,
            type="primary" if can_transcribe else "secondary"
        ):
            st.session_state[state_keys['is_processing']] = True
            st.rerun()
    
    with col4:
        if st.button(
            "🗑️ Limpiar Todo",
            use_container_width=True,
            disabled=st.session_state[state_keys['is_processing']]
        ):
            for state_key in state_keys.values():
                if 'show_recorder' not in state_key:
                    st.session_state[state_key] = None
            st.session_state[state_keys['show_recorder']] = True
            st.success("✅ Limpieza completa")
            time.sleep(1)
            st.rerun()
    
    # Mostrar información del audio
    if st.session_state[state_keys['audio_data']] and st.session_state[state_keys['audio_metadata']]:
        with st.expander("📊 Información del Audio", expanded=True):
            metadata = st.session_state[state_keys['audio_metadata']]
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                size_mb = metadata.get('size', 0) / (1024 * 1024)
                st.metric("Tamaño", f"{size_mb:.2f} MB")
            with col_info2:
                duration = metadata.get('duration', 0)
                if duration:
                    st.metric("Duración", f"{duration:.1f} seg")
            with col_info3:
                st.metric("Formato", metadata.get('mime_type', 'Unknown'))
            
            # Mostrar reproductor
            if st.session_state[state_keys['audio_data']]:
                audio_bytes = base64.b64decode(st.session_state[state_keys['audio_data']])
                st.audio(audio_bytes, format=metadata.get('mime_type', 'audio/wav'))
    
    # Proceso de transcripción
    if st.session_state[state_keys['is_processing']] and st.session_state[state_keys['audio_data']]:
        
        with st.container():
            st.markdown("---")
            
            with st.status("🔄 Procesando transcripción...", expanded=True) as status:
                
                try:
                    # Paso 1: Procesar audio
                    status.update(label="🎵 Procesando audio...", state="running")
                    
                    audio_complete, audio_chunks, audio_metadata = process_audio_data(
                        st.session_state[state_keys['audio_data']],
                        st.session_state[state_keys['audio_metadata']].get('mime_type', 'audio/webm')
                    )
                    
                    if not audio_complete:
                        raise ValueError("Error al procesar el audio")
                    
                    # Mostrar información del procesamiento
                    st.info(f"""
                    📊 **Audio procesado:**
                    - Tamaño original: {audio_metadata['original_size'] / (1024*1024):.2f} MB
                    - Tamaño procesado: {audio_metadata['processed_size'] / (1024*1024):.2f} MB
                    - Duración: {audio_metadata['duration_ms'] / 1000:.1f} segundos
                    - Chunks: {audio_metadata['num_chunks'] if audio_metadata['num_chunks'] > 0 else 1}
                    """)
                    
                    # Paso 2: Transcribir
                    status.update(label="🎯 Transcribiendo audio...", state="running")
                    
                    transcriber = WhisperTranscriber(api_key=api_key, base_url=base_url)
                    
                    if audio_chunks:
                        # Transcribir por chunks
                        st.info(f"📦 Procesando {len(audio_chunks)} segmentos...")
                        transcription = transcriber.transcribe_with_chunks(
                            audio_chunks,
                            language="es",
                            show_progress=True
                        )
                    else:
                        # Transcribir audio completo
                        transcription = transcriber.transcribe_chunk(
                            audio_complete,
                            language="es"
                        )
                    
                    if not transcription:
                        raise ValueError("La transcripción está vacía")
                    
                    # Paso 3: Generar resumen
                    status.update(label="📋 Generando resumen clínico...", state="running")
                    
                    # Usar las funciones existentes de resumen
                    summary = resumen_transcripcion(transcription, nota)
                    
                    # Intentar segundo resumen si está disponible
                    try:
                        summary2 = resumen_transcripcion2(transcription, nota)
                        if summary2:
                            final_result = f"{summary}\n\n--- VERSIÓN ALTERNATIVA ---\n\n{summary2}"
                        else:
                            final_result = summary
                    except:
                        final_result = summary
                    
                    # Guardar resultado
                    st.session_state[state_keys['transcription']] = final_result
                    
                    status.update(label="✅ Transcripción completada", state="complete")
                    st.success("🎉 Proceso completado exitosamente")
                    
                except Exception as e:
                    status.update(label=f"❌ Error: {str(e)}", state="error")
                    st.error(f"Error durante el procesamiento: {str(e)}")
                    
                finally:
                    st.session_state[state_keys['is_processing']] = False
                    time.sleep(2)
                    st.rerun()
    
    # Mostrar transcripción si existe
    if st.session_state[state_keys['transcription']]:
        st.markdown("---")
        st.markdown("### 📄 Resultado de la Transcripción")
        
        # Opciones de visualización
        col_view1, col_view2, col_view3 = st.columns([2, 1, 1])
        
        with col_view1:
            view_expanded = st.checkbox("Expandir resultado", value=True)
        
        with col_view2:
            if st.button("📋 Copiar al portapapeles"):
                st.write("Copiado!")  # En producción, usar JavaScript para copiar
        
        with col_view3:
            # Descargar como archivo
            st.download_button(
                "💾 Descargar TXT",
                st.session_state[state_keys['transcription']],
                file_name=f"transcripcion_{nota}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        # Mostrar transcripción
        with st.expander("Transcripción y Resumen", expanded=view_expanded):
            st.text_area(
                "",
                st.session_state[state_keys['transcription']],
                height=400,
                key=f"display_{nota}_{datetime.now().timestamp()}"
            )
    
    # Estadísticas de sesión
    with st.sidebar:
        st.markdown("### 📊 Estado de la Sesión")
        
        status_info = {
            "Audio cargado": "✅" if st.session_state[state_keys['audio_data']] else "❌",
            "Transcripción": "✅" if st.session_state[state_keys['transcription']] else "❌",
            "Procesando": "🔄" if st.session_state[state_keys['is_processing']] else "⏸️"
        }
        
        for label, status in status_info.items():
            st.write(f"{status} {label}")
    
    return st.session_state[state_keys['transcription']]
    
import streamlit.components.v1 as components
import json
from datetime import datetime
import hashlib

def audio_recorder_transcriber_v2(
    nota: str,
    api_key: str,
    base_url: str = "https://api.deepinfra.com/v1/openai"
) -> Optional[str]:
    """
    Sistema completo de grabación y transcripción de audio con soporte móvil.
    
    Args:
        nota: Tipo de nota ('primera', 'primera_paido', 'subsecuente')
        api_key: API key para el servicio de transcripción
        base_url: URL base de la API
    
    Returns:
        Transcripción procesada o None
    """
    
    # Inicializar session state con keys únicas
    state_keys = {
        'audio_data': f'audio_data_{nota}',
        'audio_metadata': f'audio_metadata_{nota}',
        'transcription': f'transcription_{nota}',
        'is_processing': f'is_processing_{nota}',
        'audio_hash': f'audio_hash_{nota}',
        'show_recorder': f'show_recorder_{nota}'
    }
    
    # Inicializar estados
    for key, state_key in state_keys.items():
        if state_key not in st.session_state:
            if key in ['is_processing', 'show_recorder']:
                st.session_state[state_key] = False if key == 'is_processing' else True
            else:
                st.session_state[state_key] = None
    
    # UI Principal
    st.markdown("### 🎙️ Sistema de Grabación y Transcripción")
    
    # Contenedor para el grabador
    if st.session_state[state_keys['show_recorder']]:
        with st.container():
            # Insertar componente HTML del grabador
            audio_component = components.html(
                get_audio_recorder_html(),
                height=400,
                scrolling=False
            )
    
    # Sección de controles
    col1, col2, col3, col4 = st.columns([2, 2, 2, 2])
    
    with col1:
        # Simulación de recepción de datos (en producción, usar JavaScript postMessage)
        uploaded_audio = st.file_uploader(
            "O sube un archivo de audio",
            type=['wav', 'mp3', 'webm', 'ogg', 'mp4'],
            key=f"uploader_{nota}",
            help="Formatos soportados: WAV, MP3, WebM, OGG, MP4"
        )
        
        if uploaded_audio:
            audio_bytes = uploaded_audio.read()
            audio_b64 = base64.b64encode(audio_bytes).decode()
            
            # Calcular hash para detectar cambios
            audio_hash = hashlib.md5(audio_bytes).hexdigest()
            
            if audio_hash != st.session_state[state_keys['audio_hash']]:
                st.session_state[state_keys['audio_data']] = audio_b64
                st.session_state[state_keys['audio_hash']] = audio_hash
                st.session_state[state_keys['audio_metadata']] = {
                    'mime_type': uploaded_audio.type,
                    'size': len(audio_bytes),
                    'name': uploaded_audio.name
                }
                st.success("✅ Audio cargado correctamente")
    
    with col2:
        if st.button(
            "🔄 Nuevo Audio",
            use_container_width=True,
            disabled=st.session_state[state_keys['is_processing']]
        ):
            # Limpiar audio actual
            st.session_state[state_keys['audio_data']] = None
            st.session_state[state_keys['audio_metadata']] = None
            st.session_state[state_keys['audio_hash']] = None
            st.session_state[state_keys['show_recorder']] = True
            st.rerun()
    
    with col3:
        # Botón de transcripción
        can_transcribe = (
            st.session_state[state_keys['audio_data']] is not None and 
            not st.session_state[state_keys['is_processing']]
        )
        
        if st.button(
            "📝 Transcribir",
            use_container_width=True,
            disabled=not can_transcribe,
            type="primary" if can_transcribe else "secondary"
        ):
            st.session_state[state_keys['is_processing']] = True
            st.rerun()
    
    with col4:
        if st.button(
            "🗑️ Limpiar Todo",
            use_container_width=True,
            disabled=st.session_state[state_keys['is_processing']]
        ):
            for state_key in state_keys.values():
                if 'show_recorder' not in state_key:
                    st.session_state[state_key] = None
            st.session_state[state_keys['show_recorder']] = True
            st.success("✅ Limpieza completa")
            time.sleep(1)
            st.rerun()
    
    # Mostrar información del audio
    if st.session_state[state_keys['audio_data']] and st.session_state[state_keys['audio_metadata']]:
        with st.expander("📊 Información del Audio", expanded=True):
            metadata = st.session_state[state_keys['audio_metadata']]
            
            col_info1, col_info2, col_info3 = st.columns(3)
            with col_info1:
                size_mb = metadata.get('size', 0) / (1024 * 1024)
                st.metric("Tamaño", f"{size_mb:.2f} MB")
            with col_info2:
                duration = metadata.get('duration', 0)
                if duration:
                    st.metric("Duración", f"{duration:.1f} seg")
            with col_info3:
                st.metric("Formato", metadata.get('mime_type', 'Unknown'))
            
            # Mostrar reproductor
            if st.session_state[state_keys['audio_data']]:
                audio_bytes = base64.b64decode(st.session_state[state_keys['audio_data']])
                st.audio(audio_bytes, format=metadata.get('mime_type', 'audio/wav'))
    
    # Proceso de transcripción
    if st.session_state[state_keys['is_processing']] and st.session_state[state_keys['audio_data']]:
        
        with st.container():
            st.markdown("---")
            
            with st.status("🔄 Procesando transcripción...", expanded=True) as status:
                
                try:
                    # Paso 1: Procesar audio
                    status.update(label="🎵 Procesando audio...", state="running")
                    
                    audio_complete, audio_chunks, audio_metadata = process_audio_data(
                        st.session_state[state_keys['audio_data']],
                        st.session_state[state_keys['audio_metadata']].get('mime_type', 'audio/webm')
                    )
                    
                    if not audio_complete:
                        raise ValueError("Error al procesar el audio")
                    
                    # Mostrar información del procesamiento
                    st.info(f"""
                    📊 **Audio procesado:**
                    - Tamaño original: {audio_metadata['original_size'] / (1024*1024):.2f} MB
                    - Tamaño procesado: {audio_metadata['processed_size'] / (1024*1024):.2f} MB
                    - Duración: {audio_metadata['duration_ms'] / 1000:.1f} segundos
                    - Chunks: {audio_metadata['num_chunks'] if audio_metadata['num_chunks'] > 0 else 1}
                    """)
                    
                    # Paso 2: Transcribir
                    status.update(label="🎯 Transcribiendo audio...", state="running")
                    
                    transcriber = WhisperTranscriber(api_key=api_key, base_url=base_url)
                    
                    if audio_chunks:
                        # Transcribir por chunks
                        st.info(f"📦 Procesando {len(audio_chunks)} segmentos...")
                        transcription = transcriber.transcribe_with_chunks(
                            audio_chunks,
                            language="es",
                            show_progress=True
                        )
                    else:
                        # Transcribir audio completo
                        transcription = transcriber.transcribe_chunk(
                            audio_complete,
                            language="es"
                        )
                    
                    if not transcription:
                        raise ValueError("La transcripción está vacía")
                    
                    # Paso 3: Generar resumen
                    status.update(label="📋 Generando resumen clínico...", state="running")
                    
                    # Usar las funciones existentes de resumen
                    summary = resumen_transcripcion(transcription, nota)
                    
                    # Intentar segundo resumen si está disponible
                    try:
                        summary2 = resumen_transcripcion2(transcription, nota)
                        if summary2:
                            final_result = f"{summary}\n\n--- VERSIÓN ALTERNATIVA ---\n\n{summary2}"
                        else:
                            final_result = summary
                    except:
                        final_result = summary
                    
                    # Guardar resultado
                    st.session_state[state_keys['transcription']] = final_result
                    
                    status.update(label="✅ Transcripción completada", state="complete")
                    st.success("🎉 Proceso completado exitosamente")
                    
                except Exception as e:
                    status.update(label=f"❌ Error: {str(e)}", state="error")
                    st.error(f"Error durante el procesamiento: {str(e)}")
                    
                finally:
                    st.session_state[state_keys['is_processing']] = False
                    time.sleep(2)
                    st.rerun()
    
    # Mostrar transcripción si existe
    if st.session_state[state_keys['transcription']]:
        st.markdown("---")
        st.markdown("### 📄 Resultado de la Transcripción")
        
        # Opciones de visualización
        col_view1, col_view2, col_view3 = st.columns([2, 1, 1])
        
        with col_view1:
            view_expanded = st.checkbox("Expandir resultado", value=True)
        
        with col_view2:
            if st.button("📋 Copiar al portapapeles"):
                st.write("Copiado!")  # En producción, usar JavaScript para copiar
        
        with col_view3:
            # Descargar como archivo
            st.download_button(
                "💾 Descargar TXT",
                st.session_state[state_keys['transcription']],
                file_name=f"transcripcion_{nota}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        # Mostrar transcripción
        with st.expander("Transcripción y Resumen", expanded=view_expanded):
            st.text_area(
                "",
                st.session_state[state_keys['transcription']],
                height=400,
                key=f"display_{nota}_{datetime.now().timestamp()}"
            )
    
    # Estadísticas de sesión
    with st.sidebar:
        st.markdown("### 📊 Estado de la Sesión")
        
        status_info = {
            "Audio cargado": "✅" if st.session_state[state_keys['audio_data']] else "❌",
            "Transcripción": "✅" if st.session_state[state_keys['transcription']] else "❌",
            "Procesando": "🔄" if st.session_state[state_keys['is_processing']] else "⏸️"
        }
        
        for label, status in status_info.items():
            st.write(f"{status} {label}")
    
    return st.session_state[state_keys['transcription']]

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


def audio_recorder_transcriber(nota: str):
    """Función mejorada para grabar, segmentar y transcribir audio desde el navegador."""
    
    def split_audio(audio_data: io.BytesIO, segment_duration_ms: int = 300000):
        """Divide el audio en fragmentos menores con mejor manejo de errores."""
        try:
            audio_size_mb = len(audio_data.getvalue()) / (1024 * 1024)
            if audio_size_mb > 25:
                st.warning(f"El archivo de audio ({audio_size_mb:.2f} MB) es muy grande. Se dividirá en segmentos.")
            
            audio = AudioSegment.from_file(audio_data, format="webm")
            duration_ms = len(audio)
            segments = []
            
            if duration_ms <= segment_duration_ms:
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
                
                audio_size_mb = len(audio_data.getvalue()) / (1024 * 1024)
                if audio_size_mb > 25:
                    st.error(f"El archivo ({audio_size_mb:.2f} MB) excede el límite de 25 MB")
                    return None
                
                response = client.audio.transcriptions.create(
                    model="openai/whisper-large-v3-turbo",
                    file=("audio.webm", audio_data, "audio/webm"),
                    language="es",
                    timeout=300
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

    def get_audio_signature(audio_bytes):
        """Genera una firma única para el audio usando características básicas."""
        if not audio_bytes:
            return None
        
        # Usar longitud + primeros y últimos bytes como firma
        length = len(audio_bytes)
        start_bytes = audio_bytes[:min(100, length)]
        end_bytes = audio_bytes[-min(100, length):] if length > 100 else b''
        
        # Crear una firma simple basada en características del audio
        signature = f"{length}_{sum(start_bytes)}_{sum(end_bytes)}"
        return signature

    def resumen_transcripcion(transcripcion, nota):
        model = genai.GenerativeModel('gemini-2.5-flash')
        if nota == "primera":
            response = model.generate_content(f'''
                INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.

                OBJETIVO: Redactar la evolución del padecimiento del paciente, desde su inicio hasta el estado actual, integrando únicamente la información clínica relevante extraída de las intervenciones del paciente durante la consulta.

                FORMATO REQUERIDO:
                - Idioma español
                - Texto en párrafos continuos (sin viñetas ni subtítulos), sin salto doble de línea
                - Extensión de entre 300 a 600 palabras según lo amerite el caso
                - Lenguaje técnico apropiado para documentación clínica
                - Escrito en tercera persona

                INCLUIR:
                - Antecedentes relevantes del padecimiento
                - Cronología detallada de síntomas y manifestaciones
                - Cambios en la severidad e intensidad a lo largo del tiempo
                - Factores desencadenantes o exacerbantes identificados
                - Estado actual del paciente

                OMITIR:
                - Toda información que no corresponda a la evolución del padecimiento del paciente, incluyendo sugerencias terapéuticas realizadas o propuestas durante la consulta
                - Información personal no relevante para la evolución
                - Recomendaciones o plan de tratamiento
                - Juicios de valor
                - Diagnósticos
                - Análisis sobre el caso
                - Resúmenes al final del texto

                IMPORTANTE: Dado que la transcripción incluye tanto preguntas del médico como respuestas del paciente, considera únicamente los fragmentos en los que el paciente describe su experiencia subjetiva. Ignora las intervenciones del médico excepto cuando sirvan para contextualizar una respuesta del paciente.

                ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS A CONTINUACIÓN:

                        Ejemplo 1:
                        “Cuadro actual de aproximadamente 11 meses de evolución, de inicio insidioso, curso continuo y tendiente al empeoramiento, en el contexto de un trastorno depresivo recurrente que evoluciona hacia un trastorno depresivo persistente, desencadenado por conflictos en la relación con el padre de su hijo y agravado por dependencia emocional, aislamiento social y dificultades económicas.
                        Por interrogatorio directo, la paciente refiere que desde entonces comenzó con estado de ánimo predominantemente deprimido, tendencia al llanto, apatía con pérdida del interés por actividades que previamente disfrutaba dejando de arreglarse, maquillarse y salir con amigas. Presenta hiporexia con pérdida de 8 kg en aproximadamente 7 meses con fluctuaciones en el peso; hay insomnio mixto con múltiples despertares para verificar a su hijo. Se agregaron problemas de concentración con olvidos frecuentes incluyendo la administración de medicamentos, enlentecimiento psicomotriz y fatiga.

                        Hay pensamientos persistentes de culpa relacionados con su embarazo y la percepción de "decepcionar" a sus padres, así como ideas de minusvalía "no sirvo para nada", "soy una mantenida", "les he fallado". Se añadieron pensamientos pasivos de muerte "sería mejor no estar" aunque sin ideación suicida estructurada. Presenta ansiedad con predominio de pensamientos catastróficos en relación a su familia, cefalea tipo migraña y estreñimiento.

                        Hace aproximadamente 6 meses inició tratamiento con duloxetina 60mg/día notando mejoría parcial de síntomas aunque sin remisión completa. Hace un mes, tras descubrir una presunta infidelidad de su expareja, presenta exacerbación de síntomas depresivos con deterioro en autocuidado llegando a espaciar el baño hasta por una semana, mayor aislamiento social y inicio de consumo diario de alcohol (3 cervezas) como mecanismo de afrontamiento.

                        Los síntomas han impactado significativamente en su funcionalidad, presentando deterioro en el autocuidado, dificultad para realizar las actividades de rehabilitación de su hijo y aislamiento social. Por lo anterior y el aumento de los síntomas ansiosos así como la perdida de motivación que decide acudir a consulta.”

                        Ejemplo 2:
                        “En el contexto de una historia de múltiples episodios depresivos, inicia su padecimiento actual en abril 2023 de forma insidiosa, continua y tendiente al empeoramiento sin un desencadenante aparente y agravado por deprivación académica, dificultades económicas, conflictos de pareja. Según refiere, desde entonces, comenzó con un estado de ánimo predominantemente deprimido, tendencia al llanto, apatía con perdida del interés por actividades que previamente daban placer dejándo de disfrutar sus actividades del día dejándo de asear su casa y descuidando su autocuidado. A lo anterior se añadieron hiporexia con perdida de entre 6 y 7 kg en 6 messes; hay insomnio mixto con latencia de conciliación de unas 2 horasy al menos 3 despertares; dificultades para la concentración con perdida de objetos y dificultad para mantener el hilo de conversaciones; enlentecimiento psicomotriz. Ha notado la presencia de pensamientos de culpa, minusvalía y pasivos de muerte "me siento insuficiente... siento que no le intereso a nadie, me rechazan y he pensado en mejor desaparecer [sic paciente]". A lo anterior se añadieron ansiedad flotante, nerviosísmo, cervicodorsalgia, aislamiento y episodios de pánico con sensación de ahogo, malestar torácico y síntomas vegetativos de 10-15 minutos de duración y que han ido incrementado en frecuencia de 1-2 / semana a 1-2 por día. Refiere que de junio a agosto presentó acoasmas fugaces con impacto en ánimo incrementando síntomas de ansiedad. En este contexto hace 1 mes, tras discutir con su madre, de forma impulsiva y con intención suicida, tomó unos 7ml de solución de clonazepam 2.5mg/ml sin necesidad de manejo intrahospitalario. Por lo anterior fue valorada hace 10 días en CEB en donde prescribieron fluoxetina con mejoría subjetiva referidade 10%. Por lo anterior es que decide acudir a valoración.”

                        Ejemplo 4:
                        “El episodio actual se da en el contexto de un patrón de conducta de inicio en la adolescencia tardía, persistentemente desadaptativo e inflexible caracterizado por sensación de vacío crónico, inestabilidad en la relaciones interpesonales y de emociones  con consecuentes conflictos con los padres y parejas; miedo al abandono que le ha condicionado mantenerse en una relación marcada por la violencia; ideas sobrevaloradas referenciales y distorsiones de la autoimagen; también ha presentado pobre tolerancia a la frustración que le conicionaron episodios de desregulación emociona con la presencia de ira desporporcionada e ipmulsividad que le generan conducta autolesivas como método de afrontamiento (cutting) y reactivación de pensamientos de muerte. Padecimiento de alrededor de 9 meses de inicio insidioso, continuo y tendiente al empeoramiento desencadenado por la muerte de la abuela y agravado por desempleo y separación del conyuge. Desde entonces ha presentado un estado de ánimo persistentemente triste, tendiente al llanto espontáneo; insomnio de inicio con latencia de conciliación de hasta 4 horas en asociación a rumiaciones entorno a su situación de pareja;  enlentecimiento psicomotor, problemas para la concentración con múltipls olvidos; hiporexia con perdida de 15 kg en un par de meses; además ha prsentado pensamientos de culpa, minusvalía y pasivos de muerte "Es mi culpa que me haya tratado así, me he fallado... a veces he pensado en no querer depesrtar pero pienso en mis hijos y pasa [sic]". De forma paralela ha presentado ansiedad flotante, cervicodorsalgia, nerviosísmo, inquietud motriz y paroxismos de exacerbación síntomas que se acompañan de descarga adrenérgica con sensación de muerte o perder el control. Hace 2 días, de forma impulsiva, tras ver su expareja con otra persona, presentó tentativa suicida abortada mediante flebotomía "me detienen mis hijos... fue el impuso en ese rato [sic]”

                        TEXTO A RESUMIR:
                        {transcripcion}
            ''')
        elif nota == 'primera_paido':
            response = model.generate_content(f'''

Instrucciones Generales
Asume el rol de un psiquiatra infantil especializado. Con base únicamente en la transcripción de consulta (que incluye intervenciones del médico, el paciente y uno de los padres), redacta la evolución detallada del padecimiento del paciente. La transcripción debe permitir identificar claramente quién interviene en cada turno, por lo que se debe realizar una reconstrucción precisa y coherente del relato clínico.

Objetivo Principal
Elaborar un informe preciso y conciso que describa la evolución del padecimiento del paciente desde su inicio hasta el estado actual, en orden cronológico y utilizando únicamente la información clínica relevante expresada por el paciente y su padre o madre (descartando las intervenciones del médico, salvo que sean necesarias para contextualizar la experiencia subjetiva).

Requisitos del Formato de la Respuesta
- Idioma: Español México.
- Estilo:
  - Un solo párrafo (sin viñetas, subtítulos ni saltos dobles de línea).
  - Redacción en tercera persona, concisa y precisa.
  - Lenguaje técnico apropiado para documentación clínica
  - Uso de lenguaje técnico propio de la psicopatología y semiología psiquiátrica.
- Extensión: La descripción principal debe tener entre 250 a 350 palabras según lo amerite el caso y sin incluir las secciones adicionales.
  - Evitar redundancias.
  - Mantener un orden cronológico.

Contenido a Incluir en la Evolución del Padecimiento
1. Datos Iniciales y Contexto:
   - Género (hombre o mujer) y grupo etario del paciente (preescolar: 0-5 años, escolar: 5-11 años, adolescente: >11 años).
   - Contexto sociofamiliar (por ejemplo, presencia o ausencia de padres, custodia, albergue, etc.) y dinámica familiar (relaciones, integración, factores parentales relevantes, eventos traumáticos, uso excesivo de dispositivos electrónicos, etc.).
2. Descripción Clínica Detallada:
   - Factores desencadenantes y exacerbantes.
   - Cronología de síntomas y manifestaciones (afectivos, ansiosos, cognitivos, conductuales, patrón de sueño, alimentación, etc.).
   - Evolución en severidad e intensidad de los síntomas a lo largo del tiempo.
   - Impacto en la funcionalidad diaria: desempeño académico, relaciones familiares, interpersonales, socialización, etc.
3. Estado Actual:
   - Síntomas presentes y la principal motivación para acudir a consulta.

Sección Adicional (Incluir al Final de la Descripción Principal)
Usa exclusivamente la información extraída de la transcripción para desarrollar lo siguiente:
1. Impresión diagnóstica
    - En base a los síntomas narrados y en base a tu conocimiento como experto en psiquiatría infantil genera tu propia e indepéndiente hipotesis diagnóstica propia acorde a los criterios diagnósticos del DSM 5 TR o CIE 10, que incluya sus especificadores.
    - Puedes mencionar diagnósticos concurrentes o complementarios
    - 1 a 2 diagnósticos diferenciales
2. Examen Mental
    - Incluye solo la información dentro de la transcripción y en caso de que no este omitela, no menciones que no esta
    - Incluye la descripción basadi en los ejemplos dados y en el siguiente orden: Apariencia (higiene, aliño), estado de alerta, atención, motricidad, estado de ánimo, afecto al momento de la entrevis. Características del discurso (si es
        epontáneo, inducido, fluido o no, parco, abundante o prolijo, coherente, congruente, volumen, velocidad y latencia de respuesta), pensamiento (lineal, circunstancial, circunloquial, tangencial, disgregado),
        presencia de psicosis (alucinaciones o delirios), ideación o fenómeno suicida, intrsopección del paciente sobre su enfermedad, juicio (2 a 7 años de edad = preoperacional, 7 a 12 años = concreta y > 12 años formal. Además si el juicio esta dentro del marco de la realidad o fuera en caso de que haya síntomas de psicosis),control de impulsos)
        Ejemplos de examen mental:
        - Ejemplo 1: Se trata hombre adolescente con adecuada higiene y aliño, alerta, atento, orientado cooperador de ánimo eutímico con un afecto congruente y resonante. Discurso inducido, fludio, coherente, congruente,
           volumen, velocidad y latencia de respuesta adecuados. Pensamiento lineal sin que al momento de la entrevista se encuentre psicosis o fenómeno suicida. Adecuada introspección, juicio concreto y buen
           control de impulsos.
        - Ejemplo 2: Se trata de mujer con adecuada higiene y aliño, alerta, atenta, orientada, cooperadora con inquietud motriz circunscrita a pies y manos. Refiere un ánimo ansioso con afecto congruente. Discurso
           inducido, parco, coherente, congruente, volumen bajo, velocidad adecuada y latencia de respuesta discretamente aumentada. Pensamiento lineal sin datos de psicosis o ideación suicida. Parcial introspección,
           juicio formal y buen control de impulsos.
        - Ejemplo 3: Hombre escolar con regular higiene y aliño, alerta, hipoproséxico, hipercinetico, incapaz de mantenerse en su sitio incluso deambulando por el consultorio. Parcialmente cooperador. Ánimo referido como irritable con
           afecto disonante. Discurso espontáneo, fluido, intrusivo, taquilálico coherente, congruente, con velocidad y volumen adecuados; latencia de respues disminuida. Pensamiento circunstancial y prolijo sin ideación suicida
           o psicosis. Pobre introspección, juicio concreto y pobre control de impulsos.
3. Interacción entre medicamentos
    - Identifica los medicamentos que esta o estará tomando y en base a conocimiento determina si hay alguna interacción entre ellos con una mención breve del tipo de interacción

Información a Omitir
- Todo dato que no esté relacionado con la evolución del padecimiento, salvo lo requerido en las secciones adicionales.
- Información personal irrelevante, sugerencias terapéuticas, planes de tratamiento, juicios de valor, diagnósticos no explícitamente mencionados en la transcripción, análisis del caso o resúmenes finales así como expresiones coloquiales salvo las cita textuales de los dichos por el paciente o su acompañante

Guías Adicionales
- Mantener la objetividad: basar el informe solo en lo expresado por el paciente y acompañante (y, en su caso, su madre para contextualizar).
- Seguir una cronología clara, desde la aparición de los síntomas hasta el estado actual.
- Integrar de forma concisa las secciones adicionales, sin redundancias.
- Descartar las intervenciones del médico, salvo cuando sean necesarias para interpretar o clarificar la experiencia subjetiva del paciente.
- No utilices la palabras "autolisis" o "autolítico"

            IMPORTANTE: IMPLEMENTA EL ESTILO, REDACCIÓN, SINTAXIS Y VOCABULARIO UTILIZADO EN LOS SIGUIENTES EJEMPLOS:

            EJEMPLO NÚMERO 1:
            "Se refiere una menor que proviene de una familia integrada, el padre era director de una secundaria, muere hace 3 años, era alcohólico. Ella refiere que tenia una relacion muy distante con el padre, "no me decía hija, me decía niña", muy pobre convivencia e interacción afectiva. Ella se ha caracterizado desde siempre de ser una niña solitaria, pocas amistades, en la escuela pobre convivencia, pero ya para 5to año con unas amigas hizo un video porno animado haciendom alución a un par de compañeros, lo que provocó que la condicionaran, y también le rompió un huevo de confeti a una maestra y tuvo un reporte. Ella señala que tuvo varios cambios de primaria por el trabajo de la madre como intendente y le toca pandemia de covid en 6to, por lo que ingresa a mitad de secundaria y mismo comportamiento de aislamiento, ella acepta que poco hizo, poco trabajó y logró terminarla y actualmente en preparatoria, ella dice que faltan mucho los maestros, que no tiene amigas y que por eso dejó de ir, así que termina con 64 y 3 materias reprobadas. La madre la refiere depresiva, siempre aislada en su habitación, no habla con nadie, irritable, intolerante, agresiva, no tolera indicaciones, tiene su habitación sucia, come mucho pues no tiene nada que hacer, se la pasa viendo videos, series, videojuegos, se dice estar ansiosa, pues piensa mucho las cosas, onicofagia, se muerde las mucosas de la boca, se siente de ánimo "regular, seria, pensativa", niega ideas de muerte o suicidio, alguna vez en 5to año y por los problemas que tuvo. Por estar en sus pensamientos no pone atención en nada y la madre se enoja pues no hace lo que le pide. Hace un mes van a psicología y esta pide que venga a psiquiatría para ser medicada. "

            EJEMPLO NÚMERO 2:
            "Menor que es identificado desde el kinder como muy inquieto, pero ahora que entra a primaria totralmente un cuadro caracterizado por inatención, disperso, inquieto, no trabaja en clase pues se la pasa parado y platicando, se sale del salón, muy rudo en su trato con sus compañeros, empuja o pelea, libros y cuadernos maltratados, mochila desorgaizada, pierde sus artículos escolares. En casa muy dificil para que haga las tareas, se enoja y se le tiene que presionar y vigilar, todo el tiempo en movimiento, en la comida, se levanta constantemente, se le tiene que corregir constantemente, se le castiga, tiene momentos en que es contestón, grosero, desobediente, no mide los peligros, en la calle se le tiene que vigilar pues se cruza las calles, presenta enuresis 5x30, en la socialización si convive pero termina peleando o haciendo trampa en los juegos pues no sabe perder y llora mucho. La maestra yua no lo aguanta en el salón, por eso lo deriva a esta institución. "

            EJEMPLO NÚMERO 3:
            "Menor identificado desde la primaria con toda la sintomatología de hiperactividad, inatención, impulsividad, disperso, inatento, no trabajar, cuadernos y libros maltratados, mochila desorganizada, reportes constantes, en casa dificil para hacer tareas, no se le dio la atención y si se le generaban multiples regaños y sanciones, un hijo menor con diferencia con su hermana de 15 años, padres muy incompatibles por lo que vivió en medio muy disfuncional, el hermano mayor de 32a con tratamiento en salme, por lo que también es violento, ingresa a secundaria y aunado a la adolescencia totalmente disfuncional, no trabajar, no hacer tareas, distraído, fuera del salón y debuta en el consumo de multiples sustancias, ingresa a preparatoria y definitivamente abandona por el consumo principalmente de cocaína, asi pues que no estudia. Acude a psicología en varias ocasiones y a psiquiatría, le dijeron que tenía depresión y ansiedad y le dieron sertralina 50mg-d. Hace 5 meses vive con el padre porque pelea mucho con la madre, pero igual con el padre, miente de todo, exagera todo, le aumenta a todo, coamete hurtosmenores en la tienda de la madre como golosinas o algun billete de 20 pesos, ayer se disgustaron porque ya desconfían mucho de él y se tardó en un mandado y se pelearon, y se puso alterado, golpeando paredes, diciendo que quería morirse, el señala que siente una gran necesidad de consumir sustancias pero que sabe que no puede, se siente desesperado por salir a consumir asi que ayer consumió thc y clonazepam 1.5mg, y al no consumir siente que ya no existe nada que para que está. Acuden a urgencias y les dicen que se esperen a la cita de psiquiatria infantil."

            EJEMPLO NÚMERO 4:
            "Menor que proviene de familia disfuncional y desintegrada, se separan los padres, de principio se queda con la madre y el hermano, pero se señala que la mamá llevaba una vida sin responsabilidades, primero se va el hijo con el padre y hace 5 años la menor se va también con el padre, pues aparentemente presenció situaciones de tipo sexual y se la lleva el padre y está en juicio la custodia. Desde que la menor está en kinder se presentran los reportes de conducta y se hacen totalmente evidentes en primaria, inatención, dispersa, hiperactividad, impulsividad, peleonera, no trabajar en clase, bajas calificaciones, siempre de pie, platicando. En casa muy dificil para hacer las tareas, se le tienen que decir muchas ocasiones, y por lo tanto se enoja y hace berrinches y con ello se rasguña la cara, se azota en el suelo, se golpeó la cabeza y se hizo una herida, vive con el padre y la pareja del padre con su hija adolescente, con la madrastra es muy rebelde y con el padre ñmuy modocita, asi que el padre la tiene con superprotección, por lo que no tiene ni reglas ni normas, en la secundaria que acaba de ingresar ya están los reportes, y ademas de peleas con niñas mucho mas grandes que ella y las calificaciones fueron de 6 y 7 en todas las materias y por ello es que la traen a valoración."

            EJEMPLO NÚMERO 5:
            "Menor que proviene de familia desintegrada y disfuncional, la madre refiere que el padre la dejaba encerrada con su hija mayor, y el se iba a trabajar o a bailar o salir con sus amigos y amigas. Le dejaba de forma muy específica que tenía que hacer y que quería de comer y como prepararlo, fueron 5 años de esta forma de vida y al final decide ella separarse, la madre se queda con la custodia de la niña y el padre la visita o bien la menor va algunos fines de semana a casa de él, ella refiere que ya sentía cierto acercamiento por parte de él, y a los 10a ya hay tocamientos en varias ocasiones y finalmente termina en una presunta penetración, el padre la amenaza que si habla, "me iba a ir peor", por ello no lo dice e inicia con sintomatología caracterizada por tristeza, miedo, ansiedad, temblor, inquietud, sueño con pesadillas "tenía como un bloqueo", asi como presenta ideas suicidas por diversas situaciones como sentir a la madre distante de ella, por lo que sucedía con el padre, sentimiento de culpabilidad, pensó en el harocamiento sin ninguna planificación o intento. Refiere que por estar pensando primero en todos los problemas familiares y posterior por el presunto abordaje sexual, siempre muy distraída enla escuela, incluso pensaba que nno quería estudiar, por lo que siempre con muy bajas calificaciones, sin reportes de conducta. El 25 de noviembre 2024 la menor finalamente abre el tema con una tía, pues llegaba la fecha en que tendría que ir otra vez con el padre, la tía se lo dice a la madre y van a ciudad niñez en donde se interpone una denuncia, fue valorada por ginecobstetrica y psicología y que buscaran atención en psiquiatría y por eso están en la consulta. En este momento no dan ningun tipo de sintomatología pues ella refiere que una vez que lo dijo, cambió todo, se siente mejor, incluso en la escuela ya puede estudiar y tiene califs de 9 y 10."

            EJEMPLO NÚMERO 6:
            "Masculino escolar, procedente de familia desintegrada por dinámica de violencia y padre consumidor de metanfetaminas; con antecedente de gesta patológica, de nacimiento prematuro y bajo peso al nacer, por desprendimiento prematuro de placenta y múltiples patologías asociadas a la prematurez incluida la patología de base que motiva que acudan a consulta. Tras 2 años de múltiples manejos médicos y quirúrgicos inicia su terapie en crit- teletón donde reicbió terapia física con notoria mejoría motriz, comenzando con sedestación, gateo y bipedestación asistida y emisión de bisilabos. Hace un año la madre se percata del inicio de episodios de irriitabilidad con heteroagresividad y alteraciones del patrón de sueño con insomnio de inicio "se enojaba mucho, nos mordía, pellizcaba, no dejaba de llorar" sic. Madre. Es por lo anterior que fue valorado por el psiquiatra de dicha institución quien no dio diagnóstico e inició manejo a base de 0.5mg de risperidona con mejoría sustantiva en cuanto a lo conductual, cediendo irritabilidad, heteroagresividad y mejora en el patrón del sueño. Hace 4 meses es que la madre nota que de forma progresiva la irritabilidad, heteroagresividad y rabietas fueron en incremento por lo que en ausencia actual del servicio de psiquiatría en el crit, deciden acudir a nuestra institución parar valoración."

            EJEMPLO NÚMERO 7:
            "Menor que proviene de familia monoparental, segunda hija de madre añosa, la hermana mayor actualamente tiene 26a, se desarrolla dentro de la casa de la abuela materna, quien es una mujer rigida, estricta, regañona, y por otro lado la madre también muy estricta, lo que hace una niña muy ansiosa y preocupada, tiene un largo historial de la primaria, la cambiaron en 3 ocasiones, siempre porque fue sensible que si un maestro u otro le hablaban fuerte, que en ocasiones ella recoanoce era su persepción, en otras era real, esta inestabilidad genera que tenga bajas calificaciones, entre 6 y 7. Refiere que hace un año es que se hacen mas evidentes los sintomas afectivos que hasta entonces eran fluctuantes, ella refiere que como desencadenantes son los cambios de escuela, la abuela y su trato, la muerte del abuelo materno que era su figura paterna, conoce al padre y llevan una relacion irregular que ya ahora es nula, ella presenta sentimientos de soledad, no se expresa, no cuenta sus cosas, sentimiento de que en su casa la hacen a un lado, mala apreciacion de su aspecto personal, labilidad emocional, llora de todo, miedo al que dirán. Refiere que tiene eventos de sonambulismo 3 bien reconocidos y hace 22 días presentó dengue y tuvo hipertermia muy marcada y unmomento de estado delirante por lo mismo en la madugada, se salió de la casa, caminó varias calles y se regresó al su casa, la estuvieron buscando y la abuela por su carácter la regaño, que porque hacía eso, que porque se había salido en la madrugada y como la madre estaba en usa, la mujer se sentía responsable de todo. También refiere sintomatología de macropsias y alucinaciones quinestésicas. De forma especifica refiere sintomatología depresiv caracterizada por llanto, aislamiento, no hablar, no salir, sentirse incomprendida, desesperación, de ansiedad onicofagia, se quita la paiel de los dedos (padrastros), se truena los dedos, mueve constantemente los pies. Tuvo problemas en la secundaria por una amistad que le estimuló a no entrar a clases y por ello la reportaron. En casa irritable, contestona, malmodienta, no hace sus quehaceres, dificil para su aseo personal."

            EJEMPLO NÚMERO 8:
            "Hombre escolar, nacido en méxico y criado en eeuu desde los 2 años hasta hace 6 meses. Proviene de una familia integrada, aunque temporalmente separada por la permanencia del padre en eeuu hasta el siguiente mes. La familia está compuesta por la madre, quien es ama de casa, el padre, técnico en aire acondicionado, y un hermano menor de 3 años; es el mayor de 2 hermanos. Se le refiere como un menor aplicado en la escuela con buen desempeño académico, aunque impulsivo, poco tolerante a la frustración y con un patrón de sueño caracterizado por despertares prematuros (4 am). A partir de su ingreso a la primaria, se hicieron evidentes la dificultad para atender indicaciones de la madre, particularmente en actividades que le resultan tediosas, pérdida y descuido de los útiles escolares y una tendencia a la desorganización, principalmente manifiesta en el orden de su habitación. La sintomatología que los motiva a acudir hoy a consulta inició durante el curso de 2o. De primaria, cuando tras un malentendido entre una compañera y él, la madre de esta lo abordó extraoficial y unilateralmente con aparentes amenazas. A partir de entonces, se le comenzó a notar constantemente ansioso/temeroso, tendiente al retraimiento y con disminución de la interacción social, notablemente nervioso con inquietud constante y chupeteo de región perioral, desarrollando una dermatosis como consecuencia. Se observó el incremento de la irritabilidad, oposicionismo y hostigamiento hacia el hermano menor. Por lo anterior y a petición del menor, decidieron cambiar su lugar de residencia a méxico en junio del 2024, permaneciendo el padre en eeuu. La ausencia del padre a quien refiere extrañar; el proceso de adaptación por el cambio cultural, dinámica escolar, residencia con la abuela con quien tiene una relación de conflicto, acentuaron la sintomatología descrita, particularmente la irritabilidad y negativismo "es lo que más tiene, le digo que haga algo y a todo reniega, dice que porque él... También le trae mucho coraje a su hermano y se la pasa molestándolo" sic. Madre. Es por lo anterior que deciden acudir a valoración."

            EJEMPLO NÚMERO 9:
            "El menor tiene el historial que desde prescolar es reportado por inquietud, pero ya en primaria el cuadro es evidente, es un niño inatento, disperso, inquieto, platica, se levanta, deja trabajos incompletos, pierde artículos escolares e incluso ropa, descuidado con el uniforme, se ensucia, es muy poco tolerante con sus compañeros, pelea con ellos, no quiere que hagan ruido, lo que genera ciertas riñas, y por su intolerancia y que quiere corregir a todos ya lo apartan,él se da cuenta de esto, hacen equipos y no lo eligen, pobre concentración, trae la mochila revuelta, este ciclo se ha hecho mas evidente el cuadro por las exigencias propias del 3er año. En casa muy dificil para hacer las tareas, se le tiene que decir muchas veces, y se tarda mucho en terminar cualquier tarea, lo mismo sucede con el aseo personal, sus quehaceres, en la comida está inquieto, no puede hacer mas de una iandicación, come mas o menos bien pero se la pasa platidando en la comida, tiene muy poca tolerancia a todo, siempre dice que se siente "humillado", suele pelear con su hermana de 11a, la socialización es regular, conlal madre se enoa mucho, el estado de ánimo dice que "neutro", se siente ansioso reflejado por estres, irritabilidad, enojo, dice que por estar solo en la escuela, refiere insomnio intermedio, en alguna ocasión llegó a pensar en morir para ir a ver a su papá que murió hace 4 años por covid. La madre lo lleva a un centro llamado cade, se ve el rsumen que les dieron, atendido por un psiquiatra general y una medico general, le prescribieron mfd lp de 20mg 1-0-0, y risperidona 0.25mg-d, se le dio durante un mes, la madre vio muy poca respuesta, y en la escuela con el dx. Que les dieron de tdah mixto bajaron la tensión y bajaron los reportes, por costos ya que subieron la consulta a 1450 pesos y el medicamento, pues mejor ya lo trae a esta institución."

            TEXTO A RESUMIR:
            {transcripcion}
        ''')

        else:
            response = model.generate_content(f'''
            INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución clínica del paciente entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción de la consulta proporcionada. Considera que dicha transcripción corresponde a una conversación entre el médico y el paciente, por lo que deberás identificar con claridad quién interviene en cada momento, extrayendo exclusivamente la información clínica relevante que proviene del testimonio del paciente para asegurar una redacción precisa y coherente.

            OBJETIVO: Distingue la información que corresponde a la consulta previa y a la actual, para una nota de evolución clínica del paciente, precisa y concisa que abarque los cambios y continuidad en la presentación de síntomas, desde la última valoración hasta la fecha actual.

            FORMATO REQUERIDO:
            - Idioma español México
            - Texto en un párrafo (sin viñetas, sin espacio entre párrafos ni subtítulos), sin salto doble de línea
            - Extensión de 150 a 200 palabras
            - Lenguaje técnico apropiado para documentación clínica
            - Escrito en tercera persona

            INCLUIR:
            - Antecedentes relevantes del padecimiento y particularmente del estado y evolución desde la última consulta a la actual
            - Cronología detallada de síntomas y manifestaciones (cognitivos, de socialización, emocionales, ansiosos, afectivos o anímicos, del sueño, del apetito y adherencia al tratamiento)
            - Cambios en la severidad e intensidad de los síntomas a lo largo del tiempo
            - Estado actual y evolución de sus relaciones interpersonales significativas y de su funcionalidad en ámbitos social, familiar, académico o laboral según corresponda
            - Factores desencadenantes o exacerbantes identificados por el paciente
            - Estado actual del paciente
            - Después de un salto de línea escribe un análisis donde incluyas las decisiones tomadas sobre el tratamiento, las recomendaciones hechas, los acuerdos hechos y tareas pendientes del paciente, durante la entrevista actual (ej. se decide continuar mismo tratamiento por estabilidad de síntomas, se brinda psicoeducación respecto al apego al tratamiento y se acuerda mejorar el desempeño académico y relación con sus padres, etc.)

            OMITIR:
            - Cualquier información que no forme parte de la evolución clínica del padecimiento
            - Sugerencias o intervenciones terapéuticas expresadas por el médico durante la consulta actual
            - Información personal no relevante
            - Recomendaciones o planes de tratamiento
            - Juicios de valor
            - Diagnósticos
            - Análisis o interpretaciones clínicas
            - Resúmenes finales

            IMPORTANTE: Dado que la transcripción incluye tanto las preguntas del médico como las respuestas del paciente, enfoca tu atención exclusivamente en las intervenciones del paciente que aporten información clínica relevante. Utiliza las preguntas del médico solo como guía para contextualizar las respuestas del paciente, sin incluirlas de forma directa.

            ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS DE NOTAS DE EVOLUCIÓN A CONTINUACIÓN:

            Ejemplo 1: “Se encuentra clínicamente estable, su ánimo lo refiere como mayoritariamente bien, salvo los primeros días a partir de que fue despedida, hecho que logró afrontar sin mayores complicaciones; se sintió apoyada por sus padres. Se encuentra buscando empleo, ha tenido entrevistas con adecuado desempeño y "segura" de sí misma; en ciernes entrevista que más le llama la atención. En cuanto a ansiedad ha presentado algunos síntomas asociados al estatus de la relación con su novio de la que en ocasiones se siente con culpa. Refiere un patrón de sueño fragmentado por las micciones nocturnas, 2 por noche. En cuanto al incremento de la dosis de MFD no notó tanto cambio, probablemente, por el contexto laboral. Se queja de hiporexia con impacto ponderal de 3kg en 3 semanas. El consumo de cannabis ha disminuido al igual que el craving.”

            Ejemplo 2: “La paciente refiere que hacia el mes de diciembre después de entre 1 a 2 meses de haber suspendido la sertralina por "sentirse bien" comenzó con irritabilidad por lo que acudió a psicología con mejoría sustancial. Acude el día de hoy porque desde hace 2 meses ha notado anhedonia, llanto espontáneo, hiperfagia con aumento de peso lo que impacta de forma negativa en su ánimo. Ha tenido apatía, pérdida de interés, ha dejado de cocinar, lavar su ropa, fatiga, ha perdido el interés en su arreglo, baja en la líbido, pensamientos pasivos de muerte, culpa, minusvalía con recriminación a sí misma y tendencia al aislamiento. Comienza con insomnio de conciliación; hipoprosexia. No ha presentado síntomas ansiosos.”

            Ejemplo 3: “Refiere que no ha notado cambios sustantivos respecto a la valoración previa salvo que ya ha tenido iniciativa para avanzar en los pendientes personales y encomendados. Por ejemplo hoy que no tuvo clase se puso a aspirar y lavar la alfombra de su cuarto, plan que tenía 2 meses en planes "antes me hubiera puesto hacer otra cosa". Ha tenido dificultades para despertar e ir a hacer ejercicio. Continúa con dificultades para conciliar el sueño aunque puede estar asociado a que, aunque se va a dormir a las 10pm, lo hace mientras está en videollamada con su novia. Una vez conciliado el sueño no despierta por las madrugadas y despierta hacia las 6:40 am para sus actividades, buen patrón alimenticio y de sueño. En lo escolar se siente un poco más social con mayor participación en clase e interacción con sus compañeros; en lo atencional ha mejorado sustantivamente en buena medida a que ha adoptado cambios como despejarse previo clase "voy al baño me mojo la cara, voy por una bebida y ya me enfoco mejor (sic)". En relación a la reducción de lorazepam no notó cambio alguno. Dice sentirse emocionado porque lo visitará su novia dentro de 1 mes. He disfrutado jugar XBOX, lavar los carros y cocinar.”

            Ejemplo 4: “Acude paciente refiriéndo continuar con estabilidad de sus síntomas, es decir, con la disminución de la ansiedad y síntomas depresivos además de la casi ausencia de los pensamientos de culpa/minusvalía (los de muerte están ausentes); sin embargo refiere que algunos días, los menos, ha tenido algunas bajas en el estado de ánimo sin una causa identificada. Adecuada adherencia al tratamiento, patrón de sueño y alimenticio. También ha notado menos "fastidio" por estar haciendo su trabajo además de menor irritabilidad, mayor energía con mejor concentración y rendimiento en su empleo. En cuanto a la ansiedad casi han desaparecido las rumiaciones ansiógenas y cuando estas se presentan logra identificarlas y darles cauce. Continúa con actividad física a base de rutina dentro de casa con una frecuencia de 3 días por semana durante 40 minutos. Subjetivamente califica su estado de ánimo de un 8-9/10.”

            Sección Adicional (Incluir al Final de la Descripción Principal)
            Usa exclusivamente la información extraída de la transcripción para desarrollar lo siguiente:

            1. Examen Mental
                - Incluye solo la información dentro de la transcripción y en caso de que no este omitela, no menciones que no esta
                - Incluye la descripción basado en los ejemplos dados y en el siguiente orden: Apariencia (higiene, aliño), estado de alerta, atención, motricidad, estado de ánimo, afecto al momento de la entrevis. Características del discurso (si es
                    espontáneo, inducido, fluido o no, parco, abundante o prolijo, coherente, congruente, volumen, velocidad y latencia de respuesta), pensamiento (lineal, circunstancial, circunloquial, tangencial, disgregado), conetnido del pensamiento (preocupaciones, rumiaciones, ideas obsesivas, intrusivas, etc.)
                    presencia de psicosis (alucinaciones o delirios), ideación o fenómeno suicida, intrsopección del paciente sobre su enfermedad, juicio (2 a 7 años de edad = preoperacional, 7 a 12 años = concreta y > 12 años formal. Además si el juicio esta dentro del marco de la realidad o fuera en caso de que haya síntomas de psicosis),control de impulsos)
                    Ejemplos de examen mental:
                    - Ejemplo 1: Se trata hombre adolescente con adecuada higiene y aliño, alerta, atento, orientado cooperador de ánimo eutímico con un afecto congruente y resonante. Discurso inducido, fludio, coherente, congruente,
                    volumen, velocidad y latencia de respuesta adecuados. Pensamiento lineal sin que al momento de la entrevista se encuentre psicosis o fenómeno suicida. Adecuada introspección, juicio concreto y buen
                    control de impulsos.
                    - Ejemplo 2: Se trata de mujer con adecuada higiene y aliño, ropa acorde a clima y situación, alerta, atenta, orientada, cooperadora con inquietud motriz circunscrita a pies y manos. Refiere un ánimo ansioso con afecto congruente. Discurso
                    inducido, parco, coherente, congruente, volumen bajo, velocidad adecuada y latencia de respuesta discretamente aumentada. Pensamiento lineal sin datos de psicosis o ideación suicida. Parcial introspección,
                    juicio formal y buen control de impulsos.
                    - Ejemplo 3: Hombre escolar con regular higiene y aliño, alerta, hipoproséxico, hipercinetico, incapaz de mantenerse en su sitio incluso deambulando por el consultorio. Parcialmente cooperador. Ánimo referido como irritable con
                    afecto disonante. Discurso espontáneo, fluido, intrusivo, taquilálico coherente, congruente, con velocidad y volumen adecuados; latencia de respues disminuida. Pensamiento circunstancial y prolijo sin ideación suicida
                    o psicosis. Pobre introspección, juicio concreto y pobre control de impulsos.
            2. Interacción entre medicamentos
                - Identifica los medicamentos que esta o estará tomando y en base a tu conocimiento determina si hay alguna interacción entre ellos con una mención breve del tipo de interacción

            TEXTO A RESUMIR:
            {transcripcion}
        ''')
        return response.text

    def resumen_transcripcion2(transcripcion, nota):
        llm_model = 'Qwen/Qwen3-32B'
        if nota == "primera":
            response = openai.chat.completions.create(model=llm_model, messages=[{"role": "user", "content":f'''
                INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. Ten en cuenta que la transcripción es producto de una conversación entre el médico y el paciente, por lo que deberás identificar correctamente quién está hablando en cada intervención para asegurar una reconstrucción precisa y coherente del relato clínico.

                OBJETIVO: Redactar la evolución del padecimiento del paciente, desde su inicio hasta el estado actual, integrando únicamente la información clínica relevante extraída de las intervenciones del paciente durante la consulta.

                FORMATO REQUERIDO:
                - Idioma español
                - Texto en párrafos continuos (sin viñetas ni subtítulos), sin salto doble de línea
                - Extensión de entre 300 a 600 palabras según lo amerite el caso
                - Lenguaje técnico apropiado para documentación clínica
                - Escrito en tercera persona

                INCLUIR:
                - Antecedentes relevantes del padecimiento
                - Cronología detallada de síntomas y manifestaciones
                - Cambios en la severidad e intensidad a lo largo del tiempo
                - Factores desencadenantes o exacerbantes identificados
                - Estado actual del paciente

                OMITIR:
                - Toda información que no corresponda a la evolución del padecimiento del paciente, incluyendo sugerencias terapéuticas realizadas o propuestas durante la consulta
                - Información personal no relevante para la evolución
                - Recomendaciones o plan de tratamiento
                - Juicios de valor
                - Diagnósticos
                - Análisis sobre el caso
                - Resúmenes al final del texto

                IMPORTANTE: Dado que la transcripción incluye tanto preguntas del médico como respuestas del paciente, considera únicamente los fragmentos en los que el paciente describe su experiencia subjetiva. Ignora las intervenciones del médico excepto cuando sirvan para contextualizar una respuesta del paciente.

                ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS A CONTINUACIÓN:

                        Ejemplo 1:
                        “Cuadro actual de aproximadamente 11 meses de evolución, de inicio insidioso, curso continuo y tendiente al empeoramiento, en el contexto de un trastorno depresivo recurrente que evoluciona hacia un trastorno depresivo persistente, desencadenado por conflictos en la relación con el padre de su hijo y agravado por dependencia emocional, aislamiento social y dificultades económicas.
                        Por interrogatorio directo, la paciente refiere que desde entonces comenzó con estado de ánimo predominantemente deprimido, tendencia al llanto, apatía con pérdida del interés por actividades que previamente disfrutaba dejando de arreglarse, maquillarse y salir con amigas. Presenta hiporexia con pérdida de 8 kg en aproximadamente 7 meses con fluctuaciones en el peso; hay insomnio mixto con múltiples despertares para verificar a su hijo. Se agregaron problemas de concentración con olvidos frecuentes incluyendo la administración de medicamentos, enlentecimiento psicomotriz y fatiga.

                        Hay pensamientos persistentes de culpa relacionados con su embarazo y la percepción de "decepcionar" a sus padres, así como ideas de minusvalía "no sirvo para nada", "soy una mantenida", "les he fallado". Se añadieron pensamientos pasivos de muerte "sería mejor no estar" aunque sin ideación suicida estructurada. Presenta ansiedad con predominio de pensamientos catastróficos en relación a su familia, cefalea tipo migraña y estreñimiento.

                        Hace aproximadamente 6 meses inició tratamiento con duloxetina 60mg/día notando mejoría parcial de síntomas aunque sin remisión completa. Hace un mes, tras descubrir una presunta infidelidad de su expareja, presenta exacerbación de síntomas depresivos con deterioro en autocuidado llegando a espaciar el baño hasta por una semana, mayor aislamiento social y inicio de consumo diario de alcohol (3 cervezas) como mecanismo de afrontamiento.

                        Los síntomas han impactado significativamente en su funcionalidad, presentando deterioro en el autocuidado, dificultad para realizar las actividades de rehabilitación de su hijo y aislamiento social. Por lo anterior y el aumento de los síntomas ansiosos así como la perdida de motivación que decide acudir a consulta.”

                        Ejemplo 2:
                        “En el contexto de una historia de múltiples episodios depresivos, inicia su padecimiento actual en abril 2023 de forma insidiosa, continua y tendiente al empeoramiento sin un desencadenante aparente y agravado por deprivación académica, dificultades económicas, conflictos de pareja. Según refiere, desde entonces, comenzó con un estado de ánimo predominantemente deprimido, tendencia al llanto, apatía con perdida del interés por actividades que previamente daban placer dejándo de disfrutar sus actividades del día dejándo de asear su casa y descuidando su autocuidado. A lo anterior se añadieron hiporexia con perdida de entre 6 y 7 kg en 6 messes; hay insomnio mixto con latencia de conciliación de unas 2 horasy al menos 3 despertares; dificultades para la concentración con perdida de objetos y dificultad para mantener el hilo de conversaciones; enlentecimiento psicomotriz. Ha notado la presencia de pensamientos de culpa, minusvalía y pasivos de muerte "me siento insuficiente... siento que no le intereso a nadie, me rechazan y he pensado en mejor desaparecer [sic paciente]". A lo anterior se añadieron ansiedad flotante, nerviosísmo, cervicodorsalgia, aislamiento y episodios de pánico con sensación de ahogo, malestar torácico y síntomas vegetativos de 10-15 minutos de duración y que han ido incrementado en frecuencia de 1-2 / semana a 1-2 por día. Refiere que de junio a agosto presentó acoasmas fugaces con impacto en ánimo incrementando síntomas de ansiedad. En este contexto hace 1 mes, tras discutir con su madre, de forma impulsiva y con intención suicida, tomó unos 7ml de solución de clonazepam 2.5mg/ml sin necesidad de manejo intrahospitalario. Por lo anterior fue valorada hace 10 días en CEB en donde prescribieron fluoxetina con mejoría subjetiva referidade 10%. Por lo anterior es que decide acudir a valoración.”

                        Ejemplo 4:
                        “El episodio actual se da en el contexto de un patrón de conducta de inicio en la adolescencia tardía, persistentemente desadaptativo e inflexible caracterizado por sensación de vacío crónico, inestabilidad en la relaciones interpesonales y de emociones  con consecuentes conflictos con los padres y parejas; miedo al abandono que le ha condicionado mantenerse en una relación marcada por la violencia; ideas sobrevaloradas referenciales y distorsiones de la autoimagen; también ha presentado pobre tolerancia a la frustración que le conicionaron episodios de desregulación emociona con la presencia de ira desporporcionada e ipmulsividad que le generan conducta autolesivas como método de afrontamiento (cutting) y reactivación de pensamientos de muerte. Padecimiento de alrededor de 9 meses de inicio insidioso, continuo y tendiente al empeoramiento desencadenado por la muerte de la abuela y agravado por desempleo y separación del conyuge. Desde entonces ha presentado un estado de ánimo persistentemente triste, tendiente al llanto espontáneo; insomnio de inicio con latencia de conciliación de hasta 4 horas en asociación a rumiaciones entorno a su situación de pareja;  enlentecimiento psicomotor, problemas para la concentración con múltipls olvidos; hiporexia con perdida de 15 kg en un par de meses; además ha prsentado pensamientos de culpa, minusvalía y pasivos de muerte "Es mi culpa que me haya tratado así, me he fallado... a veces he pensado en no querer depesrtar pero pienso en mis hijos y pasa [sic]". De forma paralela ha presentado ansiedad flotante, cervicodorsalgia, nerviosísmo, inquietud motriz y paroxismos de exacerbación síntomas que se acompañan de descarga adrenérgica con sensación de muerte o perder el control. Hace 2 días, de forma impulsiva, tras ver su expareja con otra persona, presentó tentativa suicida abortada mediante flebotomía "me detienen mis hijos... fue el impuso en ese rato [sic]”

                        TEXTO A RESUMIR:
                        {transcripcion}
            '''}],)
        elif nota == 'primera_paido':
            response = openai.chat.completions.create(model=llm_model, messages=[{"role": "user", "content":f'''

    Instrucciones Generales
    Asume el rol de un psiquiatra infantil especializado. Con base únicamente en la transcripción de consulta (que incluye intervenciones del médico, el paciente y uno de los padres), redacta la evolución detallada del padecimiento del paciente. La transcripción debe permitir identificar claramente quién interviene en cada turno, por lo que se debe realizar una reconstrucción precisa y coherente del relato clínico.

    Objetivo Principal
    Elaborar un informe preciso y conciso que describa la evolución del padecimiento del paciente desde su inicio hasta el estado actual, en orden cronológico y utilizando únicamente la información clínica relevante expresada por el paciente y su padre o madre (descartando las intervenciones del médico, salvo que sean necesarias para contextualizar la experiencia subjetiva).

    Requisitos del Formato de la Respuesta
    - Idioma: Español México.
    - Estilo:
    - Un solo párrafo (sin viñetas, subtítulos ni saltos dobles de línea).
    - Redacción en tercera persona, concisa y precisa.
    - Lenguaje técnico apropiado para documentación clínica
    - Uso de lenguaje técnico propio de la psicopatología y semiología psiquiátrica.
    - Extensión: La descripción principal debe tener entre 250 a 350 palabras según lo amerite el caso y sin incluir las secciones adicionales.
    - Evitar redundancias.
    - Mantener un orden cronológico.

    Contenido a Incluir en la Evolución del Padecimiento
    1. Datos Iniciales y Contexto:
    - Género (hombre o mujer) y grupo etario del paciente (preescolar: 0-5 años, escolar: 5-11 años, adolescente: >11 años).
    - Contexto sociofamiliar (por ejemplo, presencia o ausencia de padres, custodia, albergue, etc.) y dinámica familiar (relaciones, integración, factores parentales relevantes, eventos traumáticos, uso excesivo de dispositivos electrónicos, etc.).
    2. Descripción Clínica Detallada:
    - Factores desencadenantes y exacerbantes.
    - Cronología de síntomas y manifestaciones (afectivos, ansiosos, cognitivos, conductuales, patrón de sueño, alimentación, etc.).
    - Evolución en severidad e intensidad de los síntomas a lo largo del tiempo.
    - Impacto en la funcionalidad diaria: desempeño académico, relaciones familiares, interpersonales, socialización, etc.
    3. Estado Actual:
    - Síntomas presentes y la principal motivación para acudir a consulta.

    Sección Adicional (Incluir al Final de la Descripción Principal)
    Usa exclusivamente la información extraída de la transcripción para desarrollar lo siguiente:
    1. Impresión diagnóstica
        - En base a los síntomas narrados y en base a tu conocimiento como experto en psiquiatría infantil genera tu propia e indepéndiente hipotesis diagnóstica propia acorde a los criterios diagnósticos del DSM 5 TR o CIE 10, que incluya sus especificadores.
        - Puedes mencionar diagnósticos concurrentes o complementarios
        - 1 a 2 diagnósticos diferenciales
    2. Examen Mental
        - Incluye solo la información dentro de la transcripción y en caso de que no este omitela, no menciones que no esta
        - Incluye la descripción basadi en los ejemplos dados y en el siguiente orden: Apariencia (higiene, aliño), estado de alerta, atención, motricidad, estado de ánimo, afecto al momento de la entrevis. Características del discurso (si es
            epontáneo, inducido, fluido o no, parco, abundante o prolijo, coherente, congruente, volumen, velocidad y latencia de respuesta), pensamiento (lineal, circunstancial, circunloquial, tangencial, disgregado),
            presencia de psicosis (alucinaciones o delirios), ideación o fenómeno suicida, intrsopección del paciente sobre su enfermedad, juicio (2 a 7 años de edad = preoperacional, 7 a 12 años = concreta y > 12 años formal. Además si el juicio esta dentro del marco de la realidad o fuera en caso de que haya síntomas de psicosis),control de impulsos)
            Ejemplos de examen mental:
            - Ejemplo 1: Se trata hombre adolescente con adecuada higiene y aliño, alerta, atento, orientado cooperador de ánimo eutímico con un afecto congruente y resonante. Discurso inducido, fludio, coherente, congruente,
            volumen, velocidad y latencia de respuesta adecuados. Pensamiento lineal sin que al momento de la entrevista se encuentre psicosis o fenómeno suicida. Adecuada introspección, juicio concreto y buen
            control de impulsos.
            - Ejemplo 2: Se trata de mujer con adecuada higiene y aliño, alerta, atenta, orientada, cooperadora con inquietud motriz circunscrita a pies y manos. Refiere un ánimo ansioso con afecto congruente. Discurso
            inducido, parco, coherente, congruente, volumen bajo, velocidad adecuada y latencia de respuesta discretamente aumentada. Pensamiento lineal sin datos de psicosis o ideación suicida. Parcial introspección,
            juicio formal y buen control de impulsos.
            - Ejemplo 3: Hombre escolar con regular higiene y aliño, alerta, hipoproséxico, hipercinetico, incapaz de mantenerse en su sitio incluso deambulando por el consultorio. Parcialmente cooperador. Ánimo referido como irritable con
            afecto disonante. Discurso espontáneo, fluido, intrusivo, taquilálico coherente, congruente, con velocidad y volumen adecuados; latencia de respues disminuida. Pensamiento circunstancial y prolijo sin ideación suicida
            o psicosis. Pobre introspección, juicio concreto y pobre control de impulsos.
    3. Interacción entre medicamentos
        - Identifica los medicamentos que esta o estará tomando y en base a conocimiento determina si hay alguna interacción entre ellos con una mención breve del tipo de interacción

    Información a Omitir
    - Todo dato que no esté relacionado con la evolución del padecimiento, salvo lo requerido en las secciones adicionales.
    - Información personal irrelevante, sugerencias terapéuticas, planes de tratamiento, juicios de valor, diagnósticos no explícitamente mencionados en la transcripción, análisis del caso o resúmenes finales así como expresiones coloquiales salvo las cita textuales de los dichos por el paciente o su acompañante

    Guías Adicionales
    - Mantener la objetividad: basar el informe solo en lo expresado por el paciente y acompañante (y, en su caso, su madre para contextualizar).
    - Seguir una cronología clara, desde la aparición de los síntomas hasta el estado actual.
    - Integrar de forma concisa las secciones adicionales, sin redundancias.
    - Descartar las intervenciones del médico, salvo cuando sean necesarias para interpretar o clarificar la experiencia subjetiva del paciente.
    - No utilices la palabras "autolisis" o "autolítico"

                IMPORTANTE: IMPLEMENTA EL ESTILO, REDACCIÓN, SINTAXIS Y VOCABULARIO UTILIZADO EN LOS SIGUIENTES EJEMPLOS:

                EJEMPLO NÚMERO 1:
                "Se refiere una menor que proviene de una familia integrada, el padre era director de una secundaria, muere hace 3 años, era alcohólico. Ella refiere que tenia una relacion muy distante con el padre, "no me decía hija, me decía niña", muy pobre convivencia e interacción afectiva. Ella se ha caracterizado desde siempre de ser una niña solitaria, pocas amistades, en la escuela pobre convivencia, pero ya para 5to año con unas amigas hizo un video porno animado haciendom alución a un par de compañeros, lo que provocó que la condicionaran, y también le rompió un huevo de confeti a una maestra y tuvo un reporte. Ella señala que tuvo varios cambios de primaria por el trabajo de la madre como intendente y le toca pandemia de covid en 6to, por lo que ingresa a mitad de secundaria y mismo comportamiento de aislamiento, ella acepta que poco hizo, poco trabajó y logró terminarla y actualmente en preparatoria, ella dice que faltan mucho los maestros, que no tiene amigas y que por eso dejó de ir, así que termina con 64 y 3 materias reprobadas. La madre la refiere depresiva, siempre aislada en su habitación, no habla con nadie, irritable, intolerante, agresiva, no tolera indicaciones, tiene su habitación sucia, come mucho pues no tiene nada que hacer, se la pasa viendo videos, series, videojuegos, se dice estar ansiosa, pues piensa mucho las cosas, onicofagia, se muerde las mucosas de la boca, se siente de ánimo "regular, seria, pensativa", niega ideas de muerte o suicidio, alguna vez en 5to año y por los problemas que tuvo. Por estar en sus pensamientos no pone atención en nada y la madre se enoja pues no hace lo que le pide. Hace un mes van a psicología y esta pide que venga a psiquiatría para ser medicada. "

                EJEMPLO NÚMERO 2:
                "Menor que es identificado desde el kinder como muy inquieto, pero ahora que entra a primaria totralmente un cuadro caracterizado por inatención, disperso, inquieto, no trabaja en clase pues se la pasa parado y platicando, se sale del salón, muy rudo en su trato con sus compañeros, empuja o pelea, libros y cuadernos maltratados, mochila desorgaizada, pierde sus artículos escolares. En casa muy dificil para que haga las tareas, se enoja y se le tiene que presionar y vigilar, todo el tiempo en movimiento, en la comida, se levanta constantemente, se le tiene que corregir constantemente, se le castiga, tiene momentos en que es contestón, grosero, desobediente, no mide los peligros, en la calle se le tiene que vigilar pues se cruza las calles, presenta enuresis 5x30, en la socialización si convive pero termina peleando o haciendo trampa en los juegos pues no sabe perder y llora mucho. La maestra yua no lo aguanta en el salón, por eso lo deriva a esta institución. "

                EJEMPLO NÚMERO 3:
                "Menor identificado desde la primaria con toda la sintomatología de hiperactividad, inatención, impulsividad, disperso, inatento, no trabajar, cuadernos y libros maltratados, mochila desorganizada, reportes constantes, en casa dificil para hacer tareas, no se le dio la atención y si se le generaban multiples regaños y sanciones, un hijo menor con diferencia con su hermana de 15 años, padres muy incompatibles por lo que vivió en medio muy disfuncional, el hermano mayor de 32a con tratamiento en salme, por lo que también es violento, ingresa a secundaria y aunado a la adolescencia totalmente disfuncional, no trabajar, no hacer tareas, distraído, fuera del salón y debuta en el consumo de multiples sustancias, ingresa a preparatoria y definitivamente abandona por el consumo principalmente de cocaína, asi pues que no estudia. Acude a psicología en varias ocasiones y a psiquiatría, le dijeron que tenía depresión y ansiedad y le dieron sertralina 50mg-d. Hace 5 meses vive con el padre porque pelea mucho con la madre, pero igual con el padre, miente de todo, exagera todo, le aumenta a todo, coamete hurtosmenores en la tienda de la madre como golosinas o algun billete de 20 pesos, ayer se disgustaron porque ya desconfían mucho de él y se tardó en un mandado y se pelearon, y se puso alterado, golpeando paredes, diciendo que quería morirse, el señala que siente una gran necesidad de consumir sustancias pero que sabe que no puede, se siente desesperado por salir a consumir asi que ayer consumió thc y clonazepam 1.5mg, y al no consumir siente que ya no existe nada que para que está. Acuden a urgencias y les dicen que se esperen a la cita de psiquiatria infantil."

                EJEMPLO NÚMERO 4:
                "Menor que proviene de familia disfuncional y desintegrada, se separan los padres, de principio se queda con la madre y el hermano, pero se señala que la mamá llevaba una vida sin responsabilidades, primero se va el hijo con el padre y hace 5 años la menor se va también con el padre, pues aparentemente presenció situaciones de tipo sexual y se la lleva el padre y está en juicio la custodia. Desde que la menor está en kinder se presentran los reportes de conducta y se hacen totalmente evidentes en primaria, inatención, dispersa, hiperactividad, impulsividad, peleonera, no trabajar en clase, bajas calificaciones, siempre de pie, platicando. En casa muy dificil para hacer las tareas, se le tienen que decir muchas ocasiones, y por lo tanto se enoja y hace berrinches y con ello se rasguña la cara, se azota en el suelo, se golpeó la cabeza y se hizo una herida, vive con el padre y la pareja del padre con su hija adolescente, con la madrastra es muy rebelde y con el padre ñmuy modocita, asi que el padre la tiene con superprotección, por lo que no tiene ni reglas ni normas, en la secundaria que acaba de ingresar ya están los reportes, y ademas de peleas con niñas mucho mas grandes que ella y las calificaciones fueron de 6 y 7 en todas las materias y por ello es que la traen a valoración."

                EJEMPLO NÚMERO 5:
                "Menor que proviene de familia desintegrada y disfuncional, la madre refiere que el padre la dejaba encerrada con su hija mayor, y el se iba a trabajar o a bailar o salir con sus amigos y amigas. Le dejaba de forma muy específica que tenía que hacer y que quería de comer y como prepararlo, fueron 5 años de esta forma de vida y al final decide ella separarse, la madre se queda con la custodia de la niña y el padre la visita o bien la menor va algunos fines de semana a casa de él, ella refiere que ya sentía cierto acercamiento por parte de él, y a los 10a ya hay tocamientos en varias ocasiones y finalmente termina en una presunta penetración, el padre la amenaza que si habla, "me iba a ir peor", por ello no lo dice e inicia con sintomatología caracterizada por tristeza, miedo, ansiedad, temblor, inquietud, sueño con pesadillas "tenía como un bloqueo", asi como presenta ideas suicidas por diversas situaciones como sentir a la madre distante de ella, por lo que sucedía con el padre, sentimiento de culpabilidad, pensó en el harocamiento sin ninguna planificación o intento. Refiere que por estar pensando primero en todos los problemas familiares y posterior por el presunto abordaje sexual, siempre muy distraída enla escuela, incluso pensaba que nno quería estudiar, por lo que siempre con muy bajas calificaciones, sin reportes de conducta. El 25 de noviembre 2024 la menor finalamente abre el tema con una tía, pues llegaba la fecha en que tendría que ir otra vez con el padre, la tía se lo dice a la madre y van a ciudad niñez en donde se interpone una denuncia, fue valorada por ginecobstetrica y psicología y que buscaran atención en psiquiatría y por eso están en la consulta. En este momento no dan ningun tipo de sintomatología pues ella refiere que una vez que lo dijo, cambió todo, se siente mejor, incluso en la escuela ya puede estudiar y tiene califs de 9 y 10."

                EJEMPLO NÚMERO 6:
                "Masculino escolar, procedente de familia desintegrada por dinámica de violencia y padre consumidor de metanfetaminas; con antecedente de gesta patológica, de nacimiento prematuro y bajo peso al nacer, por desprendimiento prematuro de placenta y múltiples patologías asociadas a la prematurez incluida la patología de base que motiva que acudan a consulta. Tras 2 años de múltiples manejos médicos y quirúrgicos inicia su terapie en crit- teletón donde reicbió terapia física con notoria mejoría motriz, comenzando con sedestación, gateo y bipedestación asistida y emisión de bisilabos. Hace un año la madre se percata del inicio de episodios de irriitabilidad con heteroagresividad y alteraciones del patrón de sueño con insomnio de inicio "se enojaba mucho, nos mordía, pellizcaba, no dejaba de llorar" sic. Madre. Es por lo anterior que fue valorado por el psiquiatra de dicha institución quien no dio diagnóstico e inició manejo a base de 0.5mg de risperidona con mejoría sustantiva en cuanto a lo conductual, cediendo irritabilidad, heteroagresividad y mejora en el patrón del sueño. Hace 4 meses es que la madre nota que de forma progresiva la irritabilidad, heteroagresividad y rabietas fueron en incremento por lo que en ausencia actual del servicio de psiquiatría en el crit, deciden acudir a nuestra institución parar valoración."

                EJEMPLO NÚMERO 7:
                "Menor que proviene de familia monoparental, segunda hija de madre añosa, la hermana mayor actualamente tiene 26a, se desarrolla dentro de la casa de la abuela materna, quien es una mujer rigida, estricta, regañona, y por otro lado la madre también muy estricta, lo que hace una niña muy ansiosa y preocupada, tiene un largo historial de la primaria, la cambiaron en 3 ocasiones, siempre porque fue sensible que si un maestro u otro le hablaban fuerte, que en ocasiones ella recoanoce era su persepción, en otras era real, esta inestabilidad genera que tenga bajas calificaciones, entre 6 y 7. Refiere que hace un año es que se hacen mas evidentes los sintomas afectivos que hasta entonces eran fluctuantes, ella refiere que como desencadenantes son los cambios de escuela, la abuela y su trato, la muerte del abuelo materno que era su figura paterna, conoce al padre y llevan una relacion irregular que ya ahora es nula, ella presenta sentimientos de soledad, no se expresa, no cuenta sus cosas, sentimiento de que en su casa la hacen a un lado, mala apreciacion de su aspecto personal, labilidad emocional, llora de todo, miedo al que dirán. Refiere que tiene eventos de sonambulismo 3 bien reconocidos y hace 22 días presentó dengue y tuvo hipertermia muy marcada y unmomento de estado delirante por lo mismo en la madugada, se salió de la casa, caminó varias calles y se regresó al su casa, la estuvieron buscando y la abuela por su carácter la regaño, que porque hacía eso, que porque se había salido en la madrugada y como la madre estaba en usa, la mujer se sentía responsable de todo. También refiere sintomatología de macropsias y alucinaciones quinestésicas. De forma especifica refiere sintomatología depresiv caracterizada por llanto, aislamiento, no hablar, no salir, sentirse incomprendida, desesperación, de ansiedad onicofagia, se quita la paiel de los dedos (padrastros), se truena los dedos, mueve constantemente los pies. Tuvo problemas en la secundaria por una amistad que le estimuló a no entrar a clases y por ello la reportaron. En casa irritable, contestona, malmodienta, no hace sus quehaceres, dificil para su aseo personal."

                EJEMPLO NÚMERO 8:
                "Hombre escolar, nacido en méxico y criado en eeuu desde los 2 años hasta hace 6 meses. Proviene de una familia integrada, aunque temporalmente separada por la permanencia del padre en eeuu hasta el siguiente mes. La familia está compuesta por la madre, quien es ama de casa, el padre, técnico en aire acondicionado, y un hermano menor de 3 años; es el mayor de 2 hermanos. Se le refiere como un menor aplicado en la escuela con buen desempeño académico, aunque impulsivo, poco tolerante a la frustración y con un patrón de sueño caracterizado por despertares prematuros (4 am). A partir de su ingreso a la primaria, se hicieron evidentes la dificultad para atender indicaciones de la madre, particularmente en actividades que le resultan tediosas, pérdida y descuido de los útiles escolares y una tendencia a la desorganización, principalmente manifiesta en el orden de su habitación. La sintomatología que los motiva a acudir hoy a consulta inició durante el curso de 2o. De primaria, cuando tras un malentendido entre una compañera y él, la madre de esta lo abordó extraoficial y unilateralmente con aparentes amenazas. A partir de entonces, se le comenzó a notar constantemente ansioso/temeroso, tendiente al retraimiento y con disminución de la interacción social, notablemente nervioso con inquietud constante y chupeteo de región perioral, desarrollando una dermatosis como consecuencia. Se observó el incremento de la irritabilidad, oposicionismo y hostigamiento hacia el hermano menor. Por lo anterior y a petición del menor, decidieron cambiar su lugar de residencia a méxico en junio del 2024, permaneciendo el padre en eeuu. La ausencia del padre a quien refiere extrañar; el proceso de adaptación por el cambio cultural, dinámica escolar, residencia con la abuela con quien tiene una relación de conflicto, acentuaron la sintomatología descrita, particularmente la irritabilidad y negativismo "es lo que más tiene, le digo que haga algo y a todo reniega, dice que porque él... También le trae mucho coraje a su hermano y se la pasa molestándolo" sic. Madre. Es por lo anterior que deciden acudir a valoración."

                EJEMPLO NÚMERO 9:
                "El menor tiene el historial que desde prescolar es reportado por inquietud, pero ya en primaria el cuadro es evidente, es un niño inatento, disperso, inquieto, platica, se levanta, deja trabajos incompletos, pierde artículos escolares e incluso ropa, descuidado con el uniforme, se ensucia, es muy poco tolerante con sus compañeros, pelea con ellos, no quiere que hagan ruido, lo que genera ciertas riñas, y por su intolerancia y que quiere corregir a todos ya lo apartan,él se da cuenta de esto, hacen equipos y no lo eligen, pobre concentración, trae la mochila revuelta, este ciclo se ha hecho mas evidente el cuadro por las exigencias propias del 3er año. En casa muy dificil para hacer las tareas, se le tiene que decir muchas veces, y se tarda mucho en terminar cualquier tarea, lo mismo sucede con el aseo personal, sus quehaceres, en la comida está inquieto, no puede hacer mas de una iandicación, come mas o menos bien pero se la pasa platidando en la comida, tiene muy poca tolerancia a todo, siempre dice que se siente "humillado", suele pelear con su hermana de 11a, la socialización es regular, conlal madre se enoa mucho, el estado de ánimo dice que "neutro", se siente ansioso reflejado por estres, irritabilidad, enojo, dice que por estar solo en la escuela, refiere insomnio intermedio, en alguna ocasión llegó a pensar en morir para ir a ver a su papá que murió hace 4 años por covid. La madre lo lleva a un centro llamado cade, se ve el rsumen que les dieron, atendido por un psiquiatra general y una medico general, le prescribieron mfd lp de 20mg 1-0-0, y risperidona 0.25mg-d, se le dio durante un mes, la madre vio muy poca respuesta, y en la escuela con el dx. Que les dieron de tdah mixto bajaron la tensión y bajaron los reportes, por costos ya que subieron la consulta a 1450 pesos y el medicamento, pues mejor ya lo trae a esta institución."

                TEXTO A RESUMIR:
                {transcripcion}
            '''}],)

        else:
            response = openai.chat.completions.create(model=llm_model, messages=[{"role": "user", "content":f'''
            INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta una nueva nota de la evolución clínica del paciente entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción de la consulta proporcionada. Considera que dicha transcripción corresponde a una conversación entre el médico y el paciente, por lo que deberás identificar con claridad quién interviene en cada momento, extrayendo exclusivamente la información clínica relevante que proviene del testimonio del paciente para asegurar una redacción precisa y coherente.

            OBJETIVO: Distingue la información que corresponde a la consulta previa y a la actual, para una nota de evolución clínica del paciente, precisa y concisa que abarque los cambios y continuidad en la presentación de síntomas, desde la última valoración hasta la fecha actual.

            FORMATO REQUERIDO:
            - Idioma español México
            - Texto en un párrafo (sin viñetas, sin espacio entre párrafos ni subtítulos), sin salto doble de línea
            - Extensión de 150 a 200 palabras
            - Lenguaje técnico apropiado para documentación clínica
            - Escrito en tercera persona

            INCLUIR:
            - Antecedentes relevantes del padecimiento y particularmente del estado y evolución desde la última consulta a la actual
            - Cronología detallada de síntomas y manifestaciones (cognitivos, de socialización, emocionales, ansiosos, afectivos o anímicos, del sueño, del apetito y adherencia al tratamiento)
            - Cambios en la severidad e intensidad de los síntomas a lo largo del tiempo
            - Estado actual y evolución de sus relaciones interpersonales significativas y de su funcionalidad en ámbitos social, familiar, académico o laboral según corresponda
            - Factores desencadenantes o exacerbantes identificados por el paciente
            - Estado actual del paciente
            - Después de un salto de línea escribe un análisis donde incluyas las decisiones tomadas sobre el tratamiento, las recomendaciones hechas, los acuerdos hechos y tareas pendientes del paciente, durante la entrevista actual (ej. se decide continuar mismo tratamiento por estabilidad de síntomas, se brinda psicoeducación respecto al apego al tratamiento y se acuerda mejorar el desempeño académico y relación con sus padres, etc.)

            OMITIR:
            - Cualquier información que no forme parte de la evolución clínica del padecimiento
            - Sugerencias o intervenciones terapéuticas expresadas por el médico durante la consulta actual
            - Información personal no relevante
            - Recomendaciones o planes de tratamiento
            - Juicios de valor
            - Diagnósticos
            - Análisis o interpretaciones clínicas
            - Resúmenes finales

            IMPORTANTE: Dado que la transcripción incluye tanto las preguntas del médico como las respuestas del paciente, enfoca tu atención exclusivamente en las intervenciones del paciente que aporten información clínica relevante. Utiliza las preguntas del médico solo como guía para contextualizar las respuestas del paciente, sin incluirlas de forma directa.

            ESTRUCTURA TU RESPUESTA SIGUIENDO ESTILO DE LOS EJEMPLOS DE NOTAS DE EVOLUCIÓN A CONTINUACIÓN:

            Ejemplo 1: “Se encuentra clínicamente estable, su ánimo lo refiere como mayoritariamente bien, salvo los primeros días a partir de que fue despedida, hecho que logró afrontar sin mayores complicaciones; se sintió apoyada por sus padres. Se encuentra buscando empleo, ha tenido entrevistas con adecuado desempeño y "segura" de sí misma; en ciernes entrevista que más le llama la atención. En cuanto a ansiedad ha presentado algunos síntomas asociados al estatus de la relación con su novio de la que en ocasiones se siente con culpa. Refiere un patrón de sueño fragmentado por las micciones nocturnas, 2 por noche. En cuanto al incremento de la dosis de MFD no notó tanto cambio, probablemente, por el contexto laboral. Se queja de hiporexia con impacto ponderal de 3kg en 3 semanas. El consumo de cannabis ha disminuido al igual que el craving.”

            Ejemplo 2: “La paciente refiere que hacia el mes de diciembre después de entre 1 a 2 meses de haber suspendido la sertralina por "sentirse bien" comenzó con irritabilidad por lo que acudió a psicología con mejoría sustancial. Acude el día de hoy porque desde hace 2 meses ha notado anhedonia, llanto espontáneo, hiperfagia con aumento de peso lo que impacta de forma negativa en su ánimo. Ha tenido apatía, pérdida de interés, ha dejado de cocinar, lavar su ropa, fatiga, ha perdido el interés en su arreglo, baja en la líbido, pensamientos pasivos de muerte, culpa, minusvalía con recriminación a sí misma y tendencia al aislamiento. Comienza con insomnio de conciliación; hipoprosexia. No ha presentado síntomas ansiosos.”

            Ejemplo 3: “Refiere que no ha notado cambios sustantivos respecto a la valoración previa salvo que ya ha tenido iniciativa para avanzar en los pendientes personales y encomendados. Por ejemplo hoy que no tuvo clase se puso a aspirar y lavar la alfombra de su cuarto, plan que tenía 2 meses en planes "antes me hubiera puesto hacer otra cosa". Ha tenido dificultades para despertar e ir a hacer ejercicio. Continúa con dificultades para conciliar el sueño aunque puede estar asociado a que, aunque se va a dormir a las 10pm, lo hace mientras está en videollamada con su novia. Una vez conciliado el sueño no despierta por las madrugadas y despierta hacia las 6:40 am para sus actividades, buen patrón alimenticio y de sueño. En lo escolar se siente un poco más social con mayor participación en clase e interacción con sus compañeros; en lo atencional ha mejorado sustantivamente en buena medida a que ha adoptado cambios como despejarse previo clase "voy al baño me mojo la cara, voy por una bebida y ya me enfoco mejor (sic)". En relación a la reducción de lorazepam no notó cambio alguno. Dice sentirse emocionado porque lo visitará su novia dentro de 1 mes. He disfrutado jugar XBOX, lavar los carros y cocinar.”

            Ejemplo 4: “Acude paciente refiriéndo continuar con estabilidad de sus síntomas, es decir, con la disminución de la ansiedad y síntomas depresivos además de la casi ausencia de los pensamientos de culpa/minusvalía (los de muerte están ausentes); sin embargo refiere que algunos días, los menos, ha tenido algunas bajas en el estado de ánimo sin una causa identificada. Adecuada adherencia al tratamiento, patrón de sueño y alimenticio. También ha notado menos "fastidio" por estar haciendo su trabajo además de menor irritabilidad, mayor energía con mejor concentración y rendimiento en su empleo. En cuanto a la ansiedad casi han desaparecido las rumiaciones ansiógenas y cuando estas se presentan logra identificarlas y darles cauce. Continúa con actividad física a base de rutina dentro de casa con una frecuencia de 3 días por semana durante 40 minutos. Subjetivamente califica su estado de ánimo de un 8-9/10.”

            Sección Adicional (Incluir al Final de la Descripción Principal)
            Usa exclusivamente la información extraída de la transcripción para desarrollar lo siguiente:

            1. Examen Mental
                - Incluye solo la información dentro de la transcripción y en caso de que no este omitela, no menciones que no esta
                - Incluye la descripción basado en los ejemplos dados y en el siguiente orden: Apariencia (higiene, aliño), estado de alerta, atención, motricidad, estado de ánimo, afecto al momento de la entrevis. Características del discurso (si es
                    espontáneo, inducido, fluido o no, parco, abundante o prolijo, coherente, congruente, volumen, velocidad y latencia de respuesta), pensamiento (lineal, circunstancial, circunloquial, tangencial, disgregado), conetnido del pensamiento (preocupaciones, rumiaciones, ideas obsesivas, intrusivas, etc.)
                    presencia de psicosis (alucinaciones o delirios), ideación o fenómeno suicida, intrsopección del paciente sobre su enfermedad, juicio (2 a 7 años de edad = preoperacional, 7 a 12 años = concreta y > 12 años formal. Además si el juicio esta dentro del marco de la realidad o fuera en caso de que haya síntomas de psicosis),control de impulsos)
                    Ejemplos de examen mental:
                    - Ejemplo 1: Se trata hombre adolescente con adecuada higiene y aliño, alerta, atento, orientado cooperador de ánimo eutímico con un afecto congruente y resonante. Discurso inducido, fludio, coherente, congruente,
                    volumen, velocidad y latencia de respuesta adecuados. Pensamiento lineal sin que al momento de la entrevista se encuentre psicosis o fenómeno suicida. Adecuada introspección, juicio concreto y buen
                    control de impulsos.
                    - Ejemplo 2: Se trata de mujer con adecuada higiene y aliño, ropa acorde a clima y situación, alerta, atenta, orientada, cooperadora con inquietud motriz circunscrita a pies y manos. Refiere un ánimo ansioso con afecto congruente. Discurso
                    inducido, parco, coherente, congruente, volumen bajo, velocidad adecuada y latencia de respuesta discretamente aumentada. Pensamiento lineal sin datos de psicosis o ideación suicida. Parcial introspección,
                    juicio formal y buen control de impulsos.
                    - Ejemplo 3: Hombre escolar con regular higiene y aliño, alerta, hipoproséxico, hipercinetico, incapaz de mantenerse en su sitio incluso deambulando por el consultorio. Parcialmente cooperador. Ánimo referido como irritable con
                    afecto disonante. Discurso espontáneo, fluido, intrusivo, taquilálico coherente, congruente, con velocidad y volumen adecuados; latencia de respues disminuida. Pensamiento circunstancial y prolijo sin ideación suicida
                    o psicosis. Pobre introspección, juicio concreto y pobre control de impulsos.
            2. Interacción entre medicamentos
                - Identifica los medicamentos que esta o estará tomando y en base a tu conocimiento determina si hay alguna interacción entre ellos con una mención breve del tipo de interacción

            TEXTO A RESUMIR:
            {transcripcion}
        '''}],)
        response = response.choices[0].message.content
        output_text = re.sub(r'<think>[\s\S]*?</think>', '', response).strip()
        return output_text
    
    
     # Inicializar estado con claves únicas
    audio_key = f"audio_data_{nota}"
    transcription_key = f"transcripcion_{nota}"
    processing_key = f"is_processing_{nota}"
    audio_signature_key = f"audio_signature_{nota}"
    last_audio_key = f"last_audio_{nota}"
    
    # Inicializar session state
    for key in [audio_key, transcription_key, audio_signature_key, last_audio_key]:
        if key not in st.session_state:
            st.session_state[key] = None

    if processing_key not in st.session_state:
        st.session_state[processing_key] = False

    # Crear una key única para el mic_recorder que cambie periódicamente
    if "recorder_refresh" not in st.session_state:
        st.session_state["recorder_refresh"] = 0
    
    # Layout principal
    st.subheader("🎙️ Grabación y Transcripción de Audio")
    
    # Crear columnas
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Componente de grabación con key única
        recorder_key = f"mic_recorder_{nota}_{st.session_state['recorder_refresh']}"
        
        audio_value = mic_recorder(
            start_prompt="🎙️ Iniciar Grabación",
            stop_prompt="⏹️ Detener Grabación",
            just_once=False,
            use_container_width=True,
            format="webm",
            key=recorder_key
        )
        
        # Detectar nuevo audio o cambios
        current_audio = None
        current_signature = None
        
        if audio_value and audio_value.get('bytes'):
            time.sleep(1)
            current_audio = audio_value['bytes']
            current_signature = get_audio_signature(current_audio)
            
            # Verificar si es un audio nuevo o diferente
            if (current_signature != st.session_state[audio_signature_key] or 
                st.session_state[audio_key] is None):
                
                st.session_state[audio_key] = current_audio
                st.session_state[audio_signature_key] = current_signature
                st.session_state[last_audio_key] = current_audio
                
                # Forzar rerun para actualizar la interfaz
                st.rerun()

    with col2:
        # Botón de refrescar grabador si hay problemas
        if st.button("🔄 Refrescar Grabador", use_container_width=True, 
                    help="Si el grabador no responde, usa este botón"):
            st.session_state["recorder_refresh"] += 1
            st.session_state[audio_key] = None
            st.session_state[audio_signature_key] = None
            st.rerun()

    # Mostrar información del audio si existe
    if st.session_state[audio_key]:
        st.success("✅ Audio grabado correctamente")
        
        # Información del audio
        try:
            audio_size_mb = len(st.session_state[audio_key]) / (1024 * 1024)
            audio_io = io.BytesIO(st.session_state[audio_key])
            audio_segment = AudioSegment.from_file(audio_io, format="webm")
            duration_seconds = len(audio_segment) / 1000
            
            col_info1, col_info2 = st.columns(2)
            with col_info1:
                st.metric("Tamaño", f"{audio_size_mb:.2f} MB")
            with col_info2:
                st.metric("Duración", f"{duration_seconds:.1f} seg")
                
        except Exception as e:
            st.warning(f"No se pudo analizar el audio: {str(e)}")
        
        # Reproductor de audio
        st.audio(st.session_state[audio_key], format="audio/webm")
        
        # Advertencia para audios largos
        try:
            if duration_seconds > 600:  # 10 minutos
                st.warning("⚠️ Audio muy largo. La transcripción puede tomar más tiempo.")
        except:
            pass

    # Sección de transcripción
    st.divider()
    
    col_trans1, col_trans2, col_trans3 = st.columns([2, 1, 1])
    
    with col_trans1:
        # Botón de transcripción
        can_transcribe = (
            st.session_state[audio_key] is not None and 
            not st.session_state[processing_key]
        )
        
        if st.button(
            "🔮 Transcribir Audio", 
            use_container_width=True,
            disabled=not can_transcribe,
            type="primary" if can_transcribe else "secondary"
        ):
            if st.session_state[audio_key]:
                st.session_state[processing_key] = True
                
                try:
                    with st.spinner("🔄 Procesando transcripción... Por favor espere."):
                        progress_bar = st.progress(0)
                        progress_bar.progress(25, "Preparando audio...")
                        
                        audio_io = io.BytesIO(st.session_state[audio_key])
                        progress_bar.progress(50, "Enviando a transcripción...")
                        
                        transcription = transcribe_audio_with_retry(audio_io)
                        progress_bar.progress(75, "Generando resumen...")
                        
                        if transcription:
                            processed_result = process_transcription(transcription, nota)
                            st.session_state[transcription_key] = processed_result
                            progress_bar.progress(100, "¡Completado!")
                            time.sleep(1)
                            progress_bar.empty()
                            st.success("✅ Transcripción completada exitosamente")
                        else:
                            progress_bar.empty()
                            st.error("❌ No se pudo completar la transcripción")
                
                except Exception as e:
                    st.error(f"Error durante el procesamiento: {str(e)}")
                
                finally:
                    st.session_state[processing_key] = False

    with col_trans2:
        # Botón para limpiar todo
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            keys_to_clear = [audio_key, transcription_key, audio_signature_key, last_audio_key]
            for key in keys_to_clear:
                if key in st.session_state:
                    st.session_state[key] = None
            st.session_state[processing_key] = False
            st.session_state["recorder_refresh"] += 1
            st.success("✅ Todo limpiado")
            time.sleep(1)
            st.rerun()

    with col_trans3:
        # Botón para solo limpiar transcripción
        if st.button("📝 Nueva Transcripción", use_container_width=True):
            st.session_state[transcription_key] = ""
            st.success("✅ Lista para nueva transcripción")

    # Estado actual
    if st.session_state[processing_key]:
        st.info("🔄 Procesando audio... Por favor espere y no recargue la página.")
    elif not st.session_state[audio_key]:
        st.info("🎙️ Haga clic en 'Iniciar Grabación' para comenzar")
    elif st.session_state[audio_key] and not st.session_state[transcription_key]:
        st.info("🎵 Audio listo para transcribir. Haga clic en 'Transcribir Audio'")

    # Mostrar transcripción si existe
    if st.session_state[transcription_key]:
        st.divider()
        st.subheader("📄 Resultado de la Transcripción")
        with st.expander("Ver transcripción completa", expanded=True):
            st.text_area(
                "Transcripción y Resumen:", 
                st.session_state[transcription_key], 
                height=400,
                key=f"transcription_display_{nota}"
            )
    # Añadir al final de tu función, antes del return
    if st.checkbox("🔧 Modo Debug"):
        st.write("**Estado del Sistema:**")
        st.write(f"Audio en memoria: {st.session_state[audio_key] is not None}")
        # st.write(f"Hash actual: {st.session_state[audio_hash_key]}")
        st.write(f"Procesando: {st.session_state[processing_key]}")
        st.write(f"Refresh count: {st.session_state.get('recorder_refresh', 0)}")
        if audio_value:
            st.write(f"Audio_value existe: {len(audio_value.get('bytes', b''))} bytes")
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
def initialize_audio_system():
    """
    Inicializa el sistema de audio y verifica compatibilidad del navegador.
    """
    
    # CSS personalizado para mejorar la UI
    st.markdown("""
    <style>
    /* Estilos para mejorar la visualización en móvil */
    .stButton > button {
        width: 100%;
        margin: 5px 0;
    }
    
    .stTextArea > div > div > textarea {
        font-family: 'Courier New', monospace;
        font-size: 14px;
    }
    
    /* Responsive design */
    @media (max-width: 768px) {
        .stColumns > div {
            margin-bottom: 1rem;
        }
    }
    
    /* Animación para estado de procesamiento */
    @keyframes processing {
        0% { opacity: 0.6; }
        50% { opacity: 1; }
        100% { opacity: 0.6; }
    }
    
    .processing-indicator {
        animation: processing 2s ease-in-out infinite;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # JavaScript para verificar compatibilidad
    components.html("""
    <script>
    // Verificar compatibilidad del navegador
    function checkBrowserCompatibility() {
        const isCompatible = !!(
            navigator.mediaDevices &&
            navigator.mediaDevices.getUserMedia &&
            window.MediaRecorder
        );
        
        if (!isCompatible) {
            alert('Tu navegador no es compatible con la grabación de audio. Por favor usa Chrome, Firefox o Safari actualizado.');
        }
        
        // Verificar si es iOS y mostrar instrucciones especiales
        const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
        if (isIOS) {
            console.log('Dispositivo iOS detectado. Asegúrate de permitir el acceso al micrófono.');
        }
    }
    
    checkBrowserCompatibility();
    </script>
    """, height=0)
    
    return True
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
