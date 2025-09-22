# app_functions.py
# -*- coding: utf-8 -*-

import os
import io
import re
import time
import uuid
import json
import random
import threading
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

import requests
import streamlit as st
from dotenv import load_dotenv
from unidecode import unidecode
from pymongo import MongoClient
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from openai import OpenAI
import google.generativeai as genai
from streamlit_mic_recorder import mic_recorder
from streamlit.components.v1 import html as st_html

# ==========================
# Config y constantes
# ==========================
load_dotenv()

RECORDINGS_DIR = Path("recordings")
RECORDINGS_DIR.mkdir(exist_ok=True)

MONGODB_URI = os.getenv("MONGODB_URI")
GEMINI_API = os.getenv("GEMINI_API")
DEEPINFRA_API = os.getenv("DEEPINFRA_API")
DEEPINFRA_BASE = "https://api.deepinfra.com/v1/openai"

# Configura Gemini
if GEMINI_API:
    genai.configure(api_key=GEMINI_API)

# Cliente OpenAI-compatible (DeepInfra) para chat completions
openai_client = OpenAI(
    api_key=DEEPINFRA_API,
    base_url=DEEPINFRA_BASE,
)

# Whisper (DeepInfra) vía endpoint OpenAI-compatible (HTTP)
WHISPER_MODEL = "openai/whisper-large-v3-turbo"

# Límite seguro de tamaño y segmentación
MAX_FILE_MB = 24.0         # Límite seguro antes de segmentar (API ~25MB)
SEGMENT_SECONDS = 300      # 5 min por segmento (ajusta si deseas)

# ==========================
# Utilidades de archivos/audio (ffmpeg/ffprobe)
# ==========================
def save_audio_bytes_to_file(audio_bytes: bytes, suffix: str = ".webm") -> Path:
    """Guarda bytes de audio a un archivo en disco con nombre único."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    file_path = RECORDINGS_DIR / f"rec_{ts}{suffix}"
    with open(file_path, "wb") as f:
        f.write(audio_bytes)
    return file_path

def file_size_mb(path: Path) -> float:
    return path.stat().st_size / (1024 * 1024)

def ffprobe_duration_seconds(path: Path) -> float:
    """Obtiene duración de audio con ffprobe (rápido, sin decodificar todo)."""
    cmd = [
        "ffprobe", "-v", "error", "-show_entries",
        "format=duration", "-of",
        "default=noprint_wrappers=1:nokey=1", str(path)
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        return float(out.decode().strip())
    except Exception:
        return 0.0

def segment_audio_ffmpeg_copy(input_path: Path, segment_seconds: int = SEGMENT_SECONDS) -> List[Path]:
    """
    Segmenta sin recodificar (c copy). Ideal para webm/opus.
    """
    out_dir = input_path.parent / f"{input_path.stem}_parts"
    out_dir.mkdir(exist_ok=True)
    pattern = out_dir / "part_%03d.webm"

    cmd = [
        "ffmpeg", "-hide_banner", "-y", "-i", str(input_path),
        "-c", "copy", "-map", "0",
        "-f", "segment",
        "-segment_time", str(segment_seconds),
        "-reset_timestamps", "1",
        str(pattern)
    ]
    subprocess.run(cmd, check=True)
    parts = sorted(out_dir.glob("part_*.webm"))
    return parts

def convert_to_wav_ffmpeg(input_path: Path, out_mono_16k: bool = True) -> Path:
    """
    Conversión opcional a WAV usando ffmpeg (evitar si la API acepta webm/opus).
    """
    wav_path = input_path.with_suffix(".wav")
    cmd = ["ffmpeg", "-hide_banner", "-y", "-i", str(input_path)]
    if out_mono_16k:
        cmd += ["-ac", "1", "-ar", "16000"]
    cmd += [str(wav_path)]
    subprocess.run(cmd, check=True)
    return wav_path

# ==========================
# DeepInfra Whisper (HTTP)
# ==========================
def transcribe_file_deepinfra(file_path: Path, language="es", timeout=(30, 600)) -> str:
    """
    Llama al endpoint OpenAI-compatible de DeepInfra con requests,
    usando archivo desde disco para evitar ocupar RAM.
    """
    url = f"{DEEPINFRA_BASE}/audio/transcriptions"
    headers = {"Authorization": f"Bearer {DEEPINFRA_API}"}
    data = {"model": WHISPER_MODEL, "language": language}
    with open(file_path, "rb") as f:
        files = {"file": (file_path.name, f, "audio/webm")}
        resp = requests.post(url, headers=headers, data=data, files=files, timeout=timeout)
    resp.raise_for_status()
    payload = resp.json()
    return payload.get("text", "")

# ==========================
# Resumen/LLMs auxiliares
# ==========================
def resumen_transcripcion(transcripcion: str, nota: str) -> str:
    """
    Versión con Gemini. Requiere GEMINI_API.
    """
    model = genai.GenerativeModel('gemini-2.5-flash') if GEMINI_API else None
    if not model:
        # Fallback
        return transcripcion

    if nota == "primera":
        prompt = f"""
INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento de un paciente basándote en la transcripción de consulta proporcionada. La transcripción es una conversación entre médico y paciente: identifica quién habla en cada intervención para asegurar coherencia.

TEXTO A RESUMIR:
{transcripcion}
"""
    elif nota == "primera_paido":
        prompt = f"""
Instrucciones Generales
Asume el rol de un psiquiatra infantil especializado. Con base en la transcripción de la consulta (médico, paciente y uno de los padres), redacta la evolución detallada. Identifica claramente quién interviene en cada turno.

TEXTO A RESUMIR:
{transcripcion}
"""
    else:
        prompt = f"""
INSTRUCCIONES: Asume el rol de un psiquiatra y redacta una nota de evolución entre la consulta previa y la actual, precisa y concisa, basándote en la transcripción. Identifica claramente quién interviene y extrae exclusivamente la información clínica relevante del paciente.

TEXTO A RESUMIR:
{transcripcion}
"""
    response = model.generate_content(prompt)
    return getattr(response, "text", "") or ""

def resumen_transcripcion2(transcripcion: str, nota: str) -> str:
    """
    Versión con modelo adicional vía DeepInfra (OpenAI-compatible).
    """
    llm_model = 'Qwen/Qwen3-32B'
    if nota == "primera":
        user_content = f"""
INSTRUCCIONES: Asume el rol de un psiquiatra especializado y redacta la evolución detallada del padecimiento del paciente con base en la transcripción. Distingue interlocutores (médico/paciente) para coherencia.

TEXTO A RESUMIR:
{transcripcion}
"""
    elif nota == "primera_paido":
        user_content = f"""
Instrucciones Generales
Asume el rol de un psiquiatra infantil especializado. Con base en la transcripción (médico, paciente y uno de los padres), redacta la evolución detallada. Identifica claramente quién interviene.

TEXTO A RESUMIR:
{transcripcion}
"""
    else:
        user_content = f"""
INSTRUCCIONES: Redacta una nota de evolución entre consulta previa y actual, precisa y concisa, basada en la transcripción. Identifica interlocutores y extrae información clínica relevante.

