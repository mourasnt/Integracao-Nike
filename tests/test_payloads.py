import pytest
import requests
import copy
import re
from datetime import datetime

# ==============================================================================
# CONFIGURAÇÕES E CONSTANTES
# ==============================================================================
BASE_URL = "http://127.0.0.1:8282"
AUTH_URL = f"{BASE_URL}/autenticacao"
EMISSAO_URL = f"{BASE_URL}/emissao"

# Credenciais (Devem existir no seu banco de dados local para o teste funcionar)
USUARIO_VALIDO = "09098221000380"
SENHA_VALIDA = "JpY7HMVz2tMQeF04pxmTaMT09DtQyG"

# ==============================================================================
# FIXTURES (PREPARAÇÃO DO AMBIENTE)
# ==============================================================================

@pytest.fixture(scope="session")
def auth_token():
    """Realiza login uma vez e retorna o Access Key para usar nos testes."""
    payload = {"usuario": USUARIO_VALIDO, "senha": SENHA_VALIDA}
    response = requests.post(AUTH_URL, json=payload)
    
    if response.status_code != 200:
        pytest.fail(f"Falha crítica no Setup: Não foi possível autenticar. {response.text}")
    
    data = response.json()
    # Ensure 'data' object is present and not null
    payload_data = data.get("data")
    if not payload_data or not isinstance(payload_data, dict):
        pytest.fail(f"Falha crítica: resposta de autenticação inválida. Esperado 'data' com access_key, obtido: {data}")
    token = payload_data.get("access_key")
    if not token:
        pytest.fail(f"Token não encontrado na resposta de autenticação. Resposta: {data}")
    return token

@pytest.fixture
def headers(auth_token):
    return {
        "Authorization": f"Bearer {auth_token}",
        "Content-Type": "application/json"
    }

@pytest.fixture
def golden_payload():
    """
    Retorna um payload COMPLETO e VÁLIDO conforme documentação (Páginas 8, 9, 10, 11).
    Este é o modelo 'Dourado' que será sabotado pelos testes de erro.
    """
    return {
        "documentos": [
            {
                # Estrutura Minuta
                "minuta": {
                    "toma": "CNPJ_TOMADOR",
                    "nDocEmit": "CNPJ_EMISSOR",
                    "dEmi": "2024-04-03",
                    "cServ": 1, # Inteiro conforme doc
                    "cTab": "TABELA_PADRAO",
                    "tpEmi": 1, # Inteiro
                    "cStatus": 1, # Inteiro
                    "cAut": "ROMANEIO_123",
                    "carga": {
                        "pBru": "10.500", # String conforme doc
                        "pCub": "2.100",  # String
                        "qVol": "5",      # String
                        "vTot": "1500.00",# String
                        "cOrigCalc": "3550308",
                        "cDestCalc": "3304557"
                    }
                },
                # Estrutura Remetente
                "rem": {
                    "nDoc": "11111111000111",
                    "IE": "ISENTO",
                    "cFiscal": 1, # Inteiro
                    "xNome": "REMETENTE EXEMPLO LTDA",
                    "xFant": "REMETENTE FANTASIA",
                    "xLgr": "RUA TESTE",
                    "nro": "100",
                    "xBairro": "CENTRO",
                    "cMun": "3550308",
                    "CEP": "01001000",
                    "cPais": 1058
                },
                # Estrutura Destinatário
                "dest": {
                    "nDoc": "22222222000122",
                    "IE": "ISENTO",
                    "cFiscal": 2, # Inteiro
                    "xNome": "DESTINATARIO EXEMPLO SA",
                    "xFant": "DESTINATARIO FANTASIA",
                    "xLgr": "AVENIDA PAULISTA",
                    "nro": "1000",
                    "xCpl": "SALA 1", # Opcional na lógica, mas obrigatório na doc tabela
                    "xBairro": "BELA VISTA",
                    "cMun": "3550308",
                    "CEP": "01310000",
                    "cPais": 1058,
                    "nFone": "1199999999", # String
                    "email": "teste@email.com"
                },
                # Tomador
                "toma": {
                     "nDoc": "11111111000111",
                     "IE": "ISENTO",
                     "cFiscal": 1,
                     "xNome": "TOMADOR PAGADOR",
                     "xFant": "TOMADOR",
                     "xLgr": "RUA PAGADOR",
                     "nro": "50",
                     "xCpl": "",
                     "xBairro": "FINANCEIRO",
                     "cMun": "3550308",
                     "CEP": "01001000",
                     "cPais": 1058,
                     "nFone": "1188888888",
                     "email": "fin@teste.com"
                },
                # Recebedor (Local de entrega)
                "receb": {
                    "nDoc": "22222222000122",
                    "IE": "ISENTO",
                    "cFiscal": 2,
                    "xNome": "RECEBEDOR LOGISTICO",
                    "xFant": "CD 01",
                    "xLgr": "ESTRADA DO CD",
                    "nro": "500",
                    "xCpl": "GALPAO 3",
                    "xBairro": "INDUSTRIAL",
                    "cMun": "3550308",
                    "CEP": "06000000",
                    "cPais": 1058,
                    "nFone": "1177777777",
                    "email": "cd@teste.com"
                },
                # Array de Notas Fiscais
                "documentos": [
                    {
                        "nPed": "PED12345",
                        "serie": "1",
                        "nDoc": "55555",
                        "dEmi": "2024-04-01",
                        "vBC": "100.00",
                        "vICMS": "18.00",
                        "vBCST": "0.00",
                        "vST": "0.00",
                        "vProd": "1000.00",
                        "vNF": "1200.00", # String conforme doc
                        "nCFOP": "5102",
                        "pBru": "10.500",
                        "qVol": "5",
                        "chave": "35240411111111000111550010000555551000000001", # 44 digitos
                        "tpDoc": "NFE",
                        "xEsp": "VOLUMES",
                        "xNat": "VENDA"
                        # CT-e é opcional, não incluído no payload padrão
                    }
                ]
            }
        ]
    }

