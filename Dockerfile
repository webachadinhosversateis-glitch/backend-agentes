FROM python:3.10-slim

WORKDIR /app

COPY . .

RUN apt-get update && apt-get install -y \
    openscad \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn openai

CMD ["python", "main.py"]
