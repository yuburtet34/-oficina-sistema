"""
SISTEMA OFICINA - Servidor Principal
Rode com: python servidor.py
Acesse em: http://localhost:8000
"""

import json
import sqlite3
import os
import re
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

from fastapi import FastAPI, HTTPException, Request, Depends, Cookie, Depends, Cookie, Depends, Cookie
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, RedirectResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import hashlib
import secrets
import hashlib
import secrets
import hashlib
import secrets

# ── Configuração ──────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
import os as _os
DB_PATH  = Path(_os.environ.get("DB_PATH", str(BASE_DIR / "db" / "oficina.db")))
(BASE_DIR / "db").mkdir(parents=True, exist_ok=True)
app      = FastAPI(title="Sistema Oficina")

# ── Banco de dados ────────────────────────────────────────────
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

import hashlib 
import secrets 
def hash_senha(s): import hashlib; return hashlib.sha256(s.encode()).hexdigest() 
def get_usuario_atual(t=None): 
    if not t: return None 
    with get_db() as db: 
        q="SELECT u.* FROM sessoes s JOIN usuarios u ON u.id=s.usuario_id WHERE s.token=? AND s.expira_em>datetime('now','localtime')" 
        row=db.execute(q,(t,)).fetchone() 
        return dict(row) if row else None 
def exigir_login(t=None): 
    u=get_usuario_atual(t) 
    if not u: raise HTTPException(401,"Nao autenticado") 
    return u 
def exigir_admin(t=None): 
    u=exigir_login(t) 
    if u["perfil"]!="admin": raise HTTPException(403,"Acesso restrito") 
    return u 
def criar_admin_padrao(): 
    with get_db() as db: 
        if db.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]==0: 
            for u,s,n,p in [("admin1","admin123","Administrador 1","admin"),("admin2","admin123","Administrador 2","admin"),("func1","func123","Funcionario 1","funcionario"),("func2","func123","Funcionario 2","funcionario"),("func3","func123","Funcionario 3","funcionario"),("func4","func123","Funcionario 4","funcionario")]: 
                db.execute("INSERT INTO usuarios (usuario,senha_hash,nome,perfil) VALUES (?,?,?,?)",(u,hash_senha(s),n,p)) 
            print("USUARIOS CRIADOS!") 

