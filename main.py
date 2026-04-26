from fastapi import FastAPI, Request
from fastapi.responses import Response
import os
import subprocess
import uuid

app = FastAPI()


# ===== AGENTE 1 =====
def interpreter_agent(prompt):
    return {
        "tipo": "funcional",
        "descricao": prompt,
        "dimensoes": "automatico"
    }


# ===== AGENTE 2 =====
def engineering_agent(dados):
    dados["validado"] = True
    return dados


# ===== AGENTE 3 (OPENSCAD -> STL) =====
descricao = dados.get("descricao", "").lower()

if "inclinado" in descricao:
    scad_code = "rotate([60,0,0]) cube([80,60,100]);"

elif "largo" in descricao:
    scad_code = "cube([120,80,100]);"

elif "fino" in descricao:
    scad_code = "cube([40,40,100]);"

else:
    scad_code = "cube([80,60,100]);"

    with open(scad_file, "w") as f:
        f.write(scad_code)

    subprocess.run(
        ["openscad", "-o", stl_file, scad_file],
        check=True
    )

    with open(stl_file, "rb") as f:
        stl_bytes = f.read()

    return stl_bytes


# ===== AGENTE 4 =====
def validator_agent(modelo):
    return {
        "valido": True,
        "erros": []
    }


# ===== PIPELINE =====
def run_pipeline(prompt):
    passo1 = interpreter_agent(prompt)
    passo2 = engineering_agent(passo1)
    passo3 = cad_agent(passo2)
    passo4 = validator_agent(passo3)

    return passo3  # aqui retorna o STL direto


# ===== ROTAS =====
@app.get("/")
def home():
    return {"status": "online"}


@app.get("/agente")
def agente():
    return {"msg": "funcionando"}


# 🚀 ROTA PRINCIPAL DE DOWNLOAD
@app.post("/gerar")
async def gerar(req: Request):
    corpo = await req.json()
    prompt = corpo.get("prompt", "modelo simples")

    stl = run_pipeline(prompt)

    return Response(
        content=stl,
        media_type="application/sla",
        headers={
            "Content-Disposition": "attachment; filename=modelo.stl"
        }
    )


# ===== START =====
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
