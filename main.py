from fastapi import FastAPI, Request
import os

app = FastAPI()

def interpreter_agent(prompt):
    return {
        "tipo": "funcional",
        "descricao": prompt,
        "dimensoes": "automatico"
    }

def engineering_agent(dados):
    dados["validado"] = True
    return dados

def cad_agent(dados):
    scad = """
    cube([80,60,100]);
    """
    return {"scad_code": scad}

def validator_agent(modelo):
    return {"valido": True, "erros": []}

def run_pipeline(prompt):
    passo1 = interpreter_agent(prompt)
    passo2 = engineering_agent(passo1)
    passo3 = cad_agent(passo2)
    passo4 = validator_agent(passo3)

    return {
        "entrada": prompt,
        "modelo": passo3,
        "validacao": passo4
    }

@app.get("/")
def home():
    return {"status": "online"}

@app.get("/agente")
def agente():
    return {"msg": "agente funcionando"}

@app.post("/gerar")
async def gerar(req: Request):
    corpo = await req.json()
    prompt = corpo.get("prompt")
    return run_pipeline(prompt)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
