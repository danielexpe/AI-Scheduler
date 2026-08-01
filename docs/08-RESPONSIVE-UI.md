# Plano: Interface Responsiva + Modernizada

## Decisões de Design

| Decisão | Escolha |
|---------|---------|
| Sidebar mobile | Hamburger overlay (ícone ☰ no topo, menu desliza sobre o conteúdo) |
| Tabelas mobile | Cards stacked (cada linha vira um card vertical com label: valor) |
| Breakpoint | 768px (mobile abaixo, desktop acima) |
| Visual | Responsivo + modernizado (transições, sombras, micro-interações, mantendo tema escuro) |

---

## 1. Análise do Estado Atual

### 1.1 Problemas de Responsividade

| Problema | Local | Impacto |
|----------|-------|---------|
| Sidebar fixa com `width: 220px` e `position: fixed` | `base.html` | Ocupa espaço fixo em mobile, sem collapse |
| `margin-left: 220px` hardcoded no main | `base.html` | Conteúdo espremido em telas < 768px |
| Zero `@media` queries em todo o CSS | Todos os templates | Nenhum ajuste para mobile |
| Tabelas com 7 colunas sem scroll ou adaptação | `logs/list.html`, `schedules/list.html` | Overflow horizontal, quebra layout |
| `min-width: 360px` no modal | `base.html` | Estoura em smartphones 320px |
| Botões de ação múltiplos em células estreitas | `schedules/list.html`, `prompts/list.html` | Não cabem lado a lado em mobile |
| Cron builder com `flex-wrap` mas `min-width: 80px` | `schedules/create.html` | Campos muito pequenos para dedos |
| CSS duplicado entre `login.html` e `base.html` | Ambos | Manutenção duplicada |

### 1.2 Templates Afetados (9 arquivos)

| Template | Principal desafio mobile |
|----------|-------------------------|
| `base.html` | Sidebar, header, CSS global, modal |
| `login.html` | Padding e espaçamento em telas pequenas |
| `dashboard.html` | Stats grid, tabela de últimas execuções |
| `prompts/list.html` | Tabela → cards, botões de ação |
| `prompts/create.html` | Formulário em tela estreita |
| `prompts/edit.html` | Idem create |
| `schedules/list.html` | Tabela com 7 colunas → cards, toggle |
| `schedules/create.html` | Cron builder (5 campos lado a lado) |
| `schedules/edit.html` | Idem create |
| `logs/list.html` | Tabela com 7 colunas → cards |
| `cron_status.html` | Tabela de entradas do crontab |

---

## 2. Arquitetura CSS — Nova Estrutura

### 2.1 Objetivo

Centralizar TODO o CSS em `base.html` (inclusive o da página de login) usando `{% block extra_css %}` e duas seções no `<style>`:

1. **CSS Global** — variáveis, reset, componentes compartilhados, media queries
2. **CSS Específico de Página** — injetado via block (login, etc.)

### 2.2 Variáveis CSS (manter + adicionar)

```css
:root {
    /* Existentes (manter) */
    --bg: #1a1a2e;
    --card: #16213e;
    --accent: #0f3460;
    --text: #e0e0e0;
    --muted: #a0a0b0;
    --red: #e94560;
    --green: #2ecc71;
    --yellow: #f39c12;
    --border: #2a2a4a;

    /* Novas */
    --radius: 8px;
    --radius-sm: 6px;
    --shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.4);
    --transition: 0.25s ease;
    --sidebar-width: 220px;
    --header-height: 56px;
}
```

### 2.3 Media Queries — Estratégia de Breakpoints

```
Mobile First: estilos base são mobile, @media min-width: 768px adiciona desktop

@media (max-width: 767px) { ... }   // Apenas mobile (ajustes finos quando necessário)
@media (min-width: 768px) { ... }   // Desktop (sidebar visível, tabelas normais, etc.)
@media (max-width: 400px)  { ... }   // Smartphones pequenos (ajustes extras de font-size)
```

