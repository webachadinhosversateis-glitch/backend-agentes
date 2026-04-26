from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os
import re
import json

# ===============================
# CONFIG OPENAI (AGORA NÃO QUEBRA)
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# HELPERS
# ===============================
def clean_scad(text: str) -> str:
    text = re.sub(r"```.*?", "", text)
    return text.strip()

def filename_from_prompt(prompt: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:40]
    return f"{base or 'modelo'}.stl"

# ===============================
# ORIGINALIZADOR (ANTI CÓPIA)
# ===============================
def originalizer(prompt: str) -> str:
    swaps = {
        "naruto": "ninja estilo anime",
        "goku": "guerreiro de cabelo espetado"
    }
    for k, v in swaps.items():
        prompt = prompt.lower().replace(k, v)
    return prompt

# ===============================
# CLASSIFICADOR
# ===============================
def classify(prompt: str):
    if "suporte" in prompt:
        return "suporte"
    if "miniatura" in prompt or "anime" in prompt:
        return "miniatura"
    return "geral"

# ===============================
# IA (CAD INTELIGENTE)
# ===============================
def cad_agent(prompt: str):

    if not client:
        return fallback_scad(prompt)

    try:
        system = """
Você é um modelador 3D profissional.

Regras:
- Retorne apenas código OpenSCAD
- Use union, hull, difference
- Modelo deve ser bonito e funcional
- Nunca retornar cubo simples
- Sempre criar forma reconhecível
"""

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )

        return clean_scad(resp.choices[0].message.content)

    except:
        return fallback_scad(prompt)

# ===============================
# FALLBACK (NUNCA QUEBRA)
# ===============================
def fallback_scad(prompt: str):

    if "borboleta" in prompt:
        return """
        union() {
            hull() {
                translate([-20,0,0]) sphere(10);
                translate([-40,20,0]) sphere(5);
                translate([-40,-20,0]) sphere(5);
            }
            hull() {
                translate([20,0,0]) sphere(10);
                translate([40,20,0]) sphere(5);
                translate([40,-20,0]) sphere(5);
            }
            cylinder(h=40, r=2, center=true);
        }
        """

    if "suporte" in prompt:
        return """
        union() {
            cube([80,60,5]);
            translate([0,40,0])
                rotate([65,0,0])
                cube([80,5,100]);
        }
        """

    return "sphere(30);"

# ===============================
# VALIDAÇÃO
# ===============================
def validate_scad(scad: str):
    if len(scad) < 10:
        raise Exception("SCAD inválido")

# ===============================
# GERAR STL
# ===============================
def generate_stl(scad_code: str):

    name = str(uuid.uuid4())

    scad_file = f"/tmp/{name}.scad"
    stl_file = f"/tmp/{name}.stl"

    with open(scad_file, "w") as f:
        f.write(scad_code)

    result = subprocess.run(
        ["openscad", "-o", stl_file, scad_file],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise Exception(result.stderr)

    with open(stl_file, "rb") as f:
        return f.read()

# ===============================
# PIPELINE
# ===============================
def pipeline(prompt: str):

    prompt = originalizer(prompt)

    scad = cad_agent(prompt)

    validate_scad(scad)

    return generate_stl(scad)

# ===============================
# ROTAS
# ===============================
@app.get("/")
def home():
    return {"status": "online", "mode": "pro"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")

        stl = pipeline(prompt)

        filename = filename_from_prompt(prompt)

        return Response(
            content=stl,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"erro": str(e)}
        )

# ===============================
# START
# ===============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
