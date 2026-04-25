from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def home():
    return {"status": "online", "mensagem": "backend rodando"}

@app.get("/agente")
def agente():
  return {"resposta": "agente funcionando"}
