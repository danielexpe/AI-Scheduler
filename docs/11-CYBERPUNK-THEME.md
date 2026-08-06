# 11 - Tema Cyberpunk (alternavel com tema escuro atual)

## Objetivo

Adicionar um tema visual no estilo **Cyberpunk** que o usuario pode alternar com o
tema escuro atual atraves de um toggle na interface web. A preferencia e persistida
na sessao do usuario (cookie Flask), sem necessidade de login para mante-la.

## Decisoes de Design

| Decisao | Escolha |
|---|---|
| Persistencia | Flask session (cookie signed) — sem migracao de DB |
| Mecanismo CSS | Atributo `data-theme="cyberpunk"` no `<body>` + override de variaveis |
| Ativacao | Botao toggle no rodape da sidebar |
| Comportamento | POST para `/theme/toggle` → redirect de volta para pagina atual |
| Fallback | Se `session.theme` ausente, usa tema `default` (escuro atual) |
| Escopo | Afeta todas as paginas (auth e app), mesmo sem login |
| Extra effects | Scanlines, neon glow, bordas sharp, fonte mono em elementos especificos |

## Paleta Cyberpunk

### Cores Base

| Elemento | Cor | Hex | Descricao |
|---|---|---|---|
| Fundo | Preto-azulado | `#0c0c1d` | Muito escuro, tom frio |
| Cards | Azul escuro | `#141428` | Leve contraste com fundo |
| Accent (hover) | Roxo profundo | `#2d1b69` | Fundo de hover, badges info |
| Texto | Lavanda claro | `#e0e8ff` | Boa legibilidade |
| Muted | Cinza-roxo | `#6a6a9f` | Texto secundario, labels |
| **Primario (era --red)** | **Magenta neon** | `#ff00ff` | Botoes, links ativos, foco, destaque |
| **Sucesso (era --green)** | **Ciano neon** | `#00ffcc` | Botoes success, badges, toggle |
| **Warning (--yellow)** | **Amarelo eletrico** | `#ffdd00` | Alertas warning |
| Borda | Magenta translucido | `rgba(255,0,255,0.15)` | Cards, tabelas, inputs |
| **Foco (nova)** | **Ciano neon** | `#00ffcc` | `outline` em inputs com foco |

### Variaveis CSS — Mapeamento Completo

```css
[data-theme="cyberpunk"] {
    --bg:            #0c0c1d;
    --card:          #141428;
    --accent:        #2d1b69;
    --text:          #e0e8ff;
    --muted:         #6a6a9f;
    --red:           #ff00ff;   /* magenta — papel de cor primaria */
    --green:         #00ffcc;   /* ciano — sucesso, toggle */
    --yellow:        #ffdd00;   /* amarelo eletrico — warning */
    --border:        rgba(255, 0, 255, 0.15);
    --radius:        2px;       /* cantos sharp */
    --radius-sm:     2px;
    --shadow:        0 0 12px rgba(255, 0, 255, 0.15);
    --shadow-lg:     0 0 24px rgba(255, 0, 255, 0.25);
    --transition:    0.2s ease;
    --sidebar-width: 220px;
    --header-height: 56px;
}
```

### Comparacao Visual: Tema Default vs Cyberpunk

| Props | Default (dark) | Cyberpunk |
|---|---|---|
| Fundo | `#1a1a2e` (navy) | `#0c0c1d` (preto-azulado) |
| Cards | `#16213e` | `#141428` |
| Cor primaria | `#e94560` (coral) | `#ff00ff` (magenta) |
| Sucesso | `#2ecc71` (verde) | `#00ffcc` (ciano) |
| Bordas | `#2a2a4a` | `rgba(255,0,255,0.15)` (magenta translucido) |
| Cantos | `8px / 6px` | `2px` (sharp, angular) |
| Sombras | Pretas `rgba(0,0,0,...)` | Magenta glow |
| Estilo geral | Profissional, serio | Agressivo, neon, futurista |

