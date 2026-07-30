# Integracao com DeepSeek API

## Modelo Utilizado

Usaremos o modelo **deepseek-chat** (DeepSeek-V3), que suporta web search via
o parametro `enable_search` na API.

A API da DeepSeek e compativel com o formato OpenAI Chat Completions.

Endpoint base: `https://api.deepseek.com`

---

## Configuracao (.env)

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_MODEL=deepseek-chat
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MAX_TOKENS=4096
DEEPSEEK_TIMEOUT=120
```

---

## Funcao Principal

```python
# assinatura planejada
def call_deepseek(
    prompt_content: str,
    tone: str = "infografico",
    enable_search: bool = True
) -> str:
    """
    Envia prompt para DeepSeek API e retorna resposta formatada em HTML.
    
    Args:
        prompt_content: O prompt base cadastrado pelo usuario
        tone: Tom/estilo desejado (infografico, resumo, newsletter, etc.)
        enable_search: Se True, ativa web search da DeepSeek
    
    Returns:
        String HTML formatada pronta para o email
    """
```

---

## System Prompt (instrucoes para o modelo)

O system prompt sera montado dinamicamente combinando:

1. **Instrucao de formato** (fixa):
   ```
   Voce eh um assistente que gera infograficos e resumos em HTML para email.
   
   Regras:
   - Gere HTML puro e valido (DOCTYPE, head, body)
   - Todo CSS deve ser INLINE (atributo style="..." em cada elemento)
   - Use tabelas para layout de infografico quando apropriado
   - Design responsivo, largura maxima 600px
   - Cores escuras e profissionais (fundo escuro, texto claro)
   - Inclua cabecalho com titulo e data de geracao
   - Inclua rodape com fonte dos dados
   - NUNCA use CSS externo ou <style> tags (emails nao suportam bem)
   - NUNCA use JavaScript
   - Otimize imagens (use texto formatado em vez de imagens quando possivel)
   
   Responda APENAS com o HTML. Nada antes, nada depois.
   ```

2. **Instrucao de tom/estilo** (baseado no `tone`):
   - `infografico`: Use cards, icones Unicode, dados numericos destacados, timeline visual
   - `resumo`: Paragrafos concisos, topicos com bullets, hierarquia clara de titulos
   - `newsletter`: Estilo jornal, manchetes, subtitulos, data, autor
   - `analise`: Tabelas comparativas, graficos baseados em texto, conclusoes em destaque

3. **Instrucao de busca** (se `enable_search=True`):
   ```
   Use a funcao de web search para encontrar as informacoes mais recentes e
   relevantes. Priorize fontes confiaveis como portais de noticia estabelecidos.
   Cite as fontes no rodape do infografico.
   ```

---

## Chamada da API (formato planejado)

```python
import requests  # ou openai Python SDK

headers = {
    "Authorization": f"Bearer {api_key}",
    "Content-Type": "application/json"
}

payload = {
    "model": "deepseek-chat",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "max_tokens": 4096,
    "temperature": 0.7,
    "stream": False
}

# Se enable_search for True, adiciona:
# NOTA: verificar na documentacao oficial o parametro exato
# Algumas APIs usam tools/search, outras usam parametro direto
# payload["tools"] = [{"type": "web_search"}]
```

---

## Tratamento de Erros

| Erro                          | Tratamento                                    |
|-------------------------------|-----------------------------------------------|
| Timeout (>120s)               | Retry 1x, depois loga erro                    |
| Rate limit (429)              | Espera 5s, retry 1x                           |
| API key invalida (401)        | Erro fatal, loga, notifica                    |
| Resposta vazia                | Loga, envia email dizendo que nao houve retorno |
| Modelo nao encontrado (404)   | Erro fatal, verificar nome do modelo          |
| Erro de rede                  | Retry 3x com exponential backoff              |
| Web search indisponivel       | Fallback: executa sem search, avisa no email   |

---

## Timeout e Retry

```python
TIMEOUT = 120  # segundos
MAX_RETRIES = 2
RETRY_DELAY = 5  # segundos entre tentativas
```

## Logging

Toda chamada a API DeepSeek deve logar:
- Timestamp inicio e fim
- Duracao total
- Tokens usados (se disponivel na resposta)
- Status (sucesso/erro)
- Preview dos primeiros 200 caracteres da resposta

---

## Custo

- Monitorar consumo via logs de tokens
- Exibir estimativa de custo no dashboard (opcional, futuro)
- DeepSeek tem precos muito baixos (~$0.27/M input tokens, ~$1.10/M output tokens para V3)
