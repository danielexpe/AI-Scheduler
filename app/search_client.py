import os
import logging

logger = logging.getLogger(__name__)

SEARCH_RESULTS_TEMPLATE = """[DADOS DE PESQUISA RECENTE]
As informacoes a seguir foram obtidas da web e devem ser usadas como base
para sua resposta. Priorize dados factuais destas fontes:

{results}

[FIM DOS DADOS DE PESQUISA]"""


def _search_tavily(query, max_results):
    try:
        from tavily import TavilyClient
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            logger.warning("TAVILY_API_KEY nao configurada, pulando Tavily")
            return None

        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=max_results,
            search_depth="advanced"
        )
        results = response.get("results", [])
        if results:
            logger.info("Tavily retornou %d resultados para: %s", len(results), query[:60])
            return results
        logger.info("Tavily nao encontrou resultados para: %s", query[:60])
        return None

    except Exception as e:
        logger.warning("Tavily falhou: %s", e)
        return None


def _search_duckduckgo(query, max_results):
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if results:
            logger.info("DuckDuckGo retornou %d resultados para: %s", len(results), query[:60])
            return [
                {"title": r.get("title", ""), "url": r.get("href", ""), "content": r.get("body", "")}
                for r in results
            ]
        logger.info("DuckDuckGo nao encontrou resultados para: %s", query[:60])
        return None

    except Exception as e:
        logger.warning("DuckDuckGo falhou: %s", e)
        return None


def _format_results(results):
    parts = []
    for i, r in enumerate(results, 1):
        title = r.get("title", "Sem titulo")
        url = r.get("url", "")
        content = r.get("content", "")
        parts.append(
            f"{i}. Titulo: {title}\n"
            f"   Fonte: {url}\n"
            f"   Conteudo: {content}\n"
        )
    return SEARCH_RESULTS_TEMPLATE.format(results="\n".join(parts))


def web_search(query, max_results=5):
    if not query or not query.strip():
        logger.warning("web_search chamada com query vazia")
        return ""

    max_results = max(max_results, 1)
    max_results = min(max_results, 20)

    logger.info("Iniciando busca web: query='%s' max=%d", query[:60], max_results)

    results = _search_tavily(query, max_results)
    if results is None:
        logger.info("Tavily indisponivel, tentando DuckDuckGo como fallback...")
        results = _search_duckduckgo(query, max_results)

    if not results:
        logger.warning("Nenhuma API de busca retornou resultados, prosseguindo sem contexto extra")
        return ""

    formatted = _format_results(results)
    logger.info("Busca web concluida: %d resultados, %d chars formatados", len(results), len(formatted))
    return formatted