## Efeitos Visuais Cyberpunk (Alem das Cores)

### 1. Scanlines no Fundo

```css
[data-theme="cyberpunk"] body::after {
    content: "";
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    pointer-events: none;
    z-index: 9999;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0, 0, 0, 0.03) 2px,
        rgba(0, 0, 0, 0.03) 4px
    );
}
```

### 2. Glow Neon em Titulos

```css
[data-theme="cyberpunk"] h1,
[data-theme="cyberpunk"] h2,
[data-theme="cyberpunk"] h3 {
    text-shadow: 0 0 10px rgba(255, 0, 255, 0.4);
}
```

### 3. Glow Neon em Botoes

```css
[data-theme="cyberpunk"] .btn-primary {
    box-shadow: 0 0 12px rgba(255, 0, 255, 0.3);
}
[data-theme="cyberpunk"] .btn-primary:hover {
    box-shadow: 0 0 20px rgba(255, 0, 255, 0.5);
}
[data-theme="cyberpunk"] .btn-success {
    box-shadow: 0 0 12px rgba(0, 255, 204, 0.3);
}
```

### 4. Bordas com Glow em Cards

```css
[data-theme="cyberpunk"] .card {
    border: 1px solid var(--border);
    box-shadow: var(--shadow), inset 0 0 30px rgba(255, 0, 255, 0.02);
}
```

### 5. Sidebar Destaque

```css
[data-theme="cyberpunk"] .sidebar {
    border-right: 1px solid rgba(255, 0, 255, 0.2);
    box-shadow: 2px 0 20px rgba(255, 0, 255, 0.08);
}
[data-theme="cyberpunk"] .sidebar h2 {
    text-shadow: 0 0 15px rgba(255, 0, 255, 0.5);
}
[data-theme="cyberpunk"] .sidebar nav a:hover {
    text-shadow: 0 0 8px rgba(255, 0, 255, 0.4);
}
```

### 6. Inputs com Borda Neon no Foco

```css
[data-theme="cyberpunk"] input:focus,
[data-theme="cyberpunk"] select:focus,
[data-theme="cyberpunk"] textarea:focus {
    outline: none;
    border-color: #ff00ff;
    box-shadow: 0 0 10px rgba(255, 0, 255, 0.3);
}
```

### 7. Toggle Switch Customizado

```css
[data-theme="cyberpunk"] .toggle-slider::before {
    background-color: #ff00ff;
    box-shadow: 0 0 8px rgba(255, 0, 255, 0.6);
}
```

## Como o Sistema de Temas Funciona

### Fluxo

```
1. Usuario clica no botao de toggle na sidebar
       ↓
2. POST /theme/toggle (com campo hidden "next" = URL atual)
       ↓
3. Rota le session['theme'] → se 'cyberpunk' vira 'default', senao vira 'cyberpunk'
       ↓
4. Redirect 302 de volta para a URL original
       ↓
5. base.html le session.get('theme', 'default')
       ↓
6. Se 'cyberpunk' → <body data-theme="cyberpunk">
7. CSS [data-theme="cyberpunk"] aplica override de variaveis + efeitos
```

### Persistencia

- Armazenado em `session['theme']` (cookie Flask assinado com SECRET_KEY)
- **Nao expira** enquanto o cookie existir (∼31 dias default do Flask)
- Sobrevive a login/logout (a session nao e limpa no logout via Flask-Login padrao)
- Se o usuario limpar cookies do navegador, volta ao tema default
- **Sem migracao de banco de dados** — zero impacto no schema SQLite

### Vantagens desta Abordagem

- Zero linhas de JavaScript necessarias (form POST puro)
- Funciona antes mesmo de login (pagina de login tambem recebe o tema)
- Sem cookies extras — usa a infra de session existente
- Sem migracao de schema

## Arquivos Modificados

### 1. `app/__init__.py` — Configuracao de sessao