TEXTO A RESUMIR:
{transcripcion}
"""

    resp = openai_client.chat.completions.create(
        model=llm_model,
        messages=[{"role": "user", "content": user_content}],
    )
    response_text = resp.choices[0].message.content
    # Limpia tags de pensamiento si existieran
    response_text = re.sub(r'<think>[\s\S]*?</think>', '', response_text).strip()
    return response_text

def _process_transcription_text(transcription_text: str, nota: str) -> str:
    """
    Aplica los dos resúmenes y concatena resultados.
    """
    try:
        summarized_1 = resumen_transcripcion(transcription_text, nota)
    except Exception as e:
        summarized_1 = f"[Resumen 1 falló: {e}]\n{transcription_text}"

    try:
        summarized_2 = resumen_transcripcion2(transcription_text, nota)
        return summarized_1 + "\n\n---\nVersión 2:\n" + summarized_2
    except Exception as e:
        return summarized_1 + f"\n\n[Resumen 2 falló: {e}]"

# ==========================
# Job de transcripción en background
# ==========================
class TranscriptionJob:
    def __init__(self, audio_path: Path, nota: str):
        self.id = uuid.uuid4().hex
        self.audio_path = audio_path
        self.nota = nota
        self.progress = 0.0
        self.status = "queued"   # queued|running|done|error
        self.result = ""
        self.error: Optional[str] = None
        self.segments: List[str] = []

    def set_progress(self, p: float):
        self.progress = max(0.0, min(1.0, p))

def run_transcription_job(job: TranscriptionJob):
    try:
        job.status = "running"

        size_mb = file_size_mb(job.audio_path)
        dur = ffprobe_duration_seconds(job.audio_path)

        # Decidir si segmentar
        if size_mb > MAX_FILE_MB or dur > (SEGMENT_SECONDS + 10):
            parts = segment_audio_ffmpeg_copy(job.audio_path, SEGMENT_SECONDS)
        else:
            parts = [job.audio_path]

        job.segments = [str(p) for p in parts]
        total = len(parts)
        texts: List[str] = []

        for idx, part in enumerate(parts, start=1):
            text = transcribe_file_deepinfra(part)
            texts.append(text)
            job.set_progress(idx / total)

        full_text = "\n".join(texts).strip()
        summarized = _process_transcription_text(full_text, job.nota)

        job.result = summarized
        job.status = "done"
        job.set_progress(1.0)
    except Exception as e:
        job.error = str(e)
        job.status = "error"
        job.set_progress(1.0)

def _jobs_state() -> Dict[str, TranscriptionJob]:
    if "tr_jobs" not in st.session_state:
        st.session_state["tr_jobs"] = {}
    return st.session_state["tr_jobs"]

def start_transcription_job(audio_path: Path, nota: str) -> str:
    jobs = _jobs_state()
    job = TranscriptionJob(audio_path, nota)
    jobs[job.id] = job
    t = threading.Thread(target=run_transcription_job, args=(job,), daemon=True)
    t.start()
    return job.id

def get_job(job_id: str) -> Optional[TranscriptionJob]:
    return _jobs_state().get(job_id)

# ==========================
# UI: Grabación + Transcripción (optimizada)
# ==========================
def audio_recorder_transcriber(nota: str) -> str:
    """
    Grabación y transcripción sin bloquear UI:
    - Guarda audio a disco (no bytes en session_state).
    - Muestra duración con ffprobe.
    - Transcribe en background por segmentos.
    Devuelve el texto de transcripción/resumen si está listo; de lo contrario ''.
    """
    st.subheader("🎙️ Grabación y Transcripción de Audio (optimizada)")

    file_key = f"audio_file_{nota}"
    job_key = f"tr_job_{nota}"

    if file_key not in st.session_state:
        st.session_state[file_key] = None
    if job_key not in st.session_state:
        st.session_state[job_key] = None

    col1, col2 = st.columns([3, 1])
    with col1:
        audio_value = mic_recorder(
            start_prompt="🎙️ Iniciar Grabación",
            stop_prompt="⏹️ Detener Grabación",
            just_once=True,
            use_container_width=True,
            format="webm",
            key=f"mic_{nota}"
        )
        if audio_value and audio_value.get("bytes"):
            audio_path = save_audio_bytes_to_file(audio_value["bytes"], ".webm")
            st.session_state[file_key] = str(audio_path)
            st.success(f"✅ Audio guardado: {audio_path.name}")

    with col2:
        if st.button("🗑️ Limpiar audio", use_container_width=True):
            st.session_state[file_key] = None
            st.session_state[job_key] = None
            st.success("Listo para grabar de nuevo")
            st.experimental_rerun()

    audio_path_str = st.session_state[file_key]
    if audio_path_str:
        audio_path = Path(audio_path_str)
        size = file_size_mb(audio_path)
        dur = ffprobe_duration_seconds(audio_path)

        info1, info2, info3 = st.columns(3)
        with info1:
            st.metric("Archivo", audio_path.name)
        with info2:
            st.metric("Tamaño", f"{size:.2f} MB")
        with info3:
            st.metric("Duración", f"{dur/60:.1f} min")

        # Nota: st.audio con lectura desde archivo; evita duplicar bytes en session_state
        with open(audio_path, "rb") as f:
            st.audio(f.read(), format="audio/webm")

        if size > MAX_FILE_MB or dur > (SEGMENT_SECONDS + 10):
            st.warning("⚠️ Audio largo. Se segmentará automáticamente para transcribir de forma robusta.")

        if st.button("🔮 Transcribir (background)", type="primary"):
            job_id = start_transcription_job(audio_path, nota)
            st.session_state[job_key] = job_id
            st.info("Transcripción iniciada. Puedes seguir navegando.")
            st.experimental_rerun()

    # Mostrar estado del job si existe
    job_id = st.session_state[job_key]
    if job_id:
        job = get_job(job_id)
        if job:
            if job.status in ("queued", "running"):
                st.info(f"⏳ Procesando... {int(job.progress*100)}%")
                st.progress(job.progress)
                if job.segments:
                    st.caption(f"Segmentos: {len(job.segments)}")
                # Pequeño auto-refresh
                time.sleep(0.8)
                st.experimental_rerun()
            elif job.status == "done":
                st.success("✅ Transcripción completada")
                st.text_area("Transcripción/Resumen", job.result, height=400, key=f"tr_out_{nota}")
                return job.result
            else:
                st.error(f"❌ Error: {job.error}")
                return ""

    # Debug opcional
    if st.checkbox("🔧 Modo Debug"):
        st.write("Estado:")
        st.write(f"Archivo: {bool(st.session_state[file_key])}")
        st.write(f"Job: {st.session_state[job_key]}")
    return ""

# ==========================
# Componente opcional: Grabación y subida en chunks al backend (FastAPI)
# (Úsalo si implementas el microservicio de subida en trozos)
# ==========================
def chunked_recorder_component(server_url: str, session_key: str):
    """
    Inserta un widget que graba y sube chunks de 10s al servidor FastAPI.
    Guarda sessionId en session_state[session_key].
    """
    if session_key not in st.session_state:
        st.session_state[session_key] = uuid.uuid4().hex

    sess_id = st.session_state[session_key]

    component_html = f"""
