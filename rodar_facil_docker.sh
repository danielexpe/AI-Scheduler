#!/bin/bash
set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

banner() {
    echo ""
    echo -e "${CYAN}============================================${NC}"
    echo -e "${CYAN}  AI Mail Scheduler - Deploy Docker         ${NC}"
    echo -e "${CYAN}============================================${NC}"
    echo ""
}

check_docker() {
    if ! command -v docker &>/dev/null; then
        echo -e "${RED}Docker nao encontrado. Instale primeiro:${NC}"
        echo "  curl -fsSL https://get.docker.com | bash"
        echo "  sudo usermod -aG docker \$USER"
        exit 1
    fi

    if ! docker compose version &>/dev/null; then
        echo -e "${RED}Docker Compose nao encontrado.${NC}"
        echo "  Deve vir com Docker 24+. Verifique com: docker compose version"
        exit 1
    fi

    if ! docker info &>/dev/null; then
        echo -e "${RED}Docker nao esta rodando ou voce nao tem permissao.${NC}"
        echo "  Tente: sudo systemctl start docker"
        echo "  Ou adicione seu usuario ao grupo docker: sudo usermod -aG docker \$USER"
        exit 1
    fi

    echo -e "${GREEN}Docker: $(docker --version)${NC}"
    echo -e "${GREEN}Compose: $(docker compose version 2>&1 | head -1)${NC}"
}

setup_env() {
    if [ ! -f ".env" ]; then
        if [ -f ".env.example" ]; then
            cp .env.example .env
            echo -e "${YELLOW}Arquivo .env criado a partir de .env.example${NC}"
        else
            echo -e "${RED}Arquivo .env.example nao encontrado.${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}.env ja existe${NC}"
    fi

    echo ""
    echo -e "${BOLD}Verifique as configuracoes no .env:${NC}"
    echo ""

    local has_issues=0

    if grep -q "sk-xxxxxxxxxxxxxxxx" .env 2>/dev/null; then
        echo -e "  ${RED}[PENDENTE] DEEPSEEK_API_KEY nao configurada${NC}"
        has_issues=1
    else
        echo -e "  ${GREEN}[OK] DEEPSEEK_API_KEY${NC}"
    fi

    if grep -q "seuemail@gmail.com" .env 2>/dev/null || grep -q "xxxxxxxxxxxxxxxx" .env 2>/dev/null; then
        echo -e "  ${RED}[PENDENTE] GMAIL_USER ou GMAIL_APP_PASSWORD nao configurados${NC}"
        has_issues=1
    else
        echo -e "  ${GREEN}[OK] GMAIL_USER / GMAIL_APP_PASSWORD${NC}"
    fi

    if grep -q "change_me" .env 2>/dev/null; then
        echo -e "  ${RED}[PENDENTE] SECRET_KEY ainda eh o valor padrao${NC}"
        has_issues=1
    else
        echo -e "  ${GREEN}[OK] SECRET_KEY${NC}"
    fi

    if [ "$has_issues" -eq 1 ]; then
        echo ""
        echo -e "${YELLOW}Edite o arquivo .env com suas credenciais:${NC}"
        echo -e "  ${BOLD}nano .env${NC}"
        echo ""
        echo -e "  - Obtenha DEEPSEEK_API_KEY em: https://platform.deepseek.com"
        echo -e "  - GMAIL_APP_PASSWORD: https://myaccount.google.com/security > Senhas de app"
        echo -e "  - SECRET_KEY: gere com: python3 -c \"import secrets; print(secrets.token_hex(32))\""
        echo ""
        read -rp "Pressione ENTER apos configurar o .env (ou Ctrl+C para cancelar)... "
    fi
}

create_dirs() {
    mkdir -p data/backups
    echo -e "${GREEN}Diretorio data/ criado${NC}"
}

deploy() {
    echo ""
    echo -e "${CYAN}--- Build das imagens ---${NC}"
    docker compose build --pull

    echo ""
    echo -e "${CYAN}--- Parando containers antigos (se existirem) ---${NC}"
    docker compose down --remove-orphans 2>/dev/null || true

    echo ""
    echo -e "${CYAN}--- Iniciando containers ---${NC}"
    docker compose up -d

    echo ""
    echo -e "${CYAN}--- Aguardando healthcheck ---${NC}"
    local attempts=0
    local max_attempts=30
    while [ $attempts -lt $max_attempts ]; do
        if docker compose ps 2>/dev/null | grep -q "(healthy)"; then
            echo -e "${GREEN}Containers saudaveis!${NC}"
            break
        fi
        sleep 2
        attempts=$((attempts + 1))
        echo -n "."
    done
    echo ""

    if [ $attempts -ge $max_attempts ]; then
        echo -e "${RED}Timeout aguardando healthcheck. Verifique os logs:${NC}"
        echo "  docker compose logs"
    fi
}

show_status() {
    echo ""
    echo -e "${CYAN}--- Status ---${NC}"
    docker compose ps

    echo ""
    local ip=$(hostname -I 2>/dev/null | awk '{print $1}')
    [ -z "$ip" ] && ip="localhost"

    local port=$(grep -oP 'APP_PORT=\K\d+' .env 2>/dev/null || echo "5000")
    local url="http://${ip}:${port}"

    echo -e "${GREEN}============================================${NC}"
    echo -e "${GREEN}  Deploy concluido!${NC}"
    echo -e "${GREEN}  Acesse: ${BOLD}${url}${NC}"
    echo -e "${GREEN}  Registre seu primeiro usuario na pagina.${NC}"
    echo -e "${GREEN}============================================${NC}"
    echo ""
    echo -e "${CYAN}Comandos uteis:${NC}"
    echo -e "  ${BOLD}docker compose ps${NC}              # Status dos containers"
    echo -e "  ${BOLD}docker compose logs -f${NC}         # Ver logs"
    echo -e "  ${BOLD}docker compose logs cron -f${NC}    # Logs do cron"
    echo -e "  ${BOLD}docker compose restart${NC}         # Reiniciar servicos"
    echo -e "  ${BOLD}docker compose down${NC}            # Parar tudo (dados mantidos)"
    echo -e "  ${BOLD}docker compose up -d --build${NC}   # Rebuild e restart"
    echo ""
}

main() {
    banner
    check_docker
    setup_env
    create_dirs
    deploy
    show_status
}

main