# ==============================================================================
# 1. TESTES DE AUTENTICAÇÃO (/autenticacao)
# ==============================================================================

def test_auth_sucesso():
    """[AUT-01] Testa login com credenciais válidas."""
    payload = {"usuario": USUARIO_VALIDO, "senha": SENHA_VALIDA}
    resp = requests.post(AUTH_URL, json=payload)
    
    assert resp.status_code == 200
    data = resp.json()
    
    # [cite_start]Validações baseadas na doc [cite: 67]
    assert data['status'] == 1
    assert data['message'] == "OK"
    assert "access_key" in data['data']
    assert "expire_at" in data['data']

def test_auth_formato_data():
    """[AUT-02] Valida se a data de expiração segue estritamente AAAA-MM-DDTHH:MM:SS-HH-MM."""
    payload = {"usuario": USUARIO_VALIDO, "senha": SENHA_VALIDA}
    resp = requests.post(AUTH_URL, json=payload)
    expire_at = resp.json()['data']['expire_at']
    
    # Regex para: 2023-07-17T18:13:16-03:00 ou -03-00 (doc pede hífen no fuso)
    # [cite_start]A doc diz: "AAAA-MM-DDTHH:MM:SS-HH-MM" [cite: 67]
    padrao = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-\d{2}[-:]\d{2}$"
    assert re.match(padrao, expire_at), f"Formato de data inválido: {expire_at}"

def test_auth_credenciais_invalidas():
    """[AUT-03] Testa login com senha errada."""
    payload = {"usuario": USUARIO_VALIDO, "senha": "errada"}
    resp = requests.post(AUTH_URL, json=payload)
    
    # A doc sugere 401 ou 200 com status 0
    if resp.status_code == 200:
        assert resp.json()['status'] == 0
    else:
        assert resp.status_code == 401

@pytest.mark.parametrize("campo", ["usuario", "senha"])
def test_auth_campos_faltantes(campo):
    """[AUT-04] Testa payload incompleto."""
    payload = {"usuario": USUARIO_VALIDO, "senha": SENHA_VALIDA}
    del payload[campo]
    resp = requests.post(AUTH_URL, json=payload)
    # Deve retornar erro 400 ou 422
    assert resp.status_code in [400, 422]

