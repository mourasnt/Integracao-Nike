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

  # Retry loop to make migrations resilient to transient DB errors or race conditions
  MAX_RETRIES=${DB_MIGRATE_RETRIES:-5}
  ATTEMPT=1
  until alembic upgrade head; do
    RC=$?
    echo "alembic upgrade failed with exit code ${RC} (attempt ${ATTEMPT}/${MAX_RETRIES})"
    if [ "${ATTEMPT}" -ge "${MAX_RETRIES}" ]; then
      echo "Migration failed after ${ATTEMPT} attempts, aborting startup."
      exit 1
    fi
    ATTEMPT=$((ATTEMPT+1))
    sleep 2
  done

  # After successful migration, verify required columns exist (to avoid silent partial migrations)
  REQUIRED_COLUMNS=${DB_REQUIRED_COLUMNS:-"tomador_nDoc tomador_xNome rem_xLgr dest_xLgr recebedor_nDoc et_origem"}
  # Export to make it available to the embedded Python check
  export DB_REQUIRED_COLUMNS="${REQUIRED_COLUMNS}"
  ATTEMPT=1
  until python - <<PYTHON
import os, sys, urllib.parse, psycopg2

url = os.environ.get('DATABASE_URL')
if not url:
    print('No DATABASE_URL set', file=sys.stderr)
    sys.exit(1)

u = urllib.parse.urlparse(url)
user = u.username
password = u.password
host = u.hostname
port = u.port or 5432
dbname = u.path.lstrip('/')

req_str = os.environ.get('DB_REQUIRED_COLUMNS', '')
req = req_str.split() if req_str else []
print('Post-migration: checking required columns ->', req, file=sys.stderr)
try:
    conn = psycopg2.connect(host=host, port=port, user=user, password=password, dbname=dbname)
    cur = conn.cursor()
    if not req:
        print('No required columns configured, skipping check', file=sys.stderr)
        cur.close()
        conn.close()
        sys.exit(0)
    cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='shipments' AND column_name = ANY(%s)", (req,))
    found = {r[0] for r in cur.fetchall()}
    missing = [c for c in req if c not in found]
    if missing:
        print('Missing columns after migration:', missing, file=sys.stderr)
        print('Found columns:', sorted(found), file=sys.stderr)
        sys.exit(2)
    print('All required columns present')
    cur.close()
    conn.close()
    sys.exit(0)
except Exception as e:
    print('Error checking columns:', e, file=sys.stderr)
    sys.exit(3)
PYTHON
  do
    RC=$?
    echo "Post-migration check failed with exit code ${RC} (attempt ${ATTEMPT}/${MAX_RETRIES})"
    if [ "${ATTEMPT}" -ge "${MAX_RETRIES}" ]; then
      echo "Post-migration verification failed after ${ATTEMPT} attempts, aborting startup."
      exit 1
    fi
    ATTEMPT=$((ATTEMPT+1))
    sleep 2
  done
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

# Cria usuário para o cliente do FRONT se as variáveis existirem
if [ -n "$CLIENT_FRONT_USER" ] && [ -n "$CLIENT_FRONT_PASSWORD" ] && [ -f scripts/create_user.py ]; then
  echo "Creating initial API key for user $CLIENT_FRONT_USER..."
  python scripts/create_user.py "$CLIENT_FRONT_USER" "$CLIENT_FRONT_PASSWORD"
fi

# =================================================================================
# 4. Iniciar Aplicação
# =================================================================================
echo "Starting Uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload