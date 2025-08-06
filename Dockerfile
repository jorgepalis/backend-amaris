# Usa una imagen oficial de Python
FROM python:3.12-slim-bullseye

# Establece variables de entorno
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Crea el directorio del proyecto
WORKDIR /app

# Instala dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copia los archivos del proyecto
COPY . /app/


# Instala las dependencias de Python y ejecuta el script de diagnóstico
RUN pip install --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python funds/setup_simple.py

# Recolecta archivos estáticos
RUN python manage.py collectstatic --noinput

# Aplica migraciones
RUN python manage.py migrate --noinput

# Expone el puerto 8000
EXPOSE 8000

# Comando por defecto
CMD ["gunicorn", "core.wsgi:application", "--bind", "0.0.0.0:8000"]
