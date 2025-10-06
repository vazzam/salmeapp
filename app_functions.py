
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