<div style="padding: 12px; border: 1px solid #444; border-radius: 8px;">
  <button id="startBtn">🎙️ Iniciar</button>
  <button id="stopBtn" disabled>⏹️ Detener</button>
  <span id="status">Idle</span>
  <div id="debug" style="font-size: 12px; opacity: 0.8; margin-top: 8px;"></div>
</div>
<script>
const serverUrl = "{server_url}";
const sessionId = "{sess_id}";
let mediaRecorder = null;
let wakeLock = null;
let chunkIndex = 0;

async function postForm(url, formData) {{
  const res = await fetch(url, {{
    method: 'POST',
    body: formData
  }});
  return res.json();
}}

async function beginUpload() {{
  try {{
    await postForm(serverUrl + "/begin-upload", new FormData());
  }} catch(e) {{}}
}}

async function requestWakeLock(){{
  try {{
    if ('wakeLock' in navigator) {{
      wakeLock = await navigator.wakeLock.request('screen');
    }}
  }} catch(e){{}}
}}

document.getElementById("startBtn").onclick = async () => {{
  const status = document.getElementById("status");
  status.textContent = "Preparando...";
  await beginUpload();
  await requestWakeLock();

  const stream = await navigator.mediaDevices.getUserMedia({{ audio: true }});
  mediaRecorder = new MediaRecorder(stream, {{
    mimeType: "audio/webm;codecs=opus",
    audioBitsPerSecond: 32000
  }});
  chunkIndex = 0;
  document.getElementById("startBtn").disabled = true;
  document.getElementById("stopBtn").disabled = false;
  status.textContent = "Grabando...";

  mediaRecorder.ondataavailable = async (e) => {{
    if (e.data && e.data.size > 0) {{
      const fd = new FormData();
      fd.append("sessionId", sessionId);
      fd.append("chunkIndex", chunkIndex);
      fd.append("isLast", "false");
      fd.append("file", e.data, `chunk_${{chunkIndex}}.webm`);
      try {{
        await postForm(serverUrl + "/upload-chunk", fd);
      }} catch (err) {{
        document.getElementById("debug").textContent = "Upload error: " + err;
      }}
      chunkIndex += 1;
    }}
  }};
  mediaRecorder.start(10000); // 10s por chunk
}};

document.getElementById("stopBtn").onclick = async () => {{
  const status = document.getElementById("status");
  status.textContent = "Finalizando...";
  document.getElementById("stopBtn").disabled = true;
  if (mediaRecorder && mediaRecorder.state !== "inactive") {{
    mediaRecorder.onstop = async () => {{
      const fd = new FormData();
      fd.append("sessionId", sessionId);
      const resp = await postForm(serverUrl + "/finalize", fd);
      status.textContent = resp.ok ? "Listo ✅" : "Error al finalizar";
    }};
    mediaRecorder.stop();
  }}
  if (wakeLock) {{
    try {{ await wakeLock.release(); }} catch(e){{}}
  }}
}};
</script>

    st_html(component_html, height=180)

