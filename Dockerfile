# Usa una imagen base de Python ligera
FROM python:3.10-slim

# Evita prompts interactivos y reduce tamaño
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crea directorio de trabajo
WORKDIR /app

# Copia e instala dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de los archivos
COPY . .

# Expone el puerto que Streamlit usará (importante para EasyPanel)
EXPOSE 8501

# Comando para ejecutar tu app Streamlit
CMD ["streamlit", "run", "Inicio.py", "--server.port=8501", "--server.enableCORS=false", "--server.enableXsrfProtection=false", "--server.baseUrlPath="]
