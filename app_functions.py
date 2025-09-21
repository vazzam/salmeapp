import asyncio
import concurrent.futures
import gc
import hashlib
import io
import os
import queue
import random
import re
import tempfile
import threading
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional, Tuple

import google.generativeai as genai
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from pydub import AudioSegment
from pymongo import MongoClient
from streamlit_mic_recorder import mic_recorder
from unidecode import unidecode

# Configuración de directorios y variables
load_dotenv()
mongodb_uri = os.getenv("MONGODB_URI")
gemini_api = os.getenv("GEMINI_API")
deepinfra_api = os.getenv("DEEPINFRA_API")

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)

# Configuración de APIs
genai.configure(api_key=gemini_api)
openai = OpenAI(
    api_key=deepinfra_api,
    base_url="https://api.deepinfra.com/v1/openai",
)

# Thread pool executor para operaciones pesadas
executor = concurrent.futures.ThreadPoolExecutor(max_workers=3)

class AudioProcessor:
    """Clase optimizada para procesamiento de audio con gestión de memoria"""
    
    MAX_CHUNK_SIZE = 5 * 1024 * 1024  # 5MB chunks
    MAX_AUDIO_SIZE = 25 * 1024 * 1024  # 25MB límite API
    
    @staticmethod
    def save_audio_to_temp(audio_bytes: bytes, suffix: str = ".webm") -> Path:
        """Guarda audio en archivo temporal con limpieza automática"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        temp_dir = tempfile.gettempdir()
        file_path = Path(temp_dir) / f"rec_{ts}{suffix}"
        
        # Escribir en chunks para evitar picos de memoria
        chunk_size = 1024 * 1024  # 1MB chunks
        with open(file_path, "wb") as f:
            for i in range(0, len(audio_bytes), chunk_size):
                f.write(audio_bytes[i:i+chunk_size])
        
        return file_path
    
    @staticmethod
    def get_audio_hash(audio_bytes: bytes) -> str:
        """Genera hash único para el audio"""
        return hashlib.md5(audio_bytes[:1000] + audio_bytes[-1000:]).hexdigest()
    
    @staticmethod
    def optimize_audio_for_api(file_path: Path) -> Tuple[Path, int]:
        """Optimiza audio para API: reduce bitrate si es necesario"""
        try:
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            
            # Optimizaciones para reducir tamaño
            if duration_ms > 300000:  # > 5 minutos
                # Reducir bitrate para audios largos
                audio = audio.set_frame_rate(16000).set_channels(1)
                optimized_path = file_path.with_suffix(".optimized.webm")
                audio.export(optimized_path, format="webm", bitrate="32k")
                
                # Limpiar archivo original
                os.remove(file_path)
                return optimized_path, duration_ms
            
            return file_path, duration_ms
            
        except Exception as e:
            st.error(f"Error optimizando audio: {e}")
            return file_path, 0
    
    @staticmethod
    def split_audio_smart(file_path: Path, max_duration_ms: int = 300000) -> list:
        """División inteligente de audio con overlapping para contexto"""
        try:
            audio = AudioSegment.from_file(file_path)
            duration_ms = len(audio)
            
            if duration_ms <= max_duration_ms:
                return [file_path]
            
            segments = []
            overlap_ms = 2000  # 2 segundos de overlap
            
            for start_ms in range(0, duration_ms, max_duration_ms - overlap_ms):
                end_ms = min(start_ms + max_duration_ms, duration_ms)
                segment = audio[start_ms:end_ms]
                
                # Guardar segmento en archivo temporal
                segment_path = file_path.parent / f"{file_path.stem}_seg{len(segments)}.webm"
                segment.export(segment_path, format="webm", bitrate="32k")
                segments.append(segment_path)
            
            # Limpiar memoria
            del audio
            gc.collect()
            
            return segments
            
        except Exception as e:
            st.error(f"Error dividiendo audio: {e}")
            return [file_path]

class TranscriptionService:
    """Servicio optimizado para transcripción con reintentos y timeout"""
    
    def __init__(self, client):
        self.client = client
        self.max_retries = 3
        self.timeout = 120  # 2 minutos timeout
    
    def transcribe_with_timeout(self, audio_path: Path, language: str = "es") -> Optional[str]:
        """Transcribe con timeout y manejo de errores mejorado"""
        
        def _transcribe():
            try:
                with open(audio_path, "rb") as audio_file:
                    response = self.client.audio.transcriptions.create(
                        model="openai/whisper-large-v3-turbo",
                        file=(audio_path.name, audio_file, "audio/webm"),
                        language=language,
                        timeout=self.timeout
                    )
                return response.text
            except Exception as e:
                return f"Error: {str(e)}"
        
        # Ejecutar con timeout usando thread
        future = executor.submit(_transcribe)
        try:
            result = future.result(timeout=self.timeout + 10)
            return result if not result.startswith("Error:") else None
        except concurrent.futures.TimeoutError:
            future.cancel()
            return None
    
    def transcribe_segments_parallel(self, segments: list) -> str:
        """Transcribe múltiples segmentos en paralelo"""
        transcriptions = []
        
        with st.spinner(f"Transcribiendo {len(segments)} segmentos..."):
            # Crear barra de progreso
            progress_bar = st.progress(0)
            
            # Usar ThreadPoolExecutor para paralelizar
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
                futures = []
                for i, segment in enumerate(segments):
                    future = executor.submit(self.transcribe_with_timeout, segment)
                    futures.append((i, future))
                
                # Recolectar resultados en orden
                for i, future in futures:
                    try:
                        result = future.result(timeout=self.timeout + 20)
                        if result:
                            transcriptions.append(result)
                        progress_bar.progress((i + 1) / len(segments))
                    except Exception as e:
                        st.warning(f"Error en segmento {i+1}: {e}")
                        continue
            
            progress_bar.empty()
        
        # Limpiar archivos temporales
        for segment in segments:
            try:
                os.remove(segment)
            except:
                pass
        
        return " ".join(transcriptions)

def audio_recorder_transcriber(nota: str):
    """Versión optimizada del grabador y transcriptor de audio"""
    
    # Inicializar servicios
    audio_processor = AudioProcessor()
    transcription_service = TranscriptionService(openai)
    
    # Keys únicos para session state
    audio_key = f"audio_data_{nota}"
    transcription_key = f"transcripcion_{nota}"
    processing_key = f"is_processing_{nota}"
    audio_hash_key = f"audio_hash_{nota}"
    
    # Inicializar session state
    for key in [audio_key, transcription_key, audio_hash_key]:
        if key not in st.session_state:
            st.session_state[key] = None
    
    if processing_key not in st.session_state:
        st.session_state[processing_key] = False
    
    # UI Principal
    st.subheader("🎙️ Grabación y Transcripción de Audio Optimizada")
    
    # Información de estado
    if st.session_state[processing_key]:
        st.warning("⏳ Procesando audio... No recargue la página")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        # Grabador con configuración optimizada para móviles
        audio_value = mic_recorder(
            start_prompt="🎙️ Iniciar Grabación",
            stop_prompt="⏹️ Detener Grabación",
            just_once=False,  # Cambiar a False para mejor manejo
            use_container_width=True,
            format="webm",
            key=f"mic_{nota}_{st.session_state.get('recorder_version', 0)}"
        )
        
        # Procesar nuevo audio
        if audio_value and audio_value.get('bytes'):
            current_hash = audio_processor.get_audio_hash(audio_value['bytes'])
            
            # Verificar si es audio nuevo
            if current_hash != st.session_state[audio_hash_key]:
                st.session_state[audio_key] = audio_value['bytes']
                st.session_state[audio_hash_key] = current_hash
                st.success("✅ Audio capturado correctamente")
                
                # Mostrar información
                size_mb = len(audio_value['bytes']) / (1024 * 1024)
                st.info(f"Tamaño: {size_mb:.2f} MB")
    
    with col2:
        if st.button("🔄 Nuevo Audio", use_container_width=True):
            st.session_state[audio_key] = None
            st.session_state[audio_hash_key] = None
            st.session_state[transcription_key] = None
            if 'recorder_version' not in st.session_state:
                st.session_state['recorder_version'] = 0
            st.session_state['recorder_version'] += 1
            st.rerun()
    
    # Reproductor de audio
    if st.session_state[audio_key]:
        st.audio(st.session_state[audio_key], format="audio/webm")
    
    # Sección de transcripción
    st.divider()
    
    col_trans1, col_trans2 = st.columns([2, 1])
    
    with col_trans1:
        if st.button(
            "🔮 Transcribir Audio",
            use_container_width=True,
            disabled=not st.session_state[audio_key] or st.session_state[processing_key],
            type="primary"
        ):
            if st.session_state[audio_key]:
                st.session_state[processing_key] = True
                
                try:
                    # Guardar audio en archivo temporal
                    with st.spinner("Preparando audio..."):
                        audio_path = audio_processor.save_audio_to_temp(
                            st.session_state[audio_key]
                        )
                    
                    # Optimizar audio
                    with st.spinner("Optimizando audio..."):
                        optimized_path, duration_ms = audio_processor.optimize_audio_for_api(
                            audio_path
                        )
                    
                    # Dividir si es necesario
                    segments = []
                    if duration_ms > 300000:  # > 5 minutos
                        with st.spinner("Dividiendo audio largo..."):
                            segments = audio_processor.split_audio_smart(optimized_path)
                    else:
                        segments = [optimized_path]
                    
                    # Transcribir
                    if len(segments) > 1:
                        transcription = transcription_service.transcribe_segments_parallel(segments)
                    else:
                        with st.spinner("Transcribiendo..."):
                            transcription = transcription_service.transcribe_with_timeout(segments[0])
                    
                    # Procesar transcripción
                    if transcription:
                        with st.spinner("Generando resumen..."):
                            # Ejecutar en thread para no bloquear
                            future = executor.submit(process_transcription_optimized, transcription, nota)
                            result = future.result(timeout=60)
                            st.session_state[transcription_key] = result
                        
                        st.success("✅ Transcripción completada")
                    else:
                        st.error("❌ Error en la transcripción")
                    
                    # Limpiar archivos temporales
                    for file in [audio_path, optimized_path] + segments:
                        try:
                            if file.exists():
                                os.remove(file)
                        except:
                            pass
                    
                    # Liberar memoria
                    gc.collect()
                    
                except Exception as e:
                    st.error(f"Error: {str(e)}")
                finally:
                    st.session_state[processing_key] = False
    
    with col_trans2:
        if st.button("🗑️ Limpiar Todo", use_container_width=True):
            for key in [audio_key, transcription_key, audio_hash_key]:
                st.session_state[key] = None
            st.session_state[processing_key] = False
            st.rerun()
    
    # Mostrar transcripción
    if st.session_state[transcription_key]:
        st.divider()
        st.subheader("📄 Resultado")
        st.text_area(
            "Transcripción y Resumen:",
            st.session_state[transcription_key],
            height=400,
            key=f"trans_display_{nota}"
        )
    
    return st.session_state[transcription_key]

def process_transcription_optimized(transcription: str, nota: str) -> str:
    """Procesamiento optimizado de transcripción con manejo de errores"""
    try:
        # Intentar con Gemini primero
        result1 = resumen_transcripcion_optimized(transcription, nota, "gemini")
        
        # Intentar con segundo modelo en paralelo
        try:
            future = executor.submit(resumen_transcripcion_optimized, transcription, nota, "qwen")
            result2 = future.result(timeout=30)
            return f"{result1}\n\n--- VERSIÓN ALTERNATIVA ---\n\n{result2}"
        except:
            return result1
            
    except Exception as e:
        st.warning(f"Error en resumen: {e}")
        return transcription

def resumen_transcripcion_optimized(transcripcion: str, nota: str, model_type: str = "gemini") -> str:
    """Versión optimizada del resumen con timeout y caché"""
    
    # Limitar longitud de transcripción si es muy larga
    max_length = 10000
    if len(transcripcion) > max_length:
        transcripcion = transcripcion[:max_length] + "... [transcripción truncada]"
    
    prompt = _get_prompt_for_nota(nota, transcripcion)
    
    try:
        if model_type == "gemini":
            model = genai.GenerativeModel('gemini-2.5-flash')
            response = model.generate_content(prompt)
            return response.text
        else:
            response = openai.chat.completions.create(
                model='Qwen/Qwen3-32B',
                messages=[{"role": "user", "content": prompt}],
                timeout=30
            )
            return response.choices[0].message.content
    except Exception as e:
        return f"Error generando resumen: {str(e)}"

def _get_prompt_for_nota(nota: str, transcripcion: str) -> str:
    """Genera el prompt según el tipo de nota"""
    if nota == "primera":
        return f'''
        INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución 
        detallada del padecimiento basándote en la transcripción de consulta.
        
        TEXTO A RESUMIR: {transcripcion}
        '''
    elif nota == "primera_paido":
        return f'''
        INSTRUCCIONES: Asume el rol de un psiquiatra infantil. Redacta la evolución 
        del padecimiento basándote en la transcripción.
        
        TEXTO A RESUMIR: {transcripcion}
        '''
    else:
        return f'''
        INSTRUCCIONES: Redacta una nota de evolución clínica concisa basándote 
        en la transcripción de consulta.
        
        TEXTO A RESUMIR: {transcripcion}
        '''

# Mantener funciones existentes necesarias
def rand_ta():
    ta = f'{random.randint(100,130)}/{random.randint(66,78)}'
    return ta

def procesar_texto(texto):
    patron = r"^```(.*?)```$"
    coincidencia = re.search(patron, texto, re.DOTALL)
    return coincidencia.group(1) if coincidencia else texto

def stored_data(name):
    data = {
        'escalas': ['RASS.pdf','bush y francis.pdf', 'simpson angus.pdf', 'gad7.pdf', 
                   'sad persons.pdf', 'young.pdf', 'fab.pdf', 'assist.pdf', 
                   'dimensional.pdf', 'psp.pdf', 'yesavage.pdf', 'phq9.pdf', 
                   'Escala dimensional de psicosis.pdf', 'moca.pdf', 'moriski-8.pdf', 
                   'mdq.pdf', 'calgary.pdf', 'eeag.pdf', 'madrs.pdf'],
        'gpc': ['SSA-222-09 Diagnostico y tratamiento de la esquizofrenia',
               'IMSS 170-09 Diagnostico y tratamiento del trastorno bipolar',
               'IMSS-392-10 Diagnostico y tratamiento del trastorno de ansiedad en el adulto',
               'APA- Practice guideline for the treatment of patients with borderline personality disorder',
               'IMSS-161-09 Diagnostico y tratamiento del trastorno depresivo en el adulto',
               'IMSS-528-12 Diagnostico y manejo de los trastornos del espectro autista',
               'IMSS-515-11 Diagnostico y manejo del estres post traumatico',
               'SS-343-16 Diagnostico y tratamiento del consumo de marihuana en adultos en primer y segundo nivel de atención',
               'SS-023-08 Prevención, detección y consejeria en adicciones para adolescentes y adultos.',
               'IMSS-385-10 Diagnostico y tratamiento de los trastornos del Sueño',
               'SS-666-14 Prevención, diagnóstico y manejo de la depresión prenatal',
               'SS-294-10 Detección y atención de violencia de pareja en adulto',
               'ss-210-09 Diagnostico y tratamiento de epilepsia en el adulto',
               'IMSS-465-11 Prevención, diagnóstico y tratamiento del DELIRIUM en el adulto mayor hospitalizado']
    }
    return data[name]

# Mantener el resto de funciones existentes sin cambios...
def calculate_age(born):
    today = datetime.now()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def clin_merge(scale):
    return f' {scale}, ' if scale != '' else ''

def radio_check(var):
    return 'Yes' if var != '' else ''

def update_dict(dic, var):
    dic.update({var: 'Yes'})

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