---

## 3. Template por Template — O Que Muda

### 3.1 `base.html` — Layout Global (maior impacto)

#### Sidebar → Hamburger Overlay

**Comportamento:**
- **Desktop (≥768px):** sidebar fixa na esquerda (220px), sempre visível, sem ícone hamburger
- **Mobile (<768px):**
  - Sidebar fica oculta (`translateX(-100%)`)
  - Header ganha botão hamburger (☰) no canto esquerdo
  - Overlay escuro (`rgba(0,0,0,0.5)`) cobre o fundo
  - Ao tocar ☰: sidebar desliza da esquerda com transição suave + overlay aparece
  - Ao tocar overlay ou link: sidebar fecha
  - `main` ocupa 100% da largura (sem margin-left)

**HTML adicional no base.html:**
```html
<!-- Botão hamburger (visível só em mobile) -->
<button class="hamburger" onclick="toggleSidebar()" aria-label="Menu">
    <span></span><span></span><span></span>
</button>

<!-- Overlay (visível só quando sidebar aberta) -->
<div class="sidebar-overlay" onclick="closeSidebar()"></div>
```

**JS adicionado no base.html:**
```js
function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
    document.querySelector('.sidebar-overlay').classList.toggle('active');
}
function closeSidebar() {
    document.querySelector('.sidebar').classList.remove('open');
    document.querySelector('.sidebar-overlay').classList.remove('active');
}
// Fecha sidebar ao clicar em qualquer link do menu
document.querySelectorAll('.sidebar nav a').forEach(link => {
    link.addEventListener('click', closeSidebar);
});
```

#### Header — Ajustes mobile

- Desktop: mantém atual (título à esquerda, user-info à direita)
- Mobile: título menor (18px), user-info simplificado (só username + link Sair)

#### CSS do Hamburger

```css
.hamburger {
    display: none;
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    flex-direction: column;
    gap: 4px;
    z-index: 200;
}
.hamburger span {
    display: block;
    width: 22px;
    height: 2px;
    background: var(--text);
    border-radius: 2px;
    transition: var(--transition);
}
.sidebar.open .hamburger span:nth-child(1) { /* animação X */ }
.sidebar.open .hamburger span:nth-child(2) { opacity: 0; }
.sidebar.open .hamburger span:nth-child(3) { /* animação X */ }
```

#### Modal

```css
.modal {
    min-width: unset;
    width: 90%;
    max-width: 400px;
    margin: 0 16px;
}
```

#### Tabelas → Responsivas

```css
/* Wrapper para scroll em mobile (fallback para telas que não usam cards) */
.table-wrapper {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
}

/* Em mobile, esconder tabela e mostrar cards */
@media (max-width: 767px) {
    table.responsive thead { display: none; }
    table.responsive tbody,
    table.responsive tr,
    table.responsive td { display: block; }
    table.responsive tr {
        background: var(--card);
        border: 1px solid var(--border);
        border-radius: var(--radius);
        margin-bottom: 12px;
        padding: 12px;
    }
    table.responsive td {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border: none;
        font-size: 13px;
    }
    table.responsive td::before {
        content: attr(data-label);
        font-size: 11px;
        color: var(--muted);
        text-transform: uppercase;
        font-weight: 600;
        margin-right: 10px;
        white-space: nowrap;
    }
}
```

**IMPORTANTE:** Cada `<td>` precisa de `data-label` com o nome da coluna para o pseudo-elemento `::before` funcionar. Exemplo:

```html
<td data-label="Título">{{ prompt.title }}</td>
<td data-label="Tom">{{ prompt.tone }}</td>
<td data-label="Ações">
    <!-- botões -->
</td>
```

Isso precisa ser adicionado em TODAS as tabelas de todos os templates.

#### Animações e Sombras (modernização)

