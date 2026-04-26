FROM python:3.10

RUN apt-get update && apt-get install -y openscad

WORKDIR /app

COPY . .

RUN pip install --upgrade pip
RUN pip install fastapi uvicorn openai

CMD ["python", "main.py"]