def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(exist_ok=True)
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS clientes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                nome        TEXT,
                razao_social TEXT,
                cpf         TEXT,
                cnpj        TEXT,
                telefone    TEXT,
                email       TEXT,
                endereco    TEXT,
                cidade      TEXT,
                estado      TEXT,
                observacoes TEXT,
                criado_em   TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS veiculos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                placa       TEXT UNIQUE,
                modelo      TEXT,
                cliente_id  INTEGER REFERENCES clientes(id),
                cor         TEXT,
                ano         TEXT,
                observacoes TEXT,
                criado_em   TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS produtos (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo      TEXT,
                nome        TEXT NOT NULL,
                valor_venda REAL DEFAULT 0,
                qt_estoque  REAL DEFAULT 0,
                qt_minima   REAL DEFAULT 0,
                observacao  TEXT,
                atualizado_em TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS ordens_servico (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                numero          INTEGER UNIQUE,
                data            TEXT DEFAULT (date('now','localtime')),
                status          TEXT DEFAULT 'ABERTA',
                cliente_nome    TEXT,
                cliente_id      INTEGER REFERENCES clientes(id),
                veiculo_placa   TEXT,
                veiculo_modelo  TEXT,
                veiculo_id      INTEGER REFERENCES veiculos(id),
                tipo_negociacao TEXT DEFAULT 'Ordem de Serviço',
                forma_pagamento TEXT,
                valor_bruto     REAL DEFAULT 0,
                desconto        REAL DEFAULT 0,
                valor_liquido   REAL DEFAULT 0,
                observacoes         TEXT,
                nota_fiscal         TEXT,
                email_cliente       TEXT,
                telefone_cliente    TEXT,
                criado_em           TEXT DEFAULT (datetime('now','localtime')),
                fechado_em          TEXT
            );

            CREATE TABLE IF NOT EXISTS itens_os (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                os_id           INTEGER REFERENCES ordens_servico(id),
                produto_servico TEXT NOT NULL,
                tipo_item       TEXT DEFAULT 'Serviço',
                unidade         TEXT DEFAULT 'UN',
                quantidade      REAL DEFAULT 1,
                valor_unitario  REAL DEFAULT 0,
                desconto        REAL DEFAULT 0,
                valor_total     REAL DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS os_midias (
                id        INTEGER PRIMARY KEY AUTOINCREMENT,
                os_id     INTEGER REFERENCES ordens_servico(id),
                nome      TEXT,
                tipo      TEXT,
                dados     BLOB,
                criado_em TEXT DEFAULT (datetime('now','localtime'))
            );

            CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha_hash TEXT NOT NULL, nome TEXT, perfil TEXT DEFAULT 'funcionario', ativo INTEGER DEFAULT 1, criado_em TEXT DEFAULT (datetime('now','localtime')));CREATE TABLE IF NOT EXISTS sessoes (token TEXT PRIMARY KEY, usuario_id INTEGER REFERENCES usuarios(id), criado_em TEXT DEFAULT (datetime('now','localtime')), expira_em TEXT);CREATE TABLE IF NOT EXISTS usuarios (id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT UNIQUE NOT NULL, senha_hash TEXT NOT NULL, nome TEXT, perfil TEXT DEFAULT 'funcionario', ativo INTEGER DEFAULT 1);
            CREATE TABLE IF NOT EXISTS sessoes (token TEXT PRIMARY KEY, usuario_id INTEGER, expira_em TEXT);
            CREATE INDEX IF NOT EXISTS idx_os_placa    ON ordens_servico(veiculo_placa);
            CREATE INDEX IF NOT EXISTS idx_os_cliente  ON ordens_servico(cliente_nome);
            CREATE INDEX IF NOT EXISTS idx_os_status   ON ordens_servico(status);
            CREATE INDEX IF NOT EXISTS idx_os_data     ON ordens_servico(data);
            CREATE INDEX IF NOT EXISTS idx_veiculo_placa ON veiculos(placa);
        """)
    print("✅ Banco de dados iniciado")
    criar_admin_padrao()

# ── Importação do backup ──────────────────────────────────────
def importar_backup():
    arquivos = [
        BASE_DIR / "backup_1_clientes_produtos.json",
        BASE_DIR / "backup_2_veiculos.json",
        BASE_DIR / "backup_3_vendas_os.json",
        BASE_DIR / "backup_4_orcamentos.json",
    ]
    existentes = [a for a in arquivos if a.exists()]
    if not existentes:
        print("⚠️  Nenhum arquivo de backup encontrado. Iniciando banco vazio.")
        return

    print(f"📂 Importando {len(existentes)} arquivo(s) de backup...")

    with get_db() as db:
        # Verifica se já importou
        total = db.execute("SELECT COUNT(*) FROM ordens_servico").fetchone()[0]
        if total > 0:
            print(f"ℹ️  Banco já possui {total} OS. Pulando importação.")
            return

        # --- CLIENTES ---
        f1 = BASE_DIR / "backup_1_clientes_produtos.json"
        if f1.exists():
            data = json.loads(f1.read_text(encoding="utf-8"))
            clientes_map = {}
            # Aceita tanto 'clientes' (backup antigo) quanto 'pessoas' (backup v3)
            lista_c = data.get("clientes") or data.get("pessoas") or []
            for c in lista_c:
                nome = (c.get("nome") or c.get("razao_social") or "").strip()
                if not nome:
                    continue
                cur = db.execute("""
                    INSERT INTO clientes (nome, razao_social, cpf, cnpj, telefone, email, cidade, estado, observacoes)
                    VALUES (?,?,?,?,?,?,?,?,?)
                """, (nome, c.get("razao_social"), c.get("cpf") or c.get("cpf_cnpj"),
                      c.get("cnpj") or c.get("cpf_cnpj"),
                      c.get("telefone"), c.get("email"), c.get("cidade"),
                      c.get("estado"), c.get("observacoes")))
                clientes_map[nome.upper()] = cur.lastrowid

            # --- PRODUTOS ---
            for p in data.get("produtos", []):
                if not p.get("nome"):
                    continue
                try:
                    qt = float(str(p.get("qt_estoque") or 0).replace(",", "."))
                except:
                    qt = 0
                db.execute("""
                    INSERT INTO produtos (codigo, nome, valor_venda, qt_estoque, qt_minima, observacao)
                    VALUES (?,?,?,?,?,?)
                """, (p.get("codigo"), p["nome"], p.get("valor_venda", 0),
                      qt, 0, p.get("observacao")))
            print(f"   ✅ {len(lista_c)} clientes | {len(data.get('produtos',[]))} produtos")

        # --- VEÍCULOS ---
        f2 = BASE_DIR / "backup_2_veiculos.json"
        veiculos_map = {}
        if f2.exists():
            data2 = json.loads(f2.read_text(encoding="utf-8"))
            for v in data2.get("veiculos", []):
                if not v.get("placa"):
                    continue
                cur = db.execute("""
                    INSERT OR IGNORE INTO veiculos (placa, modelo) VALUES (?,?)
                """, (v["placa"], v.get("modelo")))
                veiculos_map[v["placa"]] = cur.lastrowid or db.execute(
                    "SELECT id FROM veiculos WHERE placa=?", (v["placa"],)).fetchone()[0]
            print(f"   ✅ {len(data2.get('veiculos',[]))} veículos")

        # --- VENDAS / OS ---
        f3 = BASE_DIR / "backup_3_vendas_os.json"
        if f3.exists():
            data3 = json.loads(f3.read_text(encoding="utf-8"))
            os_count = 0
            # Descobre o maior número de OS existente para sequência
            for v in data3.get("vendas_os", []):
                num    = v.get("numero_venda")
                placa  = v.get("veiculo", {}).get("placa")
                modelo = v.get("veiculo", {}).get("modelo")
                cliente_nome = (v.get("cliente_raw") or "").strip()
                # Remove placa/modelo do nome do cliente se estiver junto
                if placa and placa in cliente_nome:
                    cliente_nome = cliente_nome.replace(placa, "").strip(" -–")
                if modelo and cliente_nome.startswith(modelo):
                    cliente_nome = cliente_nome[len(modelo):].strip(" -–")

                # Suporta backup antigo e v3
                valor  = v.get("valor_liquido") or v.get("valor_total") or 0
                bruto  = v.get("valor_bruto")   or v.get("valor_total") or 0
                desc   = v.get("desconto_total") or v.get("valor_desconto") or 0
                status = v.get("status_override_aplicado") or ("CANCELADA" if v.get("data_cancelamento") else "FECHADA")
                cur = db.execute("""
                    INSERT OR IGNORE INTO ordens_servico
                    (numero, data, status, cliente_nome, veiculo_placa, veiculo_modelo,
                     tipo_negociacao, forma_pagamento, valor_bruto, desconto, valor_liquido,
                     nota_fiscal, observacoes)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (num, v.get("data"), status, cliente_nome or v.get("cliente_raw"),
                      placa, modelo, v.get("tipo_negociacao"), v.get("forma_pagamento"),
                      round(float(bruto or 0), 2), round(float(desc or 0), 2),
                      round(float(valor or 0), 2),
                      v.get("nota_fiscal") or v.get("numero_nf"),
                      v.get("observacoes")))

                os_id = cur.lastrowid
                if os_id:
                    for item in v.get("itens", []):
                        db.execute("""
                            INSERT INTO itens_os
                            (os_id, produto_servico, tipo_item, unidade, quantidade,
                             valor_unitario, desconto, valor_total)
                            VALUES (?,?,?,?,?,?,?,?)
                        """, (os_id, item.get("produto_servico"), item.get("tipo_item", "Serviço"),
                              item.get("unidade", "UN"), item.get("quantidade", 1),
                              item.get("valor_unitario", 0), item.get("desconto", 0),
                              item.get("valor_total_item", 0)))
                    os_count += 1
            print(f"   ✅ {os_count} ordens de serviço importadas")

    print("✅ Importação concluída!")

