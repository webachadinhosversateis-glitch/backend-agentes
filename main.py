from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
import os
import subprocess
import uuid

app = FastAPI()


# ===== AGENTE 1: INTERPRETAÇÃO =====
def interpreter_agent(prompt):
    return {
        "tipo": "funcional",
        "descricao": prompt,
        "dimensoes": "automatico"
    }


# ===== AGENTE 2: ENGENHARIA =====
def engineering_agent(dados):
    dados["validado"] = True
    return dados


# ===== AGENTE 3: CAD / OPENSCAD =====
def cad_agent(dados):
    scad_code = """
    cube([80, 60, 100]);
    """

    nome = str(uuid.uuid4())
    scad_file = f"/tmp/{nome}.scad"
    stl_file = f"/tmp/{nome}.stl"

    with open(scad_file, "w") as arquivo:
        arquivo.write(scad_code)

    subprocess.run(
        ["openscad", "-o", stl_file, scad_file],
        check=True
    )

    return {
        "scad_code": scad_code,
        "arquivo_stl": stl_file
    }


# ===== AGENTE 4: VALIDADOR =====
def validator_agent(modelo):
    return {
        "valido": True,
        "erros": []
    }


# ===== ORQUESTRADOR =====
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


# ===== ROTAS =====
@app.get("/")
def home():
    return {"status": "online", "mensagem": "backend rodando"}


@app.get("/agente")
def agente():
    return {"msg": "agente funcionando"}


@app.post("/gerar")
async def gerar(req: Request):
    corpo = await req.json()
    prompt = corpo.get("prompt", "modelo simples")

    resultado = run_pipeline(prompt)
    arquivo_stl = resultado["modelo"]["arquivo_stl"]

    return FileResponse(
        arquivo_stl,
        media_type="application/octet-stream",
        filename="modelo_gerado.stl"
    )


# ===== START LOCAL / RAILWAY =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