# ==============================================================================
# 2. TESTES DE EMISSÃO - CENÁRIOS MASSIVOS (/emissao)
# ==============================================================================

def test_emissao_happy_path(headers, golden_payload):
    """[EMI-01] Testa o fluxo perfeito com payload completo."""
    resp = requests.post(EMISSAO_URL, json=golden_payload, headers=headers)
    
    # Debug se falhar
    if resp.status_code != 200:
        print(f"Erro Happy Path: {resp.text}")

    assert resp.status_code in [200, 201]
    data = resp.json()
    
    # [cite_start]Validações de resposta [cite: 204]
    assert data['status'] == 1
    assert data['message'] == "Documento gerado no sistema"
    assert isinstance(data['data'], list)
    assert len(data['data']) > 0
    assert data['data'][0]['status'] == 1
    assert isinstance(data['data'][0]['id'], int)

# --- GERADOR DE CENÁRIOS DE ERRO ---

def gerar_cenarios_campos():
    """
    Gera dinamicamente cenários de teste para remover campos obrigatórios
    ou enviar tipos incorretos.
    Retorna lista de tuplas: (nome_teste, funcao_modificadora)
    """
    cenarios = []
    
    # [cite_start]1. CAMPOS OBRIGATÓRIOS DA MINUTA [cite: 170]
    campos_minuta = ["toma", "nDocEmit", "dEmi", "cServ", "cTab", "tpEmi", "cStatus", "cAut", "carga"]
    for campo in campos_minuta:
        # Cenário: Remover campo obrigatório
        cenarios.append((
            f"Minuta: faltando '{campo}'",
            lambda p, c=campo: p['documentos'][0]['minuta'].pop(c)
        ))
        # Cenário: Enviar vazio (se for string)
        cenarios.append((
            f"Minuta: '{campo}' vazio",
            lambda p, c=campo: p['documentos'][0]['minuta'].update({c: ""})
        ))

    # [cite_start]2. CAMPOS OBRIGATÓRIOS DA CARGA [cite: 170]
    campos_carga = ["pBru", "pCub", "qVol", "vTot", "cOrigCalc", "cDestCalc"]
    for campo in campos_carga:
        cenarios.append((
            f"Carga: faltando '{campo}'",
            lambda p, c=campo: p['documentos'][0]['minuta']['carga'].pop(c)
        ))

    # [cite_start]3. CAMPOS OBRIGATÓRIOS DE ATORES (Rem, Dest, Toma, Receb) [cite: 175, 180]
    # Todos compartilham estrutura similar
    atores = ["rem", "dest", "toma", "receb"]
    campos_ator = ["nDoc", "IE", "cFiscal", "xNome", "xFant", "xLgr", "nro", "xBairro", "cMun", "CEP", "cPais"]
    
    for ator in atores:
        for campo in campos_ator:
            cenarios.append((
                f"{ator.upper()}: faltando '{campo}'",
                lambda p, a=ator, c=campo: p['documentos'][0][a].pop(c)
            ))

    # [cite_start]4. CAMPOS OBRIGATÓRIOS DAS NOTAS FISCAIS [cite: 180]
    campos_nf = ["serie", "nDoc", "dEmi", "vBC", "vICMS", "vBCST", "vST", "vProd", "vNF", "nCFOP", "pBru", "qVol", "chave", "tpDoc", "xEsp", "xNat"]
    for campo in campos_nf:
        cenarios.append((
            f"Nota Fiscal: faltando '{campo}'",
            lambda p, c=campo: p['documentos'][0]['documentos'][0].pop(c)
        ))

    # 5. TESTES DE TIPO (Inteiro vs String)
    # [cite_start]Minuta.cServ deve ser Inteiro [cite: 170]
    cenarios.append((
        "Tipo Inválido: cServ string",
        lambda p: p['documentos'][0]['minuta'].update({"cServ": "TEXTO"})
    ))
    # Minuta.dEmi deve ser data string YYYY-MM-DD
    cenarios.append((
        "Formato Inválido: dEmi BR",
        lambda p: p['documentos'][0]['minuta'].update({"dEmi": "03/04/2024"})
    ))
    # [cite_start]Carga.pBru deve ser String (apesar de ser peso) [cite: 170]
    cenarios.append((
        "Tipo Inválido: pBru float",
        lambda p: p['documentos'][0]['minuta']['carga'].update({"pBru": 10.5})
    ))

    return cenarios