# ── API - Dashboard ───────────────────────────────────────────
@app.get("/api/dashboard")
def dashboard():
    with get_db() as db:
        hoje = datetime.now().strftime("%Y-%m-%d")
        mes  = datetime.now().strftime("%Y-%m")
        return {
            "os_abertas":    db.execute("SELECT COUNT(*) FROM ordens_servico WHERE status='ABERTA'").fetchone()[0],
            "os_hoje":       db.execute("SELECT COUNT(*) FROM ordens_servico WHERE data=?", (hoje,)).fetchone()[0],
            "faturamento_mes": db.execute("SELECT COALESCE(SUM(valor_liquido),0) FROM ordens_servico WHERE strftime('%Y-%m',data)=? AND status='FECHADA'", (mes,)).fetchone()[0],
            "total_clientes":  db.execute("SELECT COUNT(*) FROM clientes").fetchone()[0],
            "total_veiculos":  db.execute("SELECT COUNT(*) FROM veiculos").fetchone()[0],
            "total_os":        db.execute("SELECT COUNT(*) FROM ordens_servico").fetchone()[0],
            "estoque_baixo":   db.execute("SELECT COUNT(*) FROM produtos WHERE qt_estoque <= qt_minima AND qt_minima > 0").fetchone()[0],
            "os_recentes":   [dict(r) for r in db.execute("""
                SELECT numero, data, cliente_nome, veiculo_placa, veiculo_modelo,
                       valor_liquido, status, forma_pagamento
                FROM ordens_servico ORDER BY id DESC LIMIT 20
            """).fetchall()],
        }

