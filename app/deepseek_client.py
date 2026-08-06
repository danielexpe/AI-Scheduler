import os
import time
import requests
import logging

logger = logging.getLogger(__name__)


def _get_api_key():
    return os.getenv("DEEPSEEK_API_KEY")


def _get_base_url():
    return os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")


def _get_model():
    return os.getenv("DEEPSEEK_MODEL", "deepseek-chat")


def _get_max_tokens():
    return int(os.getenv("DEEPSEEK_MAX_TOKENS", "4096"))


def _get_timeout():
    return int(os.getenv("DEEPSEEK_TIMEOUT", "120"))


def _get_max_retries():
    return int(os.getenv("DEEPSEEK_MAX_RETRIES", "2"))


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
    api_key = _get_api_key()
    if not api_key:
        logger.error("DEEPSEEK_API_KEY nao configurada")
        return None, "DEEPSEEK_API_KEY não configurada no .env"

    tone_instruction = TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["infografico"])
    system_prompt = SYSTEM_PROMPT_BASE + "\n\nEstilo solicitado: " + tone_instruction

    if enable_search:
        system_prompt += "\n\n" + SEARCH_INSTRUCTION

    user_prompt = prompt_content

    logger.info("Chamando DeepSeek API: modelo=%s tone=%s search=%s prompt_len=%d",
                 _get_model(), tone, enable_search, len(prompt_content))

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": _get_model(),
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": _get_max_tokens(),
        "temperature": 0.7,
        "stream": False,
    }

    max_retries = _get_max_retries()
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                logger.warning("Retry %d/%d apos 5s...", attempt, max_retries)
                time.sleep(5 * attempt)

            logger.debug("POST %s/v1/chat/completions (attempt %d)", _get_base_url(), attempt + 1)
            response = requests.post(
                f"{_get_base_url()}/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=_get_timeout(),
            )

            if response.status_code == 401:
                logger.error("DeepSeek retornou 401 - API Key invalida")
                return None, "API Key inválida. Verifique DEEPSEEK_API_KEY."
            if response.status_code == 429:
                last_error = "Rate limit. Tentando novamente..."
                logger.warning("DeepSeek rate limit (429) - retrying...")
                time.sleep(5)
                continue
            if response.status_code != 200:
                last_error = f"Erro API DeepSeek ({response.status_code}): {response.text[:200]}"
                logger.error("DeepSeek status %d: %s", response.status_code, response.text[:200])
                continue

            data = response.json()
            content = data["choices"][0]["message"]["content"]
            logger.info("DeepSeek respondeu com %d chars", len(content))

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
            logger.warning("DeepSeek timeout (attempt %d)", attempt + 1)
            continue
        except requests.exceptions.ConnectionError:
            last_error = "Erro de conexão com DeepSeek API"
            logger.warning("DeepSeek connection error (attempt %d)", attempt + 1)
            continue
        except Exception as e:
            last_error = str(e)
            logger.error("DeepSeek excecao inesperada: %s", e)
            continue

    logger.error("DeepSeek todas as %d tentativas falharam: %s", max_retries + 1, last_error)
    return None, last_error or "Erro desconhecido"