```css
/* Sombra nos cards */
.card { box-shadow: var(--shadow); }

/* Hover nos cards interativos */
.card:hover { box-shadow: var(--shadow-lg); }

/* Transição suave na sidebar */
.sidebar { transition: transform var(--transition), box-shadow var(--transition); }

/* Transição nos links do menu */
.sidebar nav a { transition: background var(--transition), color var(--transition), padding-left var(--transition); }
.sidebar nav a:hover { padding-left: 24px; }

/* Fade-in nas páginas */
.main { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(6px); } to { opacity: 1; transform: translateY(0); } }

/* Transição nos botões */
.btn { transition: opacity var(--transition), transform var(--transition), box-shadow var(--transition); }
.btn:hover { transform: translateY(-1px); box-shadow: var(--shadow); }
.btn:active { transform: translateY(0); }

/* Pulse no badge de status */
.badge-success { animation: pulse 2s infinite; }
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

/* Overlay com transição */
.sidebar-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.5);
    z-index: 98;
    transition: opacity var(--transition);
    opacity: 0;
}
.sidebar-overlay.active {
    display: block;
    opacity: 1;
}
```

---

### 3.2 `dashboard.html`

| Elemento | Desktop | Mobile (<768px) |
|----------|---------|-----------------|
| Stats grid | 4 colunas | 2 colunas |
| Tabela logs | Tabela normal | Cards stacked |
| Botões inferiores | 3 lado a lado | Empilhados verticalmente |

**Ajustes:**
- `data-label` nos `<td>` da tabela de logs
- Classe `responsive` na `<table>`
- Flex-direction column nos botões no mobile

---

### 3.3 `prompts/list.html`

| Elemento | Desktop | Mobile (<768px) |
|----------|---------|-----------------|
| Toolbar | "N prompt(s)" à esquerda, botão à direita | Stack vertical |
| Tabela | 5 colunas: Título, Tom, Ativo, Criado, Ações | Cards stacked |
| Ações | 3 botões lado a lado | Botões em linha com ícones + labels |

**Ajustes:**
- `data-label` nos `<td>`
- Classe `responsive` na `<table>`
- CSS para `.actions` em mobile: `display: flex; flex-wrap: wrap; gap: 4px;`

---

### 3.4 `prompts/create.html` + `prompts/edit.html`

| Elemento | Desktop | Mobile |
|----------|---------|--------|
| Card max-width | 700px | 100% |
| Botões Salvar/Cancelar | Lado a lado | Stack vertical (Salvar primeiro, full width) |

---

### 3.5 `schedules/list.html`

| Elemento | Desktop | Mobile |
|----------|---------|--------|
| Toolbar | Contador à esquerda, botões à direita | Stack vertical |
| Tabela | 7 colunas | Cards stacked |
| Toggle switch | Funciona igual | Funciona igual (já é touch-friendly) |

**Maior desafio:** 7 colunas. Cards vão empilhar os campos como label:valor.

---

### 3.6 `schedules/create.html` + `schedules/edit.html`

| Elemento | Desktop | Mobile |
|----------|---------|--------|
| Cron builder | 5 campos em linha (flex) | 2-3 campos por linha (`flex-basis: calc(50% - 5px)`) |

**CSS para cron builder mobile:**
```css
@media (max-width: 767px) {
    .cron-builder .form-group {
        flex: 1 1 calc(50% - 5px);
        min-width: unset;
    }
}
```

---

### 3.7 `logs/list.html`

| Elemento | Desktop | Mobile |
|----------|---------|--------|
| Tabela | 7 colunas | Cards stacked |

Similar a schedules/list.html. `data-label` em todos os `<td>`.

---

### 3.8 `cron_status.html`

| Elemento | Desktop | Mobile |
|----------|---------|--------|
| Toolbar | Contador + botão lado a lado | Stack vertical |
| Tabela | 4 colunas | Cards stacked |

---

### 3.9 `login.html`

**Estratégia:** Centralizar CSS no `base.html`, e `login.html` estende `base.html`.

