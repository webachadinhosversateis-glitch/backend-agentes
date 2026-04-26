from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os

app = FastAPI()

# ===============================
# CORS
# ===============================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===============================
# 🧠 AGENTE ORIGINALIZADOR
# ===============================
def originalizer(prompt):
    prompt = prompt.lower()

    replacements = {
        "naruto": "ninja estilo anime",
        "goku": "guerreiro de cabelo espetado",
        "dragon ball": "lutador energético",
    }

    for key in replacements:
        prompt = prompt.replace(key, replacements[key])

    return prompt

# ===============================
# 🧠 CLASSIFICADOR
# ===============================
def classify(prompt):
    if "suporte" in prompt:
        return "suporte"
    if "miniatura" in prompt or "anime" in prompt:
        return "miniatura"
    if "borboleta" in prompt:
        return "decorativo"

    return "desconhecido"

# ===============================
# 🧠 PLANEJADOR CAD
# ===============================
def planner(prompt, category):
    return {
        "categoria": category,
        "descricao": prompt,
        "base": "plana",
        "estrutura": "conectada",
        "altura": 80
    }

# ===============================
# 🧱 CAD AGENT (CRIATIVO)
# ===============================
def cad_agent(plan):
    cat = plan["categoria"]
    desc = plan["descricao"]

    # SUPORTE ESTILO ANIME
    if cat == "suporte":
        return """
        union() {
            cube([80, 60, 5]);
            translate([0, 45, 0])
                rotate([60,0,0])
                cube([80, 5, 90]);

            // detalhe estilo anime
            translate([40,30,5])
                cylinder(h=3, r=15);
        }
        """

    # MINIATURA ESTILO ANIME
    if cat == "miniatura":
        return """
        union() {
            // base
            cylinder(h=5, r=30);

            // corpo
            translate([0,0,5])
                cylinder(h=40, r=10);

            // cabeça
            translate([0,0,50])
                sphere(r=12);

            // braços
            translate([-15,0,30])
                rotate([0,0,20])
                cylinder(h=30, r=3);

            translate([15,0,30])
                rotate([0,0,-20])
                cylinder(h=30, r=3);

            // cabelo estilo anime
            translate([0,0,65])
                cone();
        }
        """

    # BORBOLETA MELHORADA
    if "borboleta" in desc:
        return """
        union() {
            // asas esquerda
            hull() {
                translate([-20,0,0]) sphere(r=10);
                translate([-40,20,0]) sphere(r=5);
                translate([-40,-20,0]) sphere(r=5);
            }

            // asas direita
            hull() {
                translate([20,0,0]) sphere(r=10);
                translate([40,20,0]) sphere(r=5);
                translate([40,-20,0]) sphere(r=5);
            }

            // corpo
            cylinder(h=30, r=3);
        }
        """

    # fallback
    return "cube([80,60,100]);"


# ===============================
# 🔬 VALIDADOR
# ===============================
def validate():
    return True


# ===============================
# 🖨️ GERAR STL
# ===============================
def generate_stl(scad_code):
    nome = str(uuid.uuid4())

    scad_path = f"/tmp/{nome}.scad"
    stl_path = f"/tmp/{nome}.stl"

    with open(scad_path, "w") as f:
        f.write(scad_code)

    resultado = subprocess.run(
        ["openscad", "-o", stl_path, scad_path],
        capture_output=True,
        text=True
    )

    if resultado.returncode != 0:
        raise Exception(resultado.stderr)

    with open(stl_path, "rb") as f:
        return f.read()


# ===============================
# 🔁 PIPELINE
# ===============================
def pipeline(prompt):

    p1 = originalizer(prompt)
    cat = classify(p1)
    plan = planner(p1, cat)
    scad = cad_agent(plan)

    if not validate():
        raise Exception("Erro de validação")

    stl = generate_stl(scad)

    return stl


# ===============================
# 🌐 ROTAS
# ===============================
@app.get("/")
def home():
    return {"status": "online"}


@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")

        stl_bytes = pipeline(prompt)

        return Response(
            content=stl_bytes,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": "attachment; filename=modelo.stl"
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "erro": "Falha ao gerar STL",
                "detalhe": str(e)
            }
        )


# ===============================
# START
# ===============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
