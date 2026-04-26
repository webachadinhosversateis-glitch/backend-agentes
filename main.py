from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os
import re

# ===============================
# OPENAI (OPCIONAL)
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    except:
        client = None

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
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    return text.strip()

def gerar_nome(prompt):
    base = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")
    return (base[:40] or "modelo") + ".stl"

# ===============================
# VALIDAÇÃO FORTE
# ===============================
def validate_scad(scad):

    if not scad or len(scad) < 20:
        return False

    valid_keywords = ["cube", "sphere", "cylinder", "union", "difference", "hull"]

    if not any(k in scad for k in valid_keywords):
        return False

    if scad.count("(") != scad.count(")"):
        return False

    if scad.count("{") != scad.count("}"):
        return False

    return True

# ===============================
# FALLBACK (SEMPRE FUNCIONA)
# ===============================
def fallback_scad(prompt):
    return """
    union() {
        cube([80,60,5]);
        translate([0,40,0])
            rotate([65,0,0])
            cube([80,5,100]);
        translate([20,0,5])
            cube([40,10,10]);
    }
    """

# ===============================
# AUTO CORREÇÃO DE SCAD
# ===============================
def repair_scad(scad):
    scad = scad.strip()

    # fecha parênteses
    while scad.count("(") > scad.count(")"):
        scad += ")"

    while scad.count("{") > scad.count("}"):
        scad += "}"

    return scad

# ===============================
# CAD AGENT (IA)
# ===============================
def cad_agent(prompt):

    if not client:
        return fallback_scad(prompt)

    try:
        system = """
Você é um engenheiro especialista em OpenSCAD.

REGRAS OBRIGATÓRIAS:

- Retorne SOMENTE código OpenSCAD válido
- Código deve rodar sem erro no OpenSCAD
- Use apenas:
  cube(), sphere(), cylinder(), union(), difference(), hull()

- Sempre feche:
  ()
  {}

- NÃO explique nada
- NÃO use markdown

- Sempre gerar modelo imprimível:
  - base estável
  - espessura mínima 3mm

Se houver dúvida, gere algo simples e funcional
"""

        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3
        )

        scad = clean_scad(resp.choices[0].message.content)

        # tentativa de correção automática
        scad = repair_scad(scad)

        return scad

    except:
        return fallback_scad(prompt)

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
# PIPELINE COMPLETO
# ===============================
def pipeline(prompt):

    scad = cad_agent(prompt)

    if not validate_scad(scad):
        scad = repair_scad(scad)

    if not validate_scad(scad):
        scad = fallback_scad(prompt)

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
