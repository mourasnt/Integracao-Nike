#!/bin/sh
set -e

# Garante que o pacote da aplicação seja importável
if [ -z "$PYTHONPATH" ]; then
  export PYTHONPATH=/code
fi

# =================================================================================
# 1. Aguardar o Banco de Dados (Postgres)
# =================================================================================
if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database..."
  
  # Loop simples em Python para testar conexão TCP
  # Adicionei prints de erro para ajudar a debugar o motivo da falha
  while ! python - <<PYTHON
import os, sys, socket, urllib.parse

try:
    url = os.environ.get('DATABASE_URL')
    if not url: 
        print("Debug: No DATABASE_URL set", file=sys.stderr)
        sys.exit(0) # Skip wait if no URL
        
    if '://' not in url:
        print("Debug: DATABASE_URL format invalid (missing ://)", file=sys.stderr)
        sys.exit(0) # Skip wait if invalid format

    result = urllib.parse.urlparse(url)
    host = result.hostname
    port = result.port or 5432
    
    if not host:
        print("Debug: No hostname found in DATABASE_URL", file=sys.stderr)
        sys.exit(0)

    # Tenta conectar
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    sock.connect((host, int(port)))
    sock.close()
    sys.exit(0)
except Exception as e:
    # Imprime o erro para o log para sabermos O QUE está falhando
    # (ex: DNS error, Connection Refused, etc)
    print(f"Debug: Connection failed to {host}:{port} - {e}", file=sys.stderr)
    sys.exit(1)
PYTHON
  do
    echo "DB not ready yet, sleeping 1s..."
    sleep 1
  done
  echo "Database is ready!"
fi

# =================================================================================
# 2. Criar Tabelas (Migrações)
# =================================================================================
# Roda as migrações para criar tabelas se não existirem (ou atualizar se necessário)
if command -v alembic >/dev/null 2>&1; then
  echo "Running database migrations..."
  alembic upgrade head
fi

# =================================================================================
# 3. Scripts de Inicialização (Usuários e Chaves)
# =================================================================================

# Cria usuário inicial se as variáveis existirem
if [ -n "$INITIAL_USER" ] && [ -n "$INITIAL_PASSWORD" ] && [ -f scripts/create_user.py ]; then
  echo "Creating initial user $INITIAL_USER..."
  python scripts/create_user.py "$INITIAL_USER" "$INITIAL_PASSWORD"
fi

# Cria usuário para o cliente da API se as variáveis existirem
if [ -n "$CLIENT_USER" ] && [ -n "$CLIENT_PASSWORD" ] && [ -f scripts/create_user.py ]; then
  echo "Creating initial API key for user $CLIENT_USER..."
  python scripts/create_user.py "$CLIENT_USER" "$CLIENT_PASSWORD"
fi

# =================================================================================
# 4. Iniciar Aplicação
# =================================================================================
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload