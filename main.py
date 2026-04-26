from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os
import re
import json

# ===============================
# OPENAI (SEM QUEBRAR)
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    from openai import OpenAI
    client = OpenAI(api_key=OPENAI_API_KEY)

# ===============================
# APP
# ===============================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# UTIL
# ===============================
def clean_scad(text):
    return re.sub(r"```.*?", "", text).strip()

def gerar_nome(prompt):
    base = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")
    return (base[:40] or "modelo") + ".stl"

# ===============================
# ORIGINALIZADOR (ANTI CÓPIA)
# ===============================
def originalizer(prompt):
    swaps = {
        "naruto": "ninja anime",
        "goku": "guerreiro anime cabelo espetado"
    }
    for k, v in swaps.items():
        prompt = prompt.lower().replace(k, v)
    return prompt

# ===============================
# LIBRARY (INTELIGÊNCIA BASE)
# ===============================
def search_library(prompt):
    try:
        with open("library.json") as f:
            data = json.load(f)

        for item in data:
            for tag in item["tags"]:
                if tag in prompt.lower():
                    return item

        return None
    except:
        return None

# ===============================
# FALLBACK (NUNCA QUEBRA)
# ===============================
def fallback_scad(prompt):

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
# CAD AGENT (IA)
# ===============================
def cad_agent(prompt):

    if not client:
        return fallback_scad(prompt)

    try:
        system = """
Você é um modelador 3D profissional.

Regras:
- Retorne SOMENTE código OpenSCAD
- Use union(), difference(), hull()
- Gere formas bonitas e funcionais
- Evite formas simples como cubo puro
- Use proporções reais
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
# VALIDAÇÃO
# ===============================
def validate_scad(scad):
    if not scad or len(scad) < 10:
        raise Exception("SCAD inválido")

# ===============================
# GERAR STL
# ===============================
def generate_stl(scad):

    name = str(uuid.uuid4())

    scad_file = f"/tmp/{name}.scad"
    stl_file = f"/tmp/{name}.stl"

    with open(scad_file, "w") as f:
        f.write(scad)

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
def pipeline(prompt):

    prompt = originalizer(prompt)

    ref = search_library(prompt)

    if ref:
        prompt = f"{prompt} baseado em {ref['nome']}"

    scad = cad_agent(prompt)

    validate_scad(scad)

    return generate_stl(scad)

# ===============================
# ROTAS
# ===============================
@app.get("/")
def home():
    return {"status": "online", "modo": "pro"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")

        stl = pipeline(prompt)

        nome = gerar_nome(prompt)

        return Response(
            content=stl,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": f"attachment; filename={nome}"
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