Adicionar permanencia a sessao para que o tema sobreviva alem do fechamento do navegador:

```python
from datetime import timedelta

app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)
```

### 2. `app/routes.py` — Nova rota de toggle

```python
@routes_bp.route("/theme/toggle", methods=["POST"])
def theme_toggle():
    from flask import session
    current = session.get("theme", "default")
    session["theme"] = "cyberpunk" if current == "default" else "default"
    session.permanent = True
    next_url = request.form.get("next", request.referrer or url_for("routes.dashboard"))
    return redirect(next_url)
```

Nota: esta rota **nao tem `@login_required`** — funciona mesmo em paginas publicas.

### 3. `app/templates/base.html` — Atributo data-theme + CSS cyberpunk + toggle button

**3a. Atributo no `<body>`:**

```html
<body class="{% block body_class %}{% endblock %}"
      data-theme="{{ session.get('theme', 'default') }}">
```

**3b. Bloco CSS cyberpunk** (dentro da tag `<style>`, antes do `</style>`):

Adicionar todo o bloco `[data-theme="cyberpunk"]` com:
- Override das 15 variaveis
- Efeitos visuais (scanlines, glow, bordas, etc.)
- Ajustes de rgba derivados (alerts, badges, table hover)

**3c. Botao toggle na sidebar** (apos o `</nav>`, antes do `</aside>`):

```html
<div class="theme-toggle">
    <form method="POST" action="/theme/toggle">
        <input type="hidden" name="next" value="{{ request.path }}">
        <button type="submit" class="theme-toggle-btn"
                title="Alternar tema">
            {% if session.get('theme') == 'cyberpunk' %}
                &#9760; <!-- skull symbol -->
            {% else %}
                &#9881; <!-- gear symbol -->
            {% endif %}
        </button>
    </form>
</div>
```

**3d. CSS do botao toggle:**

```css
.theme-toggle {
    position: absolute;
    bottom: 16px;
    left: 0;
    right: 0;
    text-align: center;
    padding: 8px 0;
    border-top: 1px solid var(--border);
}
.theme-toggle-btn {
    background: none;
    border: 1px solid var(--border);
    color: var(--muted);
    font-size: 20px;
    padding: 6px 16px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    transition: var(--transition);
}
.theme-toggle-btn:hover {
    color: var(--red);
    border-color: var(--red);
    box-shadow: 0 0 12px rgba(255, 0, 255, 0.15);
}
[data-theme="cyberpunk"] .theme-toggle-btn:hover {
    box-shadow: 0 0 15px rgba(255, 0, 255, 0.3);
}
```

### 4. `app/auth.py` — Preservar tema no login/logout

Nao precisa de alteracao — a session Flask **nao e limpa** pelo `login_user()` nem pelo `logout_user()`. O cookie de sessao mantem o campo `theme` intacto.

**Unica verificacao:** `logout_user()` do Flask-Login apenas remove o user_id da sessao, nao limpa a sessao inteira. O campo `theme` persiste. Sem alteracao necessaria.

## Estrutura do CSS no base.html

O arquivo `base.html` vai crescer significativamente (~+200 linhas). Para manter organizacao, usar comentarios de secao:

```
/* ============================================
   THEME: Default Dark (variaveis no :root)
   ============================================ */
:root { ... }

/* ============================================
   Estilos base (compartilhados entre temas)
   ============================================ */
body { ... }
...

/* ============================================
   THEME: Cyberpunk
   ============================================ */
[data-theme="cyberpunk"] {
    /* variaveis */
}
[data-theme="cyberpunk"] .card { ... }
[data-theme="cyberpunk"] .btn-primary { ... }
...

/* ============================================
   Tema Default — ajustes de rgba derivados
   (permanecem como estao atualmente)
   ============================================ */

/* ============================================
   Responsivo
   ============================================ */
@media ...
```

## Ajustes de Cores Derivadas (rgba)

As cores `rgba()` usadas em alerts, badges e outros elementos precisam ser ajustadas
para o tema cyberpunk. Exemplos:

