import asyncio,socket
from typing import TypedDict
from langgraph.graph import StateGraph,START,END
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import interrupt,Command
from data_workspace.graph_runtime import no_external_tracing
class State(TypedDict):x:int
async def run():
 original=socket.socket.connect
 socket.socket.connect=lambda *a,**k: (_ for _ in ()).throw(AssertionError('graph must not open network'))
 try:
  def confirm(s):return {'x':s['x']+1 if interrupt({'x':s['x']}) is True else s['x']}
  g=StateGraph(State);g.add_node('confirm',confirm);g.add_edge(START,'confirm');g.add_edge('confirm',END);compiled=g.compile(checkpointer=InMemorySaver());config={'configurable':{'thread_id':'smoke'},'callbacks':[],'recursion_limit':5}
  with no_external_tracing():
   a=await compiled.ainvoke({'x':1},config);assert '__interrupt__' in a
   b=await compiled.ainvoke(Command(resume=True),config);assert b['x']==2
  print('PASS: installed LangGraph interrupt/resume, graph runtime network denied, tracing disabled')
 finally:socket.socket.connect=original
asyncio.run(run())
