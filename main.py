from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os
import re
import json

# ===============================
# OPENAI (obrigatório para nível pro)
# ===============================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise Exception("Defina OPENAI_API_KEY no ambiente")

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
    text = re.sub(r"```openscad", "", text, flags=re.I)
    text = re.sub(r"```scad", "", text, flags=re.I)
    text = re.sub(r"```", "", text)
    return text.strip()

def filename_from_prompt(prompt: str) -> str:
    base = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:50]
    return f"{base or 'modelo'}.stl"

def ask_ai(system: str, user: str, json_mode=False) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"} if json_mode else None,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user}
        ],
        temperature=0.2
    )
    return resp.choices[0].message.content

# ===============================
# ORIGINALIZADOR (evita cópia direta)
# ===============================
def originalizer(prompt: str) -> str:
    p = prompt.lower()
    swaps = {
        "naruto": "ninja estilo anime",
        "goku": "guerreiro de cabelo espetado",
        "dragon ball": "lutador energético",
    }
    for k, v in swaps.items():
        p = p.replace(k, v)
    return p

# ===============================
# CLASSIFICADOR
# ===============================
def classify(prompt: str) -> str:
    p = prompt.lower()
    if "suporte" in p:
        return "suporte"
    if "miniatura" in p or "anime" in p or "personagem" in p:
        return "miniatura"
    if "caixa" in p or "organizador" in p:
        return "utilidade"
    return "geral"

# ===============================
# PLANEJADOR IA (gera parâmetros)
# ===============================
def planner_agent(prompt: str, category: str) -> dict:
    system = """
Você é um planejador CAD para OpenSCAD.
Retorne JSON com parâmetros mínimos para gerar o modelo:

{
 "categoria": "",
 "altura_mm": 80,
 "largura_mm": 60,
 "profundidade_mm": 50,
 "angulo_encosto_graus": 65,
 "trava_frontal_mm": 12,
 "raio_base_mm": 30,
 "detalhes": ["lista curta"],
 "precisa_suporte": true
}

Regras:
- Se for suporte: inclua angulo_encosto_graus e trava_frontal_mm.
- Se for miniatura: inclua raio_base_mm e altura_mm.
- Não invente marcas/nomes protegidos; use estilo.
- Mantenha valores plausíveis para FDM.
"""
    payload = json.dumps({"prompt": prompt, "categoria": category}, ensure_ascii=False)
    out = ask_ai(system, payload, json_mode=True)
    return json.loads(out)

# ===============================
# CAD AGENT (OpenSCAD PARAMÉTRICO – PROFISSIONAL)
# ===============================
def cad_agent(plan: dict, prompt: str) -> str:
    system = """
Você é um modelador 3D profissional especialista em OpenSCAD.

TAREFA:
Gerar código OpenSCAD paramétrico, modular e compilável.

REGRAS (obrigatórias):
- Retorne SOMENTE código OpenSCAD.
- Use módulos (module) e variáveis no topo.
- Use $fn>=48 para curvas.
- Use union(), difference(), hull(), translate(), rotate(), mirror() quando necessário.
- Não deixar partes soltas; tudo conectado.
- Espessura mínima >= 2mm.
- Para SUPORTE: base, encosto (60–70°), trava frontal (8–14mm), estabilidade.
- Para MINIATURA: base circular, corpo, cabeça, braços; proporções coerentes.
- Evite “um cubo simples”; produza forma reconhecível.
- O código DEVE compilar no OpenSCAD.

DICAS:
- Use hull() para suavizar volumes.
- Para miniaturas estilo anime: cabelo simples (cone/cilindros), braços inclinados.
- Para suportes: reforços laterais triangulares são bem-vindos.
"""
    user = json.dumps({"plano": plan, "prompt": prompt}, ensure_ascii=False)
    scad = ask_ai(system, user)
    return clean_scad(scad)

# ===============================
# VALIDAÇÃO BÁSICA (sanidade)
# ===============================
def validate_scad(scad: str):
    if len(scad) < 20:
        raise Exception("SCAD muito curto")
    if "cube" not in scad and "cylinder" not in scad and "sphere" not in scad:
        raise Exception("SCAD sem primitives")
    # evita retorno vazio/ruim
    return True

# ===============================
# STL
# ===============================
def generate_stl(scad_code: str) -> bytes:
    name = str(uuid.uuid4())
    scad_file = f"/tmp/{name}.scad"
    stl_file = f"/tmp/{name}.stl"

    with open(scad_file, "w") as f:
        f.write(scad_code)

    res = subprocess.run(
        ["openscad", "-o", stl_file, scad_file],
        capture_output=True,
        text=True
    )

    if res.returncode != 0:
        raise Exception(res.stderr)

    with open(stl_file, "rb") as f:
        return f.read()

# ===============================
# PIPELINE
# ===============================
def pipeline(prompt: str) -> bytes:
    p = originalizer(prompt)
    cat = classify(p)
    plan = planner_agent(p, cat)
    scad = cad_agent(plan, p)
    validate_scad(scad)
    stl = generate_stl(scad)
    return stl

# ===============================
# ROTAS
# ===============================
@app.get("/")
def home():
    return {"status": "online", "mode": "cad_profissional"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")
        stl = pipeline(prompt)
        fname = filename_from_prompt(prompt)

        return Response(
            content=stl,
            media_type="application/octet-stream",
            headers={"Content-Disposition": f"attachment; filename={fname}"}
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"erro": "Falha ao gerar STL", "detalhe": str(e)}
        )

# ===============================
# START
# ===============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
