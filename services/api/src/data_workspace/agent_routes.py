"""Business query entrypoints: explicit paid planning and explicit confirmed execution."""
from fastapi import APIRouter,Depends,Request
from .auth import identity,PublicError
from .contracts import AuthContext
from .agent_contracts import AgentRequest,AgentConfirm,AgentTask,AgentTasks,AgentCapabilities
router=APIRouter(prefix='/api/v1/agent',tags=['agent'])

def service(request,auth):
    from .model_routes import authorize
    authorize(auth)
    value=request.app.state.agent
    if value is None:raise PublicError(503,'AGENT_NOT_CONFIGURED','当前服务未启用受控问数，请加载合法本机开发配置。')
    return value

@router.get('/capabilities',response_model=AgentCapabilities)
def capabilities(request:Request,auth:AuthContext=Depends(identity)):
    service(request,auth).auth(auth)
    return AgentCapabilities(available=True)
@router.post('/tasks',response_model=AgentTask)
async def start(body:AgentRequest,request:Request,auth:AuthContext=Depends(identity)):
    # async task must be scheduled on the API event loop.
    return service(request,auth).start(auth,body)
@router.get('/tasks',response_model=AgentTasks)
def list_tasks(request:Request,auth:AuthContext=Depends(identity)):
    agent=service(request,auth);agent.auth(auth);owner=request.app.state.sources.owner(auth)
    return AgentTasks(tasks=[task for id,task in agent.tasks.items() if agent.records[id]['owner']==owner])
@router.get('/tasks/{id}',response_model=AgentTask)
def read(id:str,request:Request,auth:AuthContext=Depends(identity)):
    return service(request,auth).get(auth,id)
@router.post('/tasks/{id}/confirm',response_model=AgentTask)
async def confirm(id:str,body:AgentConfirm,request:Request,auth:AuthContext=Depends(identity)):
    return await service(request,auth).confirm(auth,id,body)
@router.post('/tasks/{id}/cancel',response_model=AgentTask)
async def cancel(id:str,request:Request,auth:AuthContext=Depends(identity)):
    return await service(request,auth).cancel(auth,id)