**Mudança de arquitetura:**
- Criar `base.html` com bloco `{% block body_class %}{% endblock %}` no `<body>`
- `login.html` estende `base.html`, seta `body_class` = `login-page`
- CSS específico do login em `extra_css` ou via classe `login-page` no body
- Remove duplicação completa de CSS do login.html

---

## 4. Resumo de Mudanças por Arquivo

### 4.1 Arquivos com mudanças pesadas

| Arquivo | Mudanças |
|---------|----------|
| `base.html` | Hamburger menu, overlay, sidebar animada, modal responsivo, regras de tabela mobile, fade-in, sombras, transições, CSS do login |
| `login.html` | Simplificar: estender base.html, só HTML do form, remover CSS duplicado |
| `schedules/list.html` | data-labels, classe responsive na table, toolbar mobile |
| `logs/list.html` | data-labels, classe responsive na table |
| `prompts/list.html` | data-labels, classe responsive na table, toolbar mobile |

### 4.2 Arquivos com mudanças leves

| Arquivo | Mudanças |
|----------|----------|
| `dashboard.html` | data-labels, flex-wrap nos botões inferiores |
| `prompts/create.html` | Ajuste max-width, botões empilhados mobile |
| `prompts/edit.html` | Idem create |
| `schedules/create.html` | Cron builder flex ajuste mobile |
| `schedules/edit.html` | Idem create |
| `cron_status.html` | data-labels, classe responsive |

---

## 5. Ordem de Implementação

1. **`base.html`** — Adicionar hamburger, overlay, JS toggle, media queries, transições, sombras, fade-in, tabelas responsive, bloco `extra_css`, bloco `body_class`
2. **`login.html`** — Reescrever para estender base.html, remover CSS duplicado
3. **`dashboard.html`** — `data-label` na tabela, ajustes mobile grid
4. **`prompts/list.html`** — `data-label`, classe `responsive`, toolbar
5. **`prompts/create.html` + `edit.html`** — Botões empilhados
6. **`schedules/list.html`** — `data-label`, classe `responsive`, toolbar
7. **`schedules/create.html` + `edit.html`** — Cron builder mobile
8. **`logs/list.html`** — `data-label`, classe `responsive`
9. **`cron_status.html`** — `data-label`, classe `responsive`

---

## 6. Testes de Responsividade

### 6.1 Checklist por Breakpoint

**Mobile Pequeno (320px — iPhone SE)**
- [ ] Sidebar hamburger abre/fecha corretamente
- [ ] Overlay cobre toda a tela
- [ ] Nenhum overflow horizontal
- [ ] Form inputs não estouram
- [ ] Modal cabe na tela
- [ ] Botões full-width nos formulários

**Mobile Médio (375-414px — iPhone X/12/14)**
- [ ] Stats grid 2 colunas bem distribuído
- [ ] Cards de tabela com labels alinhados
- [ ] Cron builder com campos em 2 colunas

**Tablet (768px)**
- [ ] Sidebar já aparece fixa (não hamburger)
- [ ] Tabelas já aparecem normais (não cards)
- [ ] Stats 4 colunas

**Desktop (1024px+)**
- [ ] Layout idêntico ao atual (mas com sombras/animações)
- [ ] Sidebar fixa, hover nos links

### 6.2 Teste Cross-browser

- [ ] Chrome/Chromium (Android + Desktop)
- [ ] Firefox (Desktop)
- [ ] Safari (iOS)
- [ ] `-webkit-overflow-scrolling: touch` para scroll suave em iOS

---

## 7. Notas Técnicas

- Todo CSS permanece inline no `<style>` (sem arquivos .css externos, sem build tools)
- JS permanece inline no final do `<body>` (sem arquivos .js externos)
- Nenhuma nova dependência adicionada
- `python-crontab`, `flask-login`, etc. não são afetados — mudanças são apenas nos templates
- Zero alterações no backend (routes.py, models.py, etc.)
- Testes existentes (`test_routes.py`, `test_integration.py`) devem continuar passando sem alterações, pois testam HTML de resposta e não CSS
