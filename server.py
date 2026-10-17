import os, json, sqlite3, secrets, hashlib, hmac, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from http.cookies import SimpleCookie

DB = os.getenv('DATABASE_PATH', 'data/imperial.db')
MODULES = {'citizens','legion','mages','diplomacy','treaties','treasury','supplies','decrees','summons'}
ROLES = ['Administrador','Rei','Jarl de Solitude','General','Capitão','Tenente','Legionário','Mago de Batalha','Emissário','Aprendiz de Emissário','Tesoureiro','Cidadão']
GRANTS = {'General': {'legion','mages','diplomacy','treaties','summons'}, 'Capitão': {'legion','summons'}, 'Mago de Batalha': {'mages'}, 'Emissário': {'diplomacy','treaties'}, 'Tesoureiro': {'treasury','supplies'}}

def connect():
    con = sqlite3.connect(DB); con.row_factory = sqlite3.Row
    return con

def password_hash(password, salt):
    return hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 300000).hex()

def initialize():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    with connect() as c:
        c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE COLLATE NOCASE, salt TEXT NOT NULL, password TEXT NOT NULL, roles TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY, user_id INTEGER NOT NULL, expires REAL NOT NULL);
        CREATE TABLE IF NOT EXISTS records(id INTEGER PRIMARY KEY, module TEXT NOT NULL, data TEXT NOT NULL, updated TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY, actor TEXT NOT NULL, action TEXT NOT NULL, created TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);''')
        if not c.execute('SELECT 1 FROM users LIMIT 1').fetchone():
            pw = os.getenv('ADMIN_PASSWORD','')
            if len(pw) < 12: raise RuntimeError('Defina ADMIN_PASSWORD com pelo menos 12 caracteres para criar o administrador.')
            salt = secrets.token_hex(16)
            c.execute('INSERT INTO users(name,salt,password,roles) VALUES(?,?,?,?)',(os.getenv('ADMIN_NAME','admin'),salt,password_hash(pw,salt),json.dumps(['Administrador'])))

class Handler(BaseHTTPRequestHandler):
    attempts = {}
    def reply(self, code, data, cookie=None):
        raw = json.dumps(data,ensure_ascii=False).encode(); self.send_response(code)
        self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        if cookie: self.send_header('Set-Cookie',cookie)
        self.end_headers(); self.wfile.write(raw)
    def user(self,c):
        cookie = SimpleCookie()
        try: cookie.load(self.headers.get('Cookie',''))
        except Exception: return None
        token = cookie.get('imperial_session')
        if not token: return None
        return c.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token=? AND s.expires>?',(hashlib.sha256(token.value.encode()).hexdigest(),time.time())).fetchone()
    def can(self,u,module):
        roles=json.loads(u['roles'])
        return bool(set(roles)&{'Administrador','Rei','Jarl de Solitude'}) or any(module in GRANTS.get(r,set()) for r in roles)
    def public_user(self,u): return {'id':u['id'],'name':u['name'],'roles':json.loads(u['roles'])}
    def do_GET(self):
        if self.path.startswith('/api/'):
            with connect() as c:
                u=self.user(c)
                if not u: return self.reply(401,{'error':'Entre para continuar.'})
                if self.path=='/api/state':
                    records=[dict(r, data=json.loads(r['data'])) for r in c.execute('SELECT * FROM records ORDER BY id DESC')]
                    users=[self.public_user(x) for x in c.execute('SELECT * FROM users')] if self.can(u,'users') else []
                    return self.reply(200,{'user':self.public_user(u),'records':records,'users':users,'roles':ROLES,'permissions':[m for m in MODULES|{'users'} if self.can(u,m)],'audit':[dict(x) for x in c.execute('SELECT actor,action,created FROM audit ORDER BY id DESC LIMIT 20')]})
                return self.reply(404,{'error':'Rota não encontrada.'})
        target={'/':'index.html','/app.js':'app.js','/style.css':'style.css'}.get(self.path.split('?')[0])
        if not target: return self.reply(404,{'error':'Página não encontrada.'})
        raw=(Path(__file__).parent/'public'/target).read_bytes(); self.send_response(200)
        self.send_header('Content-Type',{'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[target.split('.')[-1]])
        self.send_header('Content-Security-Policy',"default-src 'self'; img-src 'self' https:; style-src 'self'; script-src 'self'; frame-src 'self'; frame-ancestors 'none'; base-uri 'none'")
        self.send_header('X-Content-Type-Options','nosniff'); self.end_headers(); self.wfile.write(raw)
    def do_POST(self):
        # Reject cross-site mutations; same-origin fetch includes this custom header.
        if self.headers.get('X-Imperial-Client')!='1': return self.reply(403,{'error':'Origem inválida.'})
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>100000 or length<1: raise ValueError()
            body=json.loads(self.rfile.read(length))
            if not isinstance(body,dict): raise ValueError()
            with connect() as c:
                if self.path=='/api/login':
                    key=self.client_address[0]; recent=[t for t in self.attempts.get(key,[]) if t>time.time()-300]
                    if len(recent)>=10: return self.reply(429,{'error':'Muitas tentativas. Aguarde cinco minutos.'})
                    self.attempts[key]=recent+[time.time()]
                    u=c.execute('SELECT * FROM users WHERE name=?',(str(body.get('name','')),)).fetchone()
                    if not u or not hmac.compare_digest(u['password'],password_hash(str(body.get('password','')),u['salt'])): return self.reply(401,{'error':'Nome ou senha incorretos.'})
                    self.attempts.pop(key,None); token=secrets.token_urlsafe(32)
                    c.execute('DELETE FROM sessions WHERE expires<?',(time.time(),))
                    c.execute('INSERT INTO sessions VALUES(?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),u['id'],time.time()+43200))
                    secure='; Secure' if os.getenv('COOKIE_SECURE')=='1' else ''
                    return self.reply(200,{'ok':True},'imperial_session='+token+'; HttpOnly; SameSite=Strict; Path=/; Max-Age=43200'+secure)
                u=self.user(c)
                if not u: return self.reply(401,{'error':'Entre para continuar.'})
                if self.path=='/api/logout':
                    cookie=SimpleCookie(self.headers.get('Cookie','')); token=cookie.get('imperial_session')
                    if token: c.execute('DELETE FROM sessions WHERE token=?',(hashlib.sha256(token.value.encode()).hexdigest(),))
                    return self.reply(200,{'ok':True},'imperial_session=; HttpOnly; SameSite=Strict; Path=/; Max-Age=0')
                module=body.get('module')
                if self.path=='/api/users':
                    if not self.can(u,'users'): return self.reply(403,{'error':'Sem permissão.'})
                    name=str(body.get('name','')).strip(); pw=str(body.get('password','')); roles=body.get('roles',[])
                    if not name or len(name)>100 or (len(pw)<12 and (not body.get('id') or pw)) or not isinstance(roles,list) or not roles or any(r not in ROLES for r in roles): raise ValueError()
                    uid=body.get('id')
                    if uid:
                        existing=c.execute('SELECT * FROM users WHERE id=?',(uid,)).fetchone()
                        if not existing: return self.reply(404,{'error':'Acesso não encontrado.'})
                        if 'Administrador' in json.loads(existing['roles']) and 'Administrador' not in roles:
                            admins=[x for x in c.execute('SELECT roles FROM users WHERE id<>?',(uid,)) if 'Administrador' in json.loads(x['roles'])]
                            if not admins: return self.reply(400,{'error':'Mantenha pelo menos um Administrador.'})
                        c.execute('UPDATE users SET name=?,roles=? WHERE id=?',(name,json.dumps(roles),uid))
                        if pw:
                            salt=secrets.token_hex(16)
                            c.execute('UPDATE users SET salt=?,password=? WHERE id=?',(salt,password_hash(pw,salt),uid))
                        c.execute('DELETE FROM sessions WHERE user_id=?',(uid,))
                        action='Atualizou acesso de '+name
                    else:
                        salt=secrets.token_hex(16)
                        c.execute('INSERT INTO users(name,salt,password,roles) VALUES(?,?,?,?)',(name,salt,password_hash(pw,salt),json.dumps(roles)))
                        action='Criou acesso de '+name
                elif self.path in ('/api/save','/api/delete'):
                    if module not in MODULES: raise ValueError()
                    if not self.can(u,module): return self.reply(403,{'error':'Seu cargo não permite alterar esta área.'})
                    rid=body.get('id')
                    if rid and not c.execute('SELECT id FROM records WHERE id=? AND module=?',(rid,module)).fetchone(): return self.reply(404,{'error':'Registro não encontrado.'})
                    if self.path=='/api/delete':
                        if not rid: raise ValueError()
                        c.execute('DELETE FROM records WHERE id=? AND module=?',(rid,module)); action='Excluiu registro em '+module
                    else:
                        data=body.get('data');
                        if not isinstance(data,dict) or not str(data.get('title','')).strip() or len(json.dumps(data))>30000: raise ValueError()
                        if module in ('treasury','supplies'):
                            amount=float(data.get('amount',0))
                            if not 0<amount<1e12 or data.get('direction') not in ('Entrada','Saída'): raise ValueError()
                        if module=='citizens' and (not isinstance(data.get('roles',[]),list) or any(r not in ROLES for r in data.get('roles',[]))): raise ValueError()
                        if rid: c.execute('UPDATE records SET data=?,updated=CURRENT_TIMESTAMP WHERE id=? AND module=?',(json.dumps(data),rid,module))
                        else: c.execute('INSERT INTO records(module,data) VALUES(?,?)',(module,json.dumps(data)))
                        action=('Atualizou ' if rid else 'Registrou ')+str(data['title'])
                else: return self.reply(404,{'error':'Rota não encontrada.'})
                c.execute('INSERT INTO audit(actor,action) VALUES(?,?)',(u['name'],action)); return self.reply(200,{'ok':True})
        except sqlite3.IntegrityError: self.reply(409,{'error':'Esse nome já está em uso.'})
        except (ValueError,TypeError,KeyError): self.reply(400,{'error':'Confira os campos. Valores devem ser positivos e senhas ter 12 caracteres ou mais.'})

if __name__=='__main__':
    initialize(); ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8000'))),Handler).serve_forever()
