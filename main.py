from fastapi import FastAPI, Request
from fastapi.responses import Response
import subprocess
import uuid
import os

app = FastAPI()

# ===============================
# 🧠 AGENTE INTERPRETAÇÃO
# ===============================
def interpreter_agent(prompt):
    prompt = prompt.lower()

    return {
        "descricao": prompt,
        "tipo": "funcional" if "suporte" in prompt else "decorativo",
        "complexidade": "medio",
        "precisao": "otimizado"
    }

# ===============================
# ⚙️ AGENTE ENGENHARIA
# ===============================
def engineering_agent(data):
    data["wall_thickness_mm"] = 2
    data["overhang_angle"] = 45
    data["base_contact_area"] = 50
    data["has_floating_parts"] = False
    return data

# ===============================
# 💰 AGENTE TOKEN
# ===============================
def monetization_agent(data):
    base = 10
    if data["tipo"] == "funcional":
        base += 20
    if data["complexidade"] == "alto":
        base += 50
    return base

# ===============================
# 🧱 AGENTE CAD (INTELIGENTE)
# ===============================
def cad_agent(data):
    desc = data["descricao"]

    if "suporte celular" in desc:
        scad = """
        union() {
            cube([80, 60, 5]);
            translate([0, 40, 0])
                rotate([60,0,0])
                cube([80, 5, 100]);
        }
        """
    elif "caixa" in desc:
        scad = """
        difference() {
            cube([80,60,100]);
            translate([2,2,2])
                cube([76,56,100]);
        }
        """
    else:
        scad = "cube([80,60,100]);"

    return scad

# ===============================
# 🔬 VALIDAÇÃO
# ===============================
def validate_model(data):
    errors = []

    if data["wall_thickness_mm"] < 1.2:
        errors.append("Espessura muito fina")

    if data["overhang_angle"] > 55:
        errors.append("Overhang crítico")

    return errors

# ===============================
# 🔧 CORRETOR
# ===============================
def corrector_agent(data, errors):
    if "Espessura muito fina" in errors:
        data["wall_thickness_mm"] = 1.6

    if "Overhang crítico" in errors:
        data["overhang_angle"] = 45

    return data

# ===============================
# 🖨️ GERAR STL REAL
# ===============================
def generate_stl(scad_code):
    nome = str(uuid.uuid4())
    scad_file = f"/tmp/{nome}.scad"
    stl_file = f"/tmp/{nome}.stl"

    with open(scad_file, "w") as f:
        f.write(scad_code)

    subprocess.run(
        ["openscad", "-o", stl_file, scad_file],
        check=True
    )

    with open(stl_file, "rb") as f:
        return f.read()

# ===============================
# 🔁 PIPELINE COMPLETO
# ===============================
def run_pipeline(prompt):

    step1 = interpreter_agent(prompt)
    tokens = monetization_agent(step1)

    step2 = engineering_agent(step1)

    errors = validate_model(step2)

    if errors:
        step2 = corrector_agent(step2, errors)

    scad = cad_agent(step2)

    stl = generate_stl(scad)

    return stl, tokens

# ===============================
# 🌐 ROTAS
# ===============================
@app.get("/")
def home():
    return {"status": "online"}

@app.post("/gerar")
async def gerar(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "")

    stl, tokens = run_pipeline(prompt)

    return Response(
        content=stl,
        media_type="application/sla",
        headers={
            "Content-Disposition": f"attachment; filename=modelo.stl",
            "X-Tokens-Used": str(tokens)
        }
    )

# ===============================
# START
# ===============================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
