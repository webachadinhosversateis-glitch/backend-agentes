from fastapi import FastAPI, Request
from fastapi.responses import Response
from fastapi.middleware.cors import CORSMiddleware
import subprocess
import uuid
import os

app = FastAPI()

# Libera acesso do AntiGravity / navegador
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===============================
# AGENTE INTERPRETAÇÃO
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
# AGENTE ENGENHARIA
# ===============================
def engineering_agent(data):
    data["wall_thickness_mm"] = 2
    data["overhang_angle"] = 45
    data["base_contact_area"] = 50
    data["has_floating_parts"] = False
    return data


# ===============================
# AGENTE TOKEN
# ===============================
def monetization_agent(data):
    base = 10

    if data["tipo"] == "funcional":
        base += 20

    if data["complexidade"] == "alto":
        base += 50

    return base


# ===============================
# AGENTE CAD / OPENSCAD
# ===============================
def cad_agent(data):
    desc = data["descricao"]

    if "suporte" in desc and "celular" in desc:
        scad = """
        union() {
            cube([80, 60, 5]);

            translate([0, 42, 5])
                rotate([65, 0, 0])
                cube([80, 5, 90]);

            translate([0, 5, 5])
                cube([80, 6, 12]);
        }
        """

    elif "caixa" in desc:
        scad = """
        difference() {
            cube([80, 60, 100]);
            translate([2, 2, 2])
                cube([76, 56, 100]);
        }
        """

    elif "borboleta" in desc:
        scad = """
        union() {
            // corpo
            translate([40, 30, 5])
                cylinder(h=8, r=5, $fn=32);

            // asas
            translate([20, 30, 5])
                scale([1.5, 1, 0.2])
                sphere(r=18, $fn=32);

            translate([60, 30, 5])
                scale([1.5, 1, 0.2])
                sphere(r=18, $fn=32);

            // base suporte celular
            translate([0, -10, 0])
                cube([80, 60, 5]);

            // encosto inclinado
            translate([0, 35, 5])
                rotate([65, 0, 0])
                cube([80, 5, 80]);

            // trava frontal
            translate([0, 0, 5])
                cube([80, 6, 10]);
        }
        """

    else:
        scad = """
        cube([80, 60, 100]);
        """

    return scad


# ===============================
# VALIDAÇÃO
# ===============================
def validate_model(data):
    errors = []

    if data["wall_thickness_mm"] < 1.2:
        errors.append("Espessura muito fina")

    if data["overhang_angle"] > 55:
        errors.append("Overhang crítico")

    if data["base_contact_area"] < 20:
        errors.append("Base de contato pequena")

    if data["has_floating_parts"]:
        errors.append("Partes flutuantes detectadas")

    return errors


# ===============================
# CORRETOR
# ===============================
def corrector_agent(data, errors):
    if "Espessura muito fina" in errors:
        data["wall_thickness_mm"] = 1.6

    if "Overhang crítico" in errors:
        data["overhang_angle"] = 45

    if "Base de contato pequena" in errors:
        data["base_contact_area"] = 50

    if "Partes flutuantes detectadas" in errors:
        data["has_floating_parts"] = False

    return data


# ===============================
# GERAR STL REAL
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
# PIPELINE COMPLETO
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
# ROTAS
# ===============================
@app.get("/")
def home():
    return {
        "status": "online",
        "mensagem": "API de geração STL funcionando"
    }


@app.get("/agente")
def agente():
    return {
        "status": "ok",
        "mensagem": "Agentes ativos"
    }


@app.post("/gerar")
async def gerar(req: Request):
    body = await req.json()
    prompt = body.get("prompt", "modelo simples")

    stl, tokens = run_pipeline(prompt)

    return Response(
        content=stl,
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename=modelo.stl",
            "X-Tokens-Used": str(tokens),
            "Access-Control-Expose-Headers": "Content-Disposition, X-Tokens-Used"
        }
    )


# ===============================
# START
# ===============================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8080))
    )
