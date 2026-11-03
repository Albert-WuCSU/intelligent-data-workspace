"""Actual TCP HTTP streaming with fake Key in an independent loopback fixture."""
import asyncio,json,sys
from pathlib import Path
from http.server import BaseHTTPRequestHandler,HTTPServer
from threading import Thread
import httpx
sys.path.insert(0,str(Path.cwd()/'services/api/tests'))
from test_model_stream import frames,encoded,KEY
from data_workspace.model_provider import MessagesProvider,ModelConfiguration
from data_workspace.model_budget import EstimatedBudget

calls=[]
class Handler(BaseHTTPRequestHandler):
 def do_POST(self):
  body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
  calls.append(body);assert body['stream'] and body['max_tokens']==128
  self.send_response(200);self.send_header('Content-Type','text/event-stream');self.end_headers()
  for value in frames():self.wfile.write(encoded([value]));self.wfile.flush()
 def log_message(self,*args):pass
class LoopbackOnly(httpx.AsyncBaseTransport):
 def __init__(self,url):self.url=url;self.inner=httpx.AsyncHTTPTransport()
 async def handle_async_request(self,r):
  assert r.url.host=='ada-cli-golang.ctripcorp.com'
  return await self.inner.handle_async_request(httpx.Request('POST',self.url,content=r.content,headers=r.headers))
 async def aclose(self):await self.inner.aclose()
async def run(url,budget):
 p=MessagesProvider(ModelConfiguration('http://ada-cli-golang.ctripcorp.com/coding-plan/v1/messages','fixture-model','anthropic_messages','bearer'),KEY,budget,LoopbackOnly(url))
 events=[e async for e in p.stream('fixed')]
 assert events[-1].kind=='completed' and KEY not in str(events) and 'thinking' not in str(events)
 assert len(calls)==1 and budget.summary().reserved_requests==1
 return {'status':'passed','network':'actual TCP/HTTP SSE loopback, not supplier TLS','calls':len(calls),'events':len(events),'completed':True,'sql_executed':False,'key':'fake fixture only'}
if __name__=='__main__':
 import tempfile
 with tempfile.TemporaryDirectory() as tmp:
  server=HTTPServer(('127.0.0.1',0),Handler);thread=Thread(target=server.serve_forever,daemon=True);thread.start()
  try:result=asyncio.run(run('http://127.0.0.1:'+str(server.server_port)+'/messages',EstimatedBudget(Path(tmp)/'budget')))
  finally:server.shutdown();server.server_close();thread.join(5)
  print(json.dumps(result))
