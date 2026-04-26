from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import subprocess, uuid, os, re, json

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

client = None
if OPENAI_API_KEY:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=OPENAI_API_KEY)
    except:
        client = None

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
def nome_arquivo(prompt):
    base = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")
    return (base[:40] or "modelo") + ".stl"

def limpar_json(texto):
    texto = texto.replace("```json", "").replace("```", "").strip()
    return texto


# ===============================
# ORIGINALIZADOR
# ===============================
def originalizar(prompt):
    trocas = {
        "naruto": "ninja estilo anime",
        "goku": "guerreiro estilo anime de cabelo espetado",
        "dragon ball": "anime de guerreiros energéticos",
    }

    p = prompt.lower()
    for k, v in trocas.items():
        p = p.replace(k, v)

    return p


# ===============================
# CAD ENGINE DETERMINÍSTICO
# ===============================
def scad_piramide(largura=80, profundidade=80, altura=80):
    return f"""
polyhedron(
    points=[
        [0,0,0],
        [{largura},0,0],
        [{largura},{profundidade},0],
        [0,{profundidade},0],
        [{largura/2},{profundidade/2},{altura}]
    ],
    faces=[
        [0,1,2,3],
        [0,1,4],
        [1,2,4],
        [2,3,4],
        [3,0,4]
    ]
);
"""

def scad_suporte_celular():
    return """
union() {
    // base
    cube([90,70,6]);

    // encosto inclinado
    translate([0,55,6])
        rotate([65,0,0])
        cube([90,6,100]);

    // trava frontal
    translate([0,8,6])
        cube([90,10,14]);

    // reforços laterais
    translate([5,45,6])
        rotate([65,0,0])
        cube([8,8,70]);

    translate([77,45,6])
        rotate([65,0,0])
        cube([8,8,70]);
}
"""

def scad_organizador():
    return """
difference() {
    union() {
        cube([120,80,45]);
        translate([125,0,0]) cube([60,80,45]);
    }

    translate([4,4,4]) cube([112,72,45]);
    translate([129,4,4]) cube([52,72,45]);
}
"""

def scad_chaveiro():
    return """
difference() {
    hull() {
        translate([0,0,0]) cylinder(h=4, r=18, $fn=64);
        translate([45,0,0]) cylinder(h=4, r=18, $fn=64);
    }

    translate([-5,0,-1]) cylinder(h=8, r=5, $fn=32);
}
"""

def scad_borboleta():
    return """
union() {
    // asa esquerda superior
    hull() {
        translate([-12,0,2]) sphere(r=8, $fn=48);
        translate([-42,22,2]) sphere(r=14, $fn=48);
        translate([-25,38,2]) sphere(r=10, $fn=48);
    }
    // asa esquerda inferior
    hull() {
        translate([-10,-4,2]) sphere(r=7, $fn=48);
        translate([-38,-25,2]) sphere(r=12, $fn=48);
        translate([-20,-36,2]) sphere(r=9, $fn=48);
    }
    // asa direita superior
    mirror([1,0,0])
    hull() {
        translate([-12,0,2]) sphere(r=8, $fn=48);
        translate([-42,22,2]) sphere(r=14, $fn=48);
        translate([-25,38,2]) sphere(r=10, $fn=48);
    }
    // asa direita inferior
    mirror([1,0,0])
    hull() {
        translate([-10,-4,2]) sphere(r=7, $fn=48);
        translate([-38,-25,2]) sphere(r=12, $fn=48);
        translate([-20,-36,2]) sphere(r=9, $fn=48);
    }
    // corpo
    translate([0,0,2])
        scale([0.35,1.7,0.35])
        sphere(r=18, $fn=64);
    // cabeça
    translate([0,32,4])
        sphere(r=6, $fn=48);
    // antenas
    translate([-3,37,5])
        rotate([0,0,25])
        cylinder(h=20, r=1, $fn=16);
    translate([3,37,5])
        rotate([0,0,-25])
        cylinder(h=20, r=1, $fn=16);
}
"""

def scad_miniatura_anime():
    return """
union() {
    // base
    cylinder(h=6, r=32, $fn=64);
    // pernas
    translate([-8,0,6]) cylinder(h=28, r=5, $fn=32);
    translate([8,0,6]) cylinder(h=28, r=5, $fn=32);
    // corpo
    translate([0,0,35])
        scale([0.8,0.55,1.25])
        sphere(r=18, $fn=64);
    // cabeça
    translate([0,0,68])
        sphere(r=15, $fn=64);
    // braços
    translate([-20,0,48])
        rotate([0,35,20])
        cylinder(h=32, r=4, $fn=32);
    translate([20,0,48])
        rotate([0,-35,-20])
        cylinder(h=32, r=4, $fn=32);
    // cabelo espetado simples
    translate([0,0,82])
        cylinder(h=18, r1=16, r2=0, $fn=6);
}
"""

