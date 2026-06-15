FROM python:3.10-slim

WORKDIR /app

# Установка системных зависимостей для OpenCV
RUN apt-get update && apt-get install -y \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Копирование зависимостей
COPY requirements.txt .

# Установка Python-пакетов
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

# Создание папок для данных
RUN mkdir -p /app/input /app/output

# Открываем порт
EXPOSE 8002

# Запуск
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8002"]