# ── API - Ordens de Serviço ───────────────────────────────────
@app.get("/api/os")
def listar_os(busca: str = "", status: str = "", mes: str = "", de: str = "", ate: str = "", limit: int = 50, offset: int = 0):
    with get_db() as db:
        where, params = ["1=1"], []
        if busca:
            where.append("(cliente_nome LIKE ? OR veiculo_placa LIKE ? OR veiculo_modelo LIKE ? OR CAST(numero AS TEXT) LIKE ?)")
            b = f"%{busca}%"
            params += [b, b, b, b]
        if status:
            where.append("status=?")
            params.append(status)
        if mes:
            where.append("strftime('%%Y-%%m',data)=?")
            params.append(mes)
        sql = f"SELECT * FROM ordens_servico WHERE {' AND '.join(where)} ORDER BY id DESC LIMIT ? OFFSET ?"
        rows = db.execute(sql, params + [limit, offset]).fetchall()
        total = db.execute(f"SELECT COUNT(*) FROM ordens_servico WHERE {' AND '.join(where)}", params).fetchone()[0]
        return {"total": total, "items": [dict(r) for r in rows]}

@app.get("/api/os/{os_id}")
def detalhe_os(os_id: int):
    with get_db() as db:
        os = db.execute("SELECT * FROM ordens_servico WHERE id=?", (os_id,)).fetchone()
        if not os:
            raise HTTPException(404, "OS não encontrada")
        itens = db.execute("SELECT * FROM itens_os WHERE os_id=?", (os_id,)).fetchall()
        return {**dict(os), "itens": [dict(i) for i in itens]}

@app.post("/api/os")
async def criar_os(req: Request):
    body = await req.json()
    with get_db() as db:
        # Próximo número de OS
        max_num = db.execute("SELECT COALESCE(MAX(numero),0) FROM ordens_servico").fetchone()[0]
        numero  = max_num + 1

        itens = body.pop("itens", [])
        valor_bruto   = sum(i.get("quantidade", 1) * i.get("valor_unitario", 0) for i in itens)
        desconto      = sum(i.get("desconto", 0) for i in itens)
        valor_liquido = valor_bruto - desconto

        cur = db.execute("""
            INSERT INTO ordens_servico
            (numero, data, status, cliente_nome, veiculo_placa, veiculo_modelo,
             tipo_negociacao, forma_pagamento, valor_bruto, desconto, valor_liquido, observacoes)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
        """, (numero, body.get("data", datetime.now().strftime("%d/%m/%Y")),
              body.get("status", "ABERTA"), body.get("cliente_nome"),
              body.get("veiculo_placa", "").upper(), body.get("veiculo_modelo"),
              body.get("tipo_negociacao", "Ordem de Serviço"),
              body.get("forma_pagamento"), round(valor_bruto, 2),
              round(desconto, 2), round(valor_liquido, 2), body.get("observacoes")))
        os_id = cur.lastrowid

        for item in itens:
            vt = item.get("quantidade", 1) * item.get("valor_unitario", 0) - item.get("desconto", 0)
            db.execute("""
                INSERT INTO itens_os (os_id, produto_servico, tipo_item, unidade, quantidade, valor_unitario, desconto, valor_total)
                VALUES (?,?,?,?,?,?,?,?)
            """, (os_id, item["produto_servico"], item.get("tipo_item", "Serviço"),
                  item.get("unidade", "UN"), item.get("quantidade", 1),
                  item.get("valor_unitario", 0), item.get("desconto", 0), round(vt, 2)))

        # Garante veículo cadastrado
        placa = body.get("veiculo_placa", "").upper()
        if placa:
            db.execute("INSERT OR IGNORE INTO veiculos (placa, modelo) VALUES (?,?)",
                       (placa, body.get("veiculo_modelo")))

        return {"id": os_id, "numero": numero}