# ==========================
# Otras utilidades usadas por Inicio.py
# ==========================
def rand_ta() -> str:
    """Genera una TA aleatoria."""
    ta = f'{random.randint(100,130)}/{random.randint(66,78)}'
    return ta

@st.cache_data(show_spinner=False)
def stored_data(name: str):
    data = {
        'escalas': [
            'RASS.pdf','bush y francis.pdf', 'simpson angus.pdf', 'gad7.pdf', 'sad persons.pdf',
            'young.pdf', 'fab.pdf', 'assist.pdf', 'dimensional.pdf', 'psp.pdf', 'yesavage.pdf',
            'phq9.pdf', 'Escala dimensional de psicosis.pdf', 'moca.pdf', 'moriski-8.pdf',
            'mdq.pdf', 'calgary.pdf', 'eeag.pdf', 'madrs.pdf'
        ],
        'gpc': [
            'SSA-222-09 Diagnostico y tratamiento de la esquizofrenia',
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
            'IMSS-465-11 Prevención, diagnóstico y tratamiento del DELIRIUM en el adulto mayor hospitalizado'
        ]
    }
    return data[name]

def calculate_age(born: datetime) -> int:
    today = datetime.now()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))

def clin_merge(scale: str) -> str:
    return f' {scale}, ' if scale != '' else ''

def radio_check(var: str) -> str:
    return 'Yes' if var != '' else ''

def update_dict(dic: Dict, var: str):
    dic.update({var: 'Yes',})

def id_gen() -> int:
    now = datetime.now()
    date_id = now.strftime('%d%m%y%H%M%S')
    return int(date_id)

def ensure_index(action: str, collection, index_name: str, index_key: List[tuple]):
    """
    Crea o elimina un índice en MongoDB.
    action: 'create' o 'delete'
    index_key: lista de tuplas [(campo, orden), ...]
    """
    if action == 'create':
        existing = [idx['name'] for idx in collection.list_indexes()]
        if index_name not in existing:
            collection.create_index(index_key, name=index_name)
            print(f"Created index '{index_name}' on collection '{collection.name}'")
        else:
            print(f"Index '{index_name}' already exists on collection '{collection.name}'")
    else:
        try:
            collection.drop_index(index_name)
            print(f"Index '{index_name}' has been deleted")
        except Exception as e:
            print(f"Unable to delete index '{index_name}': {e}")

def search_collection(collection, criteria: Dict, all_info: bool = True):
    results = []
    if all_info:
        for document in collection.find(criteria):
            results.append(document)
        return results
    else:
        for document in collection.find(criteria, {'_id': 0, 'nombres': 1, 'primer apellido': 1, 'segundo apellido': 1, 'generales.nacimiento.fecha': 1}):
            results.append(document)
        return results

def unidecode_except(string: str) -> str:
    exceptions = ['ñ','1','2','3','4','5','6','7','8','9','0']
    replaced_string = ''
    for c in string:
        if c in exceptions:
            replaced_string += c
        else:
            replaced_string += unidecode(c)
    return replaced_string

def data_format(field: List[str], val: List[str]) -> Dict:
    for i in range(len(val)):
        val[i] = unidecode_except(val[i])
    temp_ar = {}
    for i in range(len(field)):
        temp_ar[field[i]] = {"$regex": val[i], "$options": "i"}
    return temp_ar

def doc_field(database_name, collection_name: str, filter: Dict, projection: List[str]):
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

def buscar_clientes(nombre: str, apellido_paterno: str, apellido_materno: str):
    # Conexión rápida ad-hoc (mejor usa mongo_intial y reusa cliente)
    client = MongoClient(MONGODB_URI) if MONGODB_URI else None
    if not client:
        return []
    db = client['expedinente_electronico']
    collection = db['pacientes']
    resultados = collection.find({
        'nombre': nombre,
        'apellido_paterno': apellido_paterno,
        'apellido_materno': apellido_materno
    }, {
        '_id': 0,
        'generales.fecha_nacimiento': 1
    })
    out = [r for r in resultados]
    client.close()
    return out

