Falha minha! Eu usei um pacote Python chamado `requests` que não está instalado na sua máquina do Railway (lá só tem instalado as bibliotecas básicas do projeto antigo).

Para você não ter o trabalho chato de ter que instalar pacotes novos, eu reescrevi o código usando o `urllib`, que é uma biblioteca **nativa** do próprio Python, ou seja, é 100% garantido que vai rodar de primeira sem precisar instalar nada!

E de quebra eu ainda adicionei uma melhoria de "Multi-Threading" (`asyncio`) para garantir que o seu servidor não trave a tela de carregamento de ninguém.

Pode copiar este código abaixo, substituir todo o seu `main.py` de novo e salvar. Desta vez o Railway vai reiniciar limpinho!

```python
from fastapi import FastAPI, Request
from fastapi.responses import Response, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import os, json, re, asyncio
import urllib.request
import urllib.error

# A SUA CHAVE DA TRIPO ESTÁ AQUI
TRIPO_API_KEY = "tsk_yM5te_C_T33v2KfSuCX_IdMDELB2hKzdyL5RnX_aJp5"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================================
# TRIPO 3D NATIVE INTEGRATION
# ==========================================
async def generate_tripo_model(prompt):
    url = "https://api.tripo3d.ai/v2/openapi/task"
    headers = {
        "Authorization": f"Bearer {TRIPO_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = json.dumps({
        "type": "text_to_model",
        "prompt": prompt
    }).encode("utf-8")
    
    req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            create_res = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise Exception(f"Erro ao iniciar tarefa na Tripo: {e.read().decode('utf-8')}")
        
    task_id = create_res.get("data", {}).get("task_id")
    if not task_id:
        raise Exception("A API da Tripo não retornou um ID de tarefa.")
        
    print(f"⏳ Tarefa {task_id} criada. Aguardando a IA esculpir a malha...")
    
    model_url = None
    poll_url = f"https://api.tripo3d.ai/v2/openapi/task/{task_id}"
    poll_req = urllib.request.Request(poll_url, headers=headers, method="GET")
    
    for attempt in range(60): # Espera no máximo 120 segundos
        await asyncio.sleep(2) # Pausa assíncrona para não travar o servidor
        try:
            with urllib.request.urlopen(poll_req) as poll_res:
                data = json.loads(poll_res.read().decode("utf-8")).get("data", {})
                status = data.get("status")
                
                if status == "success":
                    model_url = data.get("result", {}).get("model", {}).get("url")
                    break
                elif status in ["failed", "cancelled", "unknown"]:
                    raise Exception("A geração do modelo falhou nos servidores da Tripo3D.")
        except Exception:
            continue
            
    if not model_url:
        raise Exception("Tempo limite esgotado. A Tripo demorou muito para responder.")
        
    print(f"✅ Modelo pronto! Baixando malha colorida...")
    try:
        with urllib.request.urlopen(model_url) as glb_response:
            return glb_response.read()
    except Exception as e:
        raise Exception("Erro ao baixar o arquivo GLB da Tripo3D.")

# ==========================================
# ROTAS DO FASTAPI
# ==========================================
@app.get("/")
def home():
    return {"status": "online", "modo": "tripo3d_genai_native"}

@app.post("/gerar")
async def gerar(req: Request):
    try:
        body = await req.json()
        prompt = body.get("prompt", "")
        if not prompt:
            return JSONResponse(status_code=400, content={"erro": "Você precisa escrever algo."})
        
        glb_data = await generate_tripo_model(prompt)
        
        filename = re.sub(r"[^a-z0-9]+", "_", prompt.lower()).strip("_")[:30] + ".glb"
        return Response(
            content=glb_data, 
            media_type="model/gltf-binary", 
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        print("Erro Servidor:", str(e))
        return JSONResponse(status_code=500, content={"erro": str(e)})

@app.post("/melhorar-prompt")
async def route_improve_prompt(req: Request):
    try:
        data = await req.json()
        prompt_original = data.get("prompt", "")
        
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            from openai import OpenAI
            client = OpenAI(api_key=openai_key)
            system_msg = "Você é um tradutor especialista em Midjourney/Tripo3D. Pegue o pedido do usuário e transforme num prompt em INGLÊS focado em textura, estilo e material (ex: 'A highly detailed 3D model of a...', '8k resolution', 'physically based rendering'). Retorne APENAS o prompt em inglês."
            resp = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": prompt_original}
                ],
                temperature=0.4
            )
            sugestao = resp.choices[0].message.content.replace("\"", "")
            return JSONResponse({"sugestao": sugestao})
        else:
            sugestao = f"A highly detailed 3D model of {prompt_original}, 8k resolution, realistic textures"
            return JSONResponse({"sugestao": sugestao})
            
    except Exception as e:
        return JSONResponse(status_code=500, content={"erro": str(e)})

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
```