@app.put("/api/os/{os_id}")
async def atualizar_os(os_id: int, req: Request):
    body = await req.json()
    with get_db() as db:
        itens = body.pop("itens", None)
        if itens is not None:
            valor_bruto   = sum(i.get("quantidade", 1) * i.get("valor_unitario", 0) for i in itens)
            desconto      = sum(i.get("desconto", 0) for i in itens)
            valor_liquido = valor_bruto - desconto
            body.update({"valor_bruto": round(valor_bruto, 2),
                         "desconto":    round(desconto, 2),
                         "valor_liquido": round(valor_liquido, 2)})
            if "email_cliente" not in body:
                body["email_cliente"] = None
            if "telefone_cliente" not in body:
                body["telefone_cliente"] = None
            if body.get("status") == "FECHADA":
                body["fechado_em"] = datetime.now().isoformat()
            db.execute("DELETE FROM itens_os WHERE os_id=?", (os_id,))
            for item in itens:
                vt = item.get("quantidade", 1) * item.get("valor_unitario", 0) - item.get("desconto", 0)
                db.execute("""
                    INSERT INTO itens_os (os_id, produto_servico, tipo_item, unidade, quantidade, valor_unitario, desconto, valor_total)
                    VALUES (?,?,?,?,?,?,?,?)
                """, (os_id, item["produto_servico"], item.get("tipo_item", "Serviço"),
                      item.get("unidade", "UN"), item.get("quantidade", 1),
                      item.get("valor_unitario", 0), item.get("desconto", 0), round(vt, 2)))

        sets   = ", ".join(f"{k}=?" for k in body)
        values = list(body.values()) + [os_id]
        db.execute(f"UPDATE ordens_servico SET {sets} WHERE id=?", values)
        return {"ok": True}

# ── API - Veículos ────────────────────────────────────────────
@app.get("/api/veiculos/buscar")
def buscar_veiculos(q: str = ""):
    q = q.upper().strip()
    if not q or len(q) < 2:
        return []
    with get_db() as db:
        rows = db.execute("""
            SELECT DISTINCT veiculo_placa, veiculo_modelo,
                   COUNT(*) as total_os
            FROM ordens_servico
            WHERE veiculo_placa LIKE ? OR veiculo_modelo LIKE ?
            GROUP BY veiculo_placa
            ORDER BY total_os DESC
            LIMIT 10
        """, (f"{q}%", f"%{q}%")).fetchall()
        return [dict(r) for r in rows]

# ── API - Clientes ────────────────────────────────────────────
@app.get("/api/veiculos/{placa}")
def historico_veiculo(placa: str):
    placa = placa.upper().replace("-", "")
    with get_db() as db:
        veiculo = db.execute("SELECT * FROM veiculos WHERE placa=?", (placa,)).fetchone()
        os_list = db.execute("""
            SELECT id, numero, data, status, cliente_nome, valor_liquido, forma_pagamento,
                   tipo_negociacao
            FROM ordens_servico WHERE veiculo_placa=? ORDER BY id DESC
        """, (placa,)).fetchall()
        return {
            "veiculo": dict(veiculo) if veiculo else {"placa": placa},
            "total_os": len(os_list),
            "valor_total": sum(r["valor_liquido"] for r in os_list),
            "historico": [dict(r) for r in os_list]
        }

# ── API - Mídias (fotos/vídeos) ──────────────────────────────
@app.post("/api/os/{os_id}/midias")
async def upload_midia(os_id: int, req: Request):
    import base64
    body = await req.json()
    nome  = body.get("nome", "arquivo")
    tipo  = body.get("tipo", "image/jpeg")
    dados = body.get("dados", "")
    with get_db() as db:
        db.execute("INSERT INTO os_midias (os_id, nome, tipo, dados) VALUES (?,?,?,?)",
                   (os_id, nome, tipo, dados))
    return {"ok": True}

@app.get("/api/os/{os_id}/midias")
def listar_midias(os_id: int):
    with get_db() as db:
        rows = db.execute("SELECT id, nome, tipo, dados, criado_em FROM os_midias WHERE os_id=? ORDER BY id", (os_id,)).fetchall()
        return [dict(r) for r in rows]