# --- EXECUÇÃO DOS CENÁRIOS PARAMETRIZADOS ---

@pytest.mark.parametrize("nome_cenario, modificador", gerar_cenarios_campos())
def test_emissao_cenarios_negativos(headers, golden_payload, nome_cenario, modificador):
    """
    Executa centenas de testes de validação.
    Cada iteração pega o payload perfeito, estraga um campo específico e verifica se a API rejeita.
    """
    payload = copy.deepcopy(golden_payload)
    
    # Aplica a modificação (ex: remover campo)
    try:
        modificador(payload)
    except KeyError:
        pytest.skip("Campo não encontrado na estrutura do payload para este teste.")

    resp = requests.post(EMISSAO_URL, json=payload, headers=headers)
    
    # ASSERTIVAS
    # A API deve retornar status: 0 no JSON ou HTTP 400/422
    
    if resp.status_code == 200:
        data = resp.json()
        
        # Pode ser erro global ou erro no item
        erro_global = (data.get('status') == 0)
        
        erro_item = False
        if 'data' in data and isinstance(data['data'], list) and len(data['data']) > 0:
            if data['data'][0].get('status') == 0:
                erro_item = True
        
        if not (erro_global or erro_item):
            pytest.fail(f"FALHA ({nome_cenario}): API aceitou payload inválido com status 1. Resp: {data}")

    elif resp.status_code in [400, 422]:
        # Sucesso no teste (API rejeitou dado inválido)
        pass
    else:
        pytest.fail(f"FALHA ({nome_cenario}): Código HTTP inesperado {resp.status_code}. Resp: {resp.text}")

# ==============================================================================
# 3. TESTES DE SEGURANÇA NA EMISSÃO
# ==============================================================================

def test_emissao_sem_token(golden_payload):
    """[SEC-01] Tentar emitir sem header Authorization."""
    resp = requests.post(EMISSAO_URL, json=golden_payload) # Sem headers
    assert resp.status_code in [401, 403]

def test_emissao_token_invalido(golden_payload):
    """[SEC-02] Tentar emitir com token falso."""
    headers_fake = {"Authorization": "Bearer TOKEN_FALSO_123", "Content-Type": "application/json"}
    resp = requests.post(EMISSAO_URL, json=golden_payload, headers=headers_fake)
    assert resp.status_code in [401, 403]

# ==============================================================================
# 4. TESTES DE ESTRUTURA GERAL
# ==============================================================================

def test_payload_vazio(headers):
    """Enviar JSON vazio."""
    resp = requests.post(EMISSAO_URL, json={}, headers=headers)
    assert resp.status_code in [400, 422]

def test_lista_documentos_vazia(headers, golden_payload):
    """Enviar array 'documentos' vazio."""
    golden_payload['documentos'] = []
    resp = requests.post(EMISSAO_URL, json=golden_payload, headers=headers)
    
    # Dependendo da regra, pode ser sucesso (nada a processar) ou erro.
    # Assumindo que deve processar sem erro (200) mas status pode variar
    assert resp.status_code in [200, 201]

def test_chave_tamanho_incorreto(headers, golden_payload):
    """Testa regra de negócio: Chave deve ter 44 dígitos."""
    golden_payload['documentos'][0]['documentos'][0]['chave'] = "123" # Muito curta
    resp = requests.post(EMISSAO_URL, json=golden_payload, headers=headers)
    
    # Deve constar como erro
    data = resp.json()
    if resp.status_code == 200:
        # Verifica se o item específico deu erro
        assert data['data'][0]['status'] == 0
    else:
        assert resp.status_code in [400, 422]