def check_ef(var: str) -> str:
    return var if var != "" else 'sin alteraciones'

def note_show(consultas_previas: int, paciente: List[Dict], nota: str):
    renglon = '\n'
    evol = st.expander('CONSULTAS PREVIAS', expanded=True)
    with evol:
        fechas_citas = []
        for i in range(consultas_previas):
            fechas_citas.insert(0, paciente[0]['consultas'][i]['fecha'])
        fecha_nota_prev = st.selectbox('Seleccione fecha de citas previas:', fechas_citas)
        for consulta in paciente[0]["consultas"]:
            if consulta["fecha"] == fecha_nota_prev:
                if consulta['fecha'] == fechas_citas[-1]:
                    st.subheader('Consulta de primera vez')
                    st.text_area('', nota, height=300)
                else:
                    prev_cons = consulta
                    consulta_anterior = ('##### ' + prev_cons['fecha'] + renglon + renglon +
                        '> ' + prev_cons['presentacion'].replace('\n', ' ') + renglon + '- ' +
                        prev_cons['subjetivo'] + renglon + renglon +
                        '- SOMATOMETRÍA Y SIGNOS VITALES:' + renglon +
                        'FC: ' + prev_cons['fc'] + ' lpm' + ' | ' +  'FR: ' + prev_cons['fr'] + ' rpm' + ' | ' + 'TA: ' + prev_cons['ta'] + ' mmHg' + ' | ' + ' ------- ' + 'PESO: ' +  str(prev_cons['peso']) + ' ' + 'kg' + '  ' + 'TALLA: ' + str(prev_cons['talla']) + ' ' + 'cm' + renglon + renglon + '- ' +
                        prev_cons['objetivo'] + renglon + renglon +
                        'PHQ-9: '+ prev_cons['clinimetrias']['phq9'] + ' ' + ' |   ' +
                        'GAD-7: '+ prev_cons['clinimetrias']['gad7'] + ' ' + ' |   ' +
                        'SADPERSONS: '+ prev_cons['clinimetrias']['sadpersons'] + ' ' + ' |   ' +
                        'YOUNG: '+ prev_cons['clinimetrias']['young'] + ' ' + ' |   ' +
                        'MDQ: '+ prev_cons['clinimetrias']['mdq'] + ' ' + ' |   ' +
                        'ASRS: '+ prev_cons['clinimetrias']['asrs'] + ' ' + ' |   ' +
                        'OTRAS: '+ prev_cons['clinimetrias']['otras_clini'] + ' ' + ' |   ' + renglon + renglon +
                        '##### ' + 'ANÁLISIS: ' + renglon + prev_cons['analisis'] + renglon + renglon +
                        '##### ' + 'PLAN: ' + renglon + prev_cons['plan'] + renglon + '--- ')
                    st.markdown(consulta_anterior)
    return fechas_citas[-1] if consultas_previas > 0 else None

def last_note(consultas_previas: int, paciente: List[Dict], nota: str):
    fechas_citas = []
    for i in range(consultas_previas):
        fechas_citas.append(paciente[0]['consultas'][i]['fecha'])
    return (fechas_citas[-1], len(fechas_citas)) if fechas_citas else ("", 0)

def mongo_intial(mongodb_uri: Optional[str]):
    uri = mongodb_uri or MONGODB_URI
    client = MongoClient(uri)
    db = client['expedinente_electronico']  # base de datos
    pacientes = db['pacientes']             # colección
    # Índice por nombres y apellidos
    ensure_index('create', pacientes, 'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo apellido', 1)])
    return client, pacientes

def mongo_connect(mongodb_uri: Optional[str]):
    uri = mongodb_uri or MONGODB_URI
    client = MongoClient(uri)
    db = client['expedinente_electronico']
    pacientes = db['pacientes']
    ensure_index('create', pacientes, 'nombre_apellidos', [('nombres', 1), ('primer apellido', -1), ('segundo apellido', 1)])
    return client

def gdrive_up(local_file: str, final_name: str) -> str:
    gauth = GoogleAuth()
    scope = [
        'https://www.googleapis.com/auth/drive',
        'https://www.googleapis.com/auth/drive.file',
        'https://www.googleapis.com/auth/drive.appdata'
    ]
    gauth.service_account_json = 'service_account.json'
    drive = GoogleDrive(gauth)
    gfile = drive.CreateFile({'parents': [{'id': '1ESHu5ZblpwcCI5PrHP-80YrQ-NPiH7nm'}], 'title': final_name})
    gfile.SetContentFile(local_file)
    gfile.Upload()
    file_url = 'https://drive.google.com/file/d/' + gfile['id'] + '/view'
    return file_url

# ==========================
# Resumen paciente y chat con expediente (Gemini)
# ==========================
HTML_EX = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Evolución de Escalas Clinimétricas y Peso</title>
    <style>
        body { background-color: transparent; margin: 0; padding: 40px; font-family: 'Segoe UI', Arial, sans-serif; color: #fff; }
        .frame { background: linear-gradient(145deg, rgba(44,44,44,0.9), rgba(37,37,37,0.9)); border-radius: 20px; box-shadow: 0 10px 40px rgba(0,0,0,0.6); padding: 30px; display: flex; justify-content: space-between; align-items: flex-start; max-width: 2100px; margin: 0 auto; flex-wrap: nowrap; overflow-x: auto; }
        .chart-container { width: 400px; height: 300px; background: transparent; position: relative; border-radius: 12px; padding: 15px; transition: all 0.3s ease; flex-shrink: 0; }
        .chart-container:hover { transform: scale(1.02); box-shadow: 0 5px 20px rgba(0,0,0,0.3); }
        canvas { background: transparent !important; border-radius: 10px; }
        ::-webkit-scrollbar { height: 8px; }
        ::-webkit-scrollbar-track { background: rgba(51,51,51,0.5); border-radius: 4px; }
        ::-webkit-scrollbar-thumb { background: rgba(85,85,85,0.7); border-radius: 4px; }
        ::-webkit-scrollbar-thumb:hover { background: rgba(119,119,119,0.9); }
    </style>
</head>
<body>
    <div class="frame">
        <div class="chart-container"><canvas id="phq9Chart"></canvas></div>
        <div class="chart-container"><canvas id="gad7Chart"></canvas></div>
        <div class="chart-container"><canvas id="gafChart"></canvas></div>
        <div class="chart-container"><canvas id="mdqChart"></canvas></div>
        <div class="chart-container"><canvas id="weightChart"></canvas></div>
    </div>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        const chartConfig = {{
            type: 'line',
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                scales: {{
                    x: {{
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)', borderColor: 'rgba(255, 255, 255, 0.2)' }},
                        ticks: {{ color: '#e0e0e0', font: {{ size: 12, weight: '500' }} }}
                    }},
                    y: {{
                        grid: {{ color: 'rgba(255, 255, 255, 0.05)', borderColor: 'rgba(255, 255, 255, 0.2)' }},
                        ticks: {{ color: '#e0e0e0', font: {{ size: 12, weight: '500' }} }}
                    }}
                }},
                plugins: {{
                    legend: {{
                        labels: {{ color: '#ffffff', font: {{ size: 16, weight: '600' }}, padding: 20, boxWidth: 20, usePointStyle: true }}
                    }},
                    tooltip: {{
                        backgroundColor: 'rgba(30, 30, 30, 0.9)',
                        titleFont: {{ size: 14, weight: '600' }},
                        bodyFont: {{ size: 12 }},
                        cornerRadius: 10,
                        padding: 12,
                        borderColor: 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1
                    }}
                }},
                elements: {{
                    line: {{ tension: 0.5, borderWidth: 3, fill: false, spanGaps: true }},
                    point: {{ radius: 6, hoverRadius: 9, backgroundColor: '#fff', borderWidth: 2 }}
                }},
                animation: {{ duration: 1800, easing: 'easeOutExpo' }}
            }}
        }};
        const data = {{
            labels: ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun'],
            phq9: [10, null, 8, null, 6, 5],
            gad7: [8, 9, null, 6, null, 4],
            gaf: [60, null, 65, 70, null, 75],
            mdq: [null, 5, 3, null, 3, 2],
            weight: [70, 71, null, 70, null, 69]
        }};
        new Chart(document.getElementById('phq9Chart'), {{
            ...chartConfig,
            data: {{ labels: data.labels, datasets: [{{ label: 'PHQ-9', data: data.phq9, borderColor: '#ff6b6b', pointBackgroundColor: '#ff6b6b', pointBorderColor: '#fff', backgroundColor: 'transparent' }}] }}
        }});
        new Chart(document.getElementById('gad7Chart'), {{
            ...chartConfig,
            data: {{ labels: data.labels, datasets: [{{ label: 'GAD-7', data: data.gad7, borderColor: '#4ecdc4', pointBackgroundColor: '#4ecdc4', pointBorderColor: '#fff', backgroundColor: 'transparent' }}] }}
        }});
        new Chart(document.getElementById('gafChart'), {{
            ...chartConfig,
            data: {{ labels: data.labels, datasets: [{{ label: 'GAF', data: data.gaf, borderColor: '#45b7d1', pointBackgroundColor: '#45b7d1', pointBorderColor: '#fff', backgroundColor: 'transparent' }}] }}
        }});
        new Chart(document.getElementById('mdqChart'), {{
            ...chartConfig,
            data: {{ labels: data.labels, datasets: [{{ label: 'MDQ', data: data.mdq, borderColor: '#96c93d', pointBackgroundColor: '#96c93d', pointBorderColor: '#fff', backgroundColor: 'transparent' }}] }}
        }});
        new Chart(document.getElementById('weightChart'), {{
            ...chartConfig,
            data: {{ labels: data.labels, datasets: [{{ label: 'Peso (kg)', data: data.weight, borderColor: '#ffa502', pointBackgroundColor: '#ffa502', pointBorderColor: '#fff', backgroundColor: 'transparent' }}] }}
        }});
    </script>
</body>
</html>
"""

def resumen_paciente(datos: str):
    """
    Genera resumen usando Gemini y extrae, si existe, un bloque HTML de gráficas del texto.
    Devuelve (resumen_markdown, html_code).
    """
    model = genai.GenerativeModel('gemini-2.5-flash') if GEMINI_API else None
    if not model:
        return datos, ""  # Fallback

    prompt = f"""
INSTRUCCIONES: Actúa como un especialista médico y elabora un resumen conciso del expediente clínico proporcionado,
seguido del código HTML para visualizar gráficamente la evolución de las escalas clinimétricas registradas.

RESUMEN DE EXPEDIENTE CLÍNICO
- Presenta la información en una tabla con las columnas: Fecha, Evolución y síntomas, Hallazgos clínicos, Análisis médico y Tratamiento.
- Utiliza terminología médica apropiada manteniendo un tono profesional.
- Enfatiza y detalla más extensamente la última consulta, mientras que las anteriores deberán ser más breves y concisas.
- Usa markdown para títulos/subtítulos.

EXPEDIENTE CLÍNICO:
{datos}

GRÁFICAS DE CLINIMETRÍAS
Si el expediente contiene valores de escalas (GAF, PHQ-9, GAD-7, MDQ, etc.), genera código HTML para visualizar la evolución.
Solo incluye gráficos con más de 2 valores. La escala debe ir de 0 al máximo. Une puntos existentes (sin 0 en faltantes).
Usa esta plantilla como base:
{HTML_EX}
"""
    response = model.generate_content(prompt)
    text = getattr(response, "text", "") or ""

    # Extraer bloque HTML si viene entre fences
    html_code = ""
    code_match = re.search(r'```html(.*?)```', text, re.DOTALL | re.IGNORECASE)
    if code_match:
        html_code = code_match.group(1).strip()
        resumen = re.sub(r'```html(.*?)```', '', text, flags=re.DOTALL | re.IGNORECASE).strip()
    else:
        resumen = text

    # Limpia fences markdown residuales
    resumen = re.sub(r'```markdown(.*?)```', r'\1', resumen, flags=re.DOTALL | re.IGNORECASE).strip()
    return resumen, html_code

def chat_expediente(pregunta: str, expediente: str) -> str:
    model = genai.GenerativeModel('gemini-2.5-flash') if GEMINI_API else None
    if not model:
        return ""
    prompt = f"""
INSTRUCCIONES: Responde la pregunta sobre el expediente clínico proporcionado en forma breve, precisa y profesional.

PREGUNTA:
{pregunta}

EXPEDIENTE CLÍNICO:
{expediente}
"""
    response = model.generate_content(prompt)
    return getattr(response, "text", "") or ""