# ===============================
# CLASSIFICADOR LOCAL
# ===============================
def scad_deterministico(prompt):
    p = prompt.lower()
    if "pirâmide" in p or "piramide" in p:
        return scad_piramide()
    if "suporte" in p and "celular" in p:
        return scad_suporte_celular()
    if "organizador" in p or "porta caneta" in p:
        return scad_organizador()
    if "chaveiro" in p:
        return scad_chaveiro()
    if "borboleta" in p:
        return scad_borboleta()
    if "miniatura" in p or "anime" in p or "personagem" in p:
        return scad_miniatura_anime()
    return None

# ===============================
# IA PLANEJADORA CAD
# ===============================
def plano_cad_ia(prompt):
    if not client:
        return None

    system = """
Você é um engenheiro CAD paramétrico.

Você NÃO deve gerar código OpenSCAD.
Você deve retornar SOMENTE JSON.

Objetivo:
Entender o pedido e escolher uma estratégia CAD.

Formato obrigatório:
{
  "categoria": "suporte|organizador|chaveiro|decoracao|miniatura|geometrico|geral",
  "forma_base": "cubo|cilindro|esfera|piramide|organico",
  "largura": 80,
  "profundidade": 60,
  "altura": 80,
  "detalhes": ["lista curta"],
  "funcional": true,
  "precisa_base": true
}

Regras CRÍTICAS:
- As chaves 'categoria' e 'forma_base' DEVEM conter exatamente uma das opções fornecidas.
- Use APENAS letras minúsculas e NUNCA use acentos na forma_base (Ex: use "piramide" ao invés de "pirâmide").
- Não use nomes oficiais de personagens.
- Para miniatura/anime, use categoria miniatura.
- Para pirâmide, use forma_base "piramide".
"""

    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": prompt}
        ],
        temperature=0.15
    )

    return json.loads(limpar_json(resp.choices[0].message.content))


# ===============================
# INTERPRETADOR DO PLANO CAD
# ===============================
def scad_do_plano(plano):
    if not plano:
        return scad_suporte_celular()

    categoria = plano.get("categoria", "geral")
    
    # Anti-Falha: Limpa qualquer acento e joga para minúsculo para evitar o erro do cubo perfeito
    forma = plano.get("forma_base", "cubo").lower().replace("â", "a").replace("í", "i").replace("á", "a")

    largura = float(plano.get("largura", 80))
    profundidade = float(plano.get("profundidade", 60))
    altura = float(plano.get("altura", 80))

    if forma == "piramide":
        return scad_piramide(largura, profundidade, altura)

    if categoria == "suporte":
        return scad_suporte_celular()

    if categoria == "organizador":
        return scad_organizador()

    if categoria == "chaveiro":
        return scad_chaveiro()

    if categoria == "miniatura":
        return scad_miniatura_anime()

    if forma == "cilindro":
        return f"cylinder(h={altura}, r={largura/2}, $fn=64);"

    if forma == "esfera":
        return f"sphere(r={largura/2}, $fn=64);"

    return f"cube([{largura},{profundidade},{altura}]);"


# ===============================
# VALIDAÇÃO
# ===============================
def validar_scad(scad):
    if not scad or len(scad) < 20:
        return False
    if scad.count("(") != scad.count(")"):
        return False
    if scad.count("{") != scad.count("}"):
        return False
    if not any(x in scad for x in ["cube", "sphere", "cylinder", "polyhedron", "union", "hull"]):
        return False
    return True


# ===============================
# STL
# ===============================
def gerar_stl(scad):
    name = str(uuid.uuid4())
    scad_file = f"/tmp/{name}.scad"
    stl_file = f"/tmp/{name}.stl"

    with open(scad_file, "w", encoding="utf-8") as f:
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
# PIPELINE FUSION-LIKE
# ===============================
def pipeline(prompt):
    prompt_original = prompt
    prompt = originalizar(prompt)

    scad = scad_deterministico(prompt)

    if not scad:
        plano = plano_cad_ia(prompt)
        scad = scad_do_plano(plano)

    if not validar_scad(scad):
        scad = scad_suporte_celular()

    return gerar_stl(scad), nome_arquivo(prompt_original)


# ===============================
# ROTAS
# ===============================
@app.get("/")
def home():
    return {
        "status": "online",
        "modo": "cad_engine_fusion_like",
        "ia": bool(client)
    }

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")

        stl, filename = pipeline(prompt)

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
            content={
                "erro": "Falha ao gerar modelo",
                "detalhe": str(e)
            }
        )

# NOVA ROTA: MELHORAR PROMPT
@app.post("/melhorar-prompt")
async def route_improve_prompt(req: Request):
    if not client:
        return JSONResponse({"erro": "A IA não está configurada."}, status_code=500)
    try:
        data = await req.json()
        prompt_original = data.get("prompt", "")
        
        system_msg = "Você é um engenheiro especialista em modelagem 3D. O usuário vai te dar uma ideia. Reescreva essa ideia em 1 a 2 frases altamente detalhadas focando na geometria do objeto (formas, estabilidade, ângulos e recortes utilitários). Retorne APENAS o novo texto sugerido, sem explicações extras."
        
        resp = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": prompt_original}
            ],
            temperature=0.4
        )
        sugestao = resp.choices[0].message.content.replace("\"", "")
        return JSONResponse({"sugestao": sugestao})
    except Exception as e:
        return JSONResponse({"erro": str(e)}, status_code=500)


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
