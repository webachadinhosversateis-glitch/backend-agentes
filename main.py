from fastapi import FastAPI, Request

app = FastAPI()

# ===== AGENTES =====

def interpreter_agent(prompt):
    return {
        "tipo": "funcional",
        "dimensoes": "automático",
        "descricao": prompt
    }

def engineering_agent(data):
    data["validado"] = True
    return data

def cad_agent(data):
    scad = f"""
    cube([80,60,100]);
    """
    return {"scad_code": scad}

def validator_agent(model):
    return {"valid": True, "errors": []}

# ===== ORQUESTRADOR =====

def run_pipeline(prompt):
    step1 = interpreter_agent(prompt)
    step2 = engineering_agent(step1)
    step3 = cad_agent(step2)
    step4 = validator_agent(step3)

    return {
        "input": prompt,
        "modelo": step3,
        "validacao": step4
    }

# ===== ROTAS =====

@app.get("/")
def home():
    return {"status": "online"}

@app.get("/agente")
def agente():
    return {"msg": "agente funcionando"}

@app.post("/gerar")
async def gerar(req: Request):
    body = await req.json()
    prompt = body.get("prompt")

    result = run_pipeline(prompt)

    return result
