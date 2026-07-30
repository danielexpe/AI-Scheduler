import os
import time
import requests
import logging

logger = logging.getLogger(__name__)

DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_BASE_URL = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
DEEPSEEK_MAX_TOKENS = int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))
DEEPSEEK_TIMEOUT = int(os.getenv("DEEPSEEK_TIMEOUT", "120"))
DEEPSEEK_MAX_RETRIES = int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))


SYSTEM_PROMPT_BASE = """Você é um assistente que gera infográficos e resumos em HTML para email.

Regras:
- Gere HTML puro e válido (DOCTYPE, head, body)
- Todo CSS deve ser INLINE (atributo style="..." em cada elemento)
- Use tabelas para layout de infográfico quando apropriado
- Design responsivo, largura máxima 600px
- Cores escuras e profissionais (fundo escuro, texto claro)
- Inclua cabeçalho com título e data de geração
- Inclua rodapé com fonte dos dados
- NUNCA use CSS externo ou <style> tags (emails não suportam bem)
- NUNCA use JavaScript
- Otimize imagens (use texto formatado em vez de imagens quando possível)
- NÃO use backticks (```) ou marcação de código no início/fim da resposta

Responda APENAS com o HTML. Nada antes, nada depois."""


TONE_INSTRUCTIONS = {
    "infografico": "Use cards, ícones Unicode, dados numéricos destacados, timeline visual. Layout visual rico.",
    "resumo": "Parágrafos concisos, tópicos com bullets, hierarquia clara de títulos. Texto direto e informativo.",
    "newsletter": "Estilo jornal, manchetes, subtítulos, data, autor. Layout de boletim informativo.",
    "analise": "Tabelas comparativas, gráficos baseados em texto, conclusões em destaque. Formato analítico.",
}

SEARCH_INSTRUCTION = """
Use a função de web search para encontrar as informações mais recentes e
relevantes. Priorize fontes confiáveis como portais de notícia estabelecidos.
Cite as fontes no rodapé do infográfico.
"""


def call_deepseek(prompt_content, tone="infografico", enable_search=True):
    if not DEEPSEEK_API_KEY:
        return None, "DEEPSEEK_API_KEY não configurada no .env"

    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["infografico"])
    system_prompt = SYSTEM_PROMPT_BASE + "\n\nEstilo solicitado: " + tone_instruction

    if enable_search:
        system_prompt += "\n\n" + SEARCH_INSTRUCTION

    user_prompt = f"Tópico: {prompt_content}\n\nGere o infográfico/relatório em HTML com CSS inline conforme as instruções."

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": DEEPSEEK_MAX_TOKENS,
        "temperature": 0.7,
        "stream": False,
    }

    last_error = None
    for attempt in range(DEEPSEEK_MAX_RETRIES + 1):
        try:
            if attempt > 0:
                time.sleep(5 * attempt)

            response = requests.post(
                f"{DEEPSEEK_BASE_URL}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=DEEPSEEK_TIMEOUT,
            )

            if response.status_code == 401:
                return None, "API Key inválida. Verifique DEEPSEEK_API_KEY."
            if response.status_code == 429:
                last_error = "Rate limit. Tentando novamente..."
                time.sleep(5)
                continue
            if response.status_code != 200:
                last_error = f"Erro API DeepSeek ({response.status_code}): {response.text[:200]}"
                continue

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            if content.startswith("```html"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            return content, None

        except requests.exceptions.Timeout:
            last_error = "Timeout ao conectar com DeepSeek API"
            continue
        except requests.exceptions.ConnectionError:
            last_error = "Erro de conexão com DeepSeek API"
            continue
        except Exception as e:
            last_error = str(e)
            continue

    return None, last_error or "Erro desconhecido"