@app.delete("/api/midias/{midia_id}")
def deletar_midia(midia_id: int):
    with get_db() as db:
        db.execute("DELETE FROM os_midias WHERE id=?", (midia_id,))
    return {"ok": True}

# ── API - Autocomplete veículos ──────────────────────────────
@app.get("/api/clientes")
def listar_clientes(busca: str = "", limit: int = 30):
    with get_db() as db:
        if busca:
            rows = db.execute("""
                SELECT * FROM clientes WHERE nome LIKE ? OR telefone LIKE ? OR cpf LIKE ? OR cnpj LIKE ?
                ORDER BY nome LIMIT ?
            """, (f"%{busca}%", f"%{busca}%", f"%{busca}%", f"%{busca}%", limit)).fetchall()
        else:
            rows = db.execute("SELECT * FROM clientes ORDER BY nome LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# ── API - Produtos ────────────────────────────────────────────
@app.get("/api/produtos")
def listar_produtos(busca: str = "", limit: int = 50):
    with get_db() as db:
        if busca:
            rows = db.execute("""
                SELECT * FROM produtos WHERE nome LIKE ? OR codigo LIKE ?
                ORDER BY nome LIMIT ?
            """, (f"%{busca}%", f"%{busca}%", limit)).fetchall()
        else:
            rows = db.execute("SELECT * FROM produtos ORDER BY nome LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]

# ── Frontend ──────────────────────────────────────────────────
# endpoints de login 
@app.post("/api/login") 
async def login(req: Request): 
    body=await req.json() 
    with get_db() as db: 
        row=db.execute("SELECT * FROM usuarios WHERE usuario=? AND ativo=1",(body.get("usuario",""),)).fetchone() 
        if not row or row["senha_hash"]!=hash_senha(body.get("senha","")): raise HTTPException(401,"Usuario ou senha invalidos") 
        import secrets 
        token=secrets.token_hex(32) 
        db.execute("INSERT INTO sessoes (token,usuario_id,expira_em) VALUES (?,?,datetime('now','localtime','+7 days'))",(token,row["id"])) 
        resp=JSONResponse({"ok":True,"nome":row["nome"],"perfil":row["perfil"]}) 
        resp.set_cookie("session_token",token,httponly=True,max_age=604800,samesite="none",secure=True) 
        return resp 
@app.post("/api/logout") 
def logout(session_token: str=Cookie(None)): 
    if session_token: 
        with get_db() as db: db.execute("DELETE FROM sessoes WHERE token=?",(session_token,)) 
    resp=JSONResponse({"ok":True}) 
    resp.delete_cookie("session_token") 
    return resp 
@app.get("/api/me")
def me(session_token: str=Cookie(None)):
    user=get_usuario_atual(session_token) 
    if not user: raise HTTPException(401,"Nao autenticado") 
    return {"nome":user["nome"],"usuario":user["usuario"],"perfil":user["perfil"]} 
@app.get("/api/usuarios")
def listar_usuarios(session_token: str=Cookie(None)): 
    exigir_admin(session_token) 
    with get_db() as db: 
        rows=db.execute("SELECT id,usuario,nome,perfil,ativo FROM usuarios ORDER BY id").fetchall() 
        return [dict(r) for r in rows] 

@app.get("/", response_class=HTMLResponse)
def frontend():
    return Path(BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

@app.get("/{path:path}", response_class=HTMLResponse)
def spa(path: str):
    f = BASE_DIR / "static" / path
    if f.exists():
        return f.read_text(encoding="utf-8")
    return Path(BASE_DIR / "static" / "index.html").read_text(encoding="utf-8")

# ── Inicialização ─────────────────────────────────────────────
if __name__ == "__main__":
    import socket
    init_db()
    importar_backup()
    # Descobre IP local
    try:
        ip = socket.gethostbyname(socket.gethostname())
    except:
        ip = "localhost"
    print(f"""
╔══════════════════════════════════════════════════╗
║         SISTEMA OFICINA - RODANDO ✅             ║
╠══════════════════════════════════════════════════╣
║  Acesso local:   http://localhost:8000           ║
║  Acesso na rede: http://{ip}:8000  ║
║                                                  ║
║  Para parar: pressione CTRL+C                    ║
╚══════════════════════════════════════════════════╝
""")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")# endpoints de login 