| Elemento | Default | Cyberpunk |
|---|---|---|
| Table row hover | `rgba(233,69,96,0.05)` | `rgba(255,0,255,0.05)` |
| Alert error bg | `rgba(233,69,96,0.15)` | `rgba(255,0,255,0.12)` |
| Badge success bg | `rgba(46,204,113,0.2)` | `rgba(0,255,204,0.15)` |
| Badge info bg | `rgba(15,52,96,0.5)` | `rgba(45,27,105,0.5)` |
| Badge muted (nova) | — | `rgba(106,106,159,0.2)` |

## Pagina de Login no Modo Cyberpunk

A tela de login (`login.html`) tambem recebe o tema cyberpunk porque o `data-theme`
esta no `<body>` do `base.html`. Ajustes especificos:

```css
[data-theme="cyberpunk"] .login-box {
    border: 1px solid rgba(255, 0, 255, 0.2);
    box-shadow: 0 0 30px rgba(255, 0, 255, 0.15);
}
[data-theme="cyberpunk"] .login-box h2 {
    text-shadow: 0 0 15px rgba(255, 0, 255, 0.5);
}
```

## Testes

### Novos testes: `tests/test_theme.py`

| Teste | Descricao |
|---|---|
| `test_theme_default_on_first_visit` | Sem cookie de sessao → `data-theme="default"` |
| `test_theme_toggle_to_cyberpunk` | POST `/theme/toggle` → `session['theme'] = 'cyberpunk'` |
| `test_theme_toggle_back_to_default` | POST 2x → volta a `'default'` |
| `test_theme_persists_across_pages` | Define cyberpunk → navega para `/prompts` → ainda cyberpunk |
| `test_theme_applied_in_html` | Resposta contem `data-theme="cyberpunk"` no `<body>` |
| `test_theme_login_page_has_toggle` | GET `/auth/login` → contem `data-theme` no body |
| `test_theme_redirect_back` | POST com `next=/prompts` → redirect para `/prompts` |
| `test_theme_no_login_required` | Sem login → POST `/theme/toggle` → 302 (nao 401) |

### Atualizar: `tests/test_routes.py`

Adicionar `_login` / `_logout` no `setUp` para garantir estado limpo.

## Ordem de Implementacao

1. **`app/__init__.py`** — `PERMANENT_SESSION_LIFETIME = 30 days`
2. **`app/routes.py`** — Nova rota `POST /theme/toggle`
3. **`app/templates/base.html`** — 3 mudancas:
   a. `data-theme` no `<body>`
   b. Bloco `[data-theme="cyberpunk"]` de ~200 linhas CSS
   c. Botao toggle na sidebar com CSS
4. **`tests/test_theme.py`** — 8 novos testes
5. **Rodar `./run_tests.sh`** — validar tudo
6. **Teste visual** — subir a app, clicar no toggle, verificar todas as paginas

## Notas

- **Scanlines**: O pseudo-elemento `::after` com `pointer-events: none` garante que
  nao interfere com cliques. Impacto de performance e desprezivel (CSS puro, sem JS).
- **Acessibilidade**: O tema cyberpunk mantem contraste adequado. Texto `#e0e8ff` sobre
  fundo `#0c0c1d` tem ratio de contraste ~12:1 (excede WCAG AAA).
- **Tamanho do CSS**: O arquivo base.html cresce ~200 linhas. Total estimado: ~750 linhas.
  Dentro do aceitavel para CSS inline (sem HTTP request extra).
- **Compatibilidade**: `data-theme` attribute selector funciona em todos os browsers modernos
  (IE11+, Chrome 7+, Firefox 6+, Safari 5.1+). `repeating-linear-gradient` tem suporte amplo.
- **Botao toggle responsivo**: No mobile, o botao fica visivel no footer da sidebar quando
  ela esta aberta (overlay). Funciona igual ao resto da sidebar.
