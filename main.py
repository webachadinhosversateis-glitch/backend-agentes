from fastapi import FastAPI
import os

app = FastAPI()

@app.get("/")
def home():
    return {"status": "online", "mensagem": "backend rodando"}

@app.get("/agente")
def agente():
    return {"resposta": "agente funcionando"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
