import unittest, tempfile, threading, os, json, urllib.request, urllib.error, http.cookiejar
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import server

class Integration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory(); server.DB=cls.temp.name+'/test.db'
        os.environ['ADMIN_PASSWORD']='a-strong-test-password'
        server.initialize()
        cls.http=server.ThreadingHTTPServer(('127.0.0.1',0),server.Handler)
        threading.Thread(target=cls.http.serve_forever,daemon=True).start()
        cls.base='http://127.0.0.1:'+str(cls.http.server_port)
    @classmethod
    def tearDownClass(cls):
        cls.http.shutdown(); cls.http.server_close(); cls.temp.cleanup()
    def client(self): return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
    def request(self,client,path,data=None,header=True):
        req=urllib.request.Request(self.base+'/api/'+path,data=json.dumps(data).encode() if data is not None else None,headers={'Content-Type':'application/json',**({'X-Imperial-Client':'1'} if header else {})})
        try:
            with client.open(req) as r: return r.status,json.load(r)
        except urllib.error.HTTPError as e: return e.code,json.load(e)
    def test_complete_workflow(self):
        admin=self.client(); visitor=self.client()
        self.assertEqual(self.request(admin,'state')[0],401)
        self.assertEqual(self.request(admin,'login',{'name':'admin','password':'wrong'})[0],401)
        self.assertEqual(self.request(admin,'login',{'name':'admin','password':'a-strong-test-password'})[0],200)
        self.assertEqual(self.request(admin,'users',{'name':'reader','password':'reader-password-123','roles':['Cidadão']})[0],200)
        self.assertEqual(self.request(visitor,'login',{'name':'reader','password':'reader-password-123'})[0],200)
        self.assertEqual(self.request(visitor,'save',{'module':'decrees','data':{'title':'Forbidden'}})[0],403)
        self.assertEqual(self.request(visitor,'users',{'name':'intruder','password':'intruder-pass-123','roles':['Administrador']})[0],403)
        for module in server.MODULES:
            data={'title':'Teste '+module,'amount':'12','direction':'Entrada','roles':['Cidadão']}
            self.assertEqual(self.request(admin,'save',{'module':module,'data':data})[0],200)
        code,state=self.request(admin,'state'); self.assertEqual(len(state['records']),len(server.MODULES))
        record=state['records'][0]
        self.assertEqual(self.request(admin,'save',{'module':record['module'],'id':record['id'],'data':{'title':'Editado','amount':5,'direction':'Saída'}})[0],200)
        self.assertEqual(self.request(admin,'save',{'module':'treasury','data':{'title':'Inválido','amount':-1,'direction':'Entrada'}})[0],400)
        self.assertEqual(self.request(admin,'delete',{'module':record['module'],'id':record['id']},header=False)[0],403)
        self.assertEqual(self.request(admin,'delete',{'module':record['module'],'id':record['id']})[0],200)
        self.assertEqual(self.request(admin,'delete',{'module':record['module'],'id':record['id']})[0],404)
        self.assertTrue(self.request(admin,'state')[1]['audit'])
        access=self.request(admin,'state')[1]['users']
        reader=next(x for x in access if x['name']=='reader')
        self.assertEqual(self.request(admin,'users',{'id':reader['id'],'name':'reader','password':'','roles':['Emissário','Tesoureiro']})[0],200)
        self.assertEqual(self.request(visitor,'state')[0],401)
        self.assertEqual(self.request(visitor,'login',{'name':'reader','password':'reader-password-123'})[0],200)
        self.assertIn('treasury',self.request(visitor,'state')[1]['permissions'])
        self.assertEqual(self.request(admin,'users',{'id':1,'name':'admin','password':'','roles':['Cidadão']})[0],400)
        server.initialize()  # Restart initialization preserves records/users.
        self.assertEqual(len(self.request(admin,'state')[1]['records']),len(server.MODULES)-1)
        self.assertEqual(self.request(admin,'logout',{})[0],200)
        self.assertEqual(self.request(admin,'state')[0],401)
    def test_grants_union(self):
        h=object.__new__(server.Handler)
        self.assertTrue(h.can({'roles':'["Emissário", "Tesoureiro"]'},'treasury'))
        self.assertTrue(h.can({'roles':'["Emissário", "Tesoureiro"]'},'treaties'))
        self.assertFalse(h.can({'roles':'["Emissário", "Tesoureiro"]'},'users'))

if __name__=='__main__': unittest.main()
