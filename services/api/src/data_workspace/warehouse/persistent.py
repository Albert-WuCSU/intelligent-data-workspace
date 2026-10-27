"""One owning asyncio task for each long-lived MCP session.

Only explicit list_tables verification opens/reopens a failed worker. Calls are
serialized; a submission is NEVER replayed after failure or reconnect.
"""
import asyncio
from .client import OwnedMCPClient
from data_workspace.auth import PublicError

class PersistentMCP:
    def __init__(self,auth,on_failure,client_factory=None):
        self.auth=auth;self.on_failure=on_failure
        self.factory=client_factory or OwnedMCPClient
        self.queue=asyncio.Queue(maxsize=1);self.current=None;self.context=None;self.task=None;self.stopping=False

    def start(self):
        if self.task is not None:raise RuntimeError('MCP owner already started')
        self.task=asyncio.create_task(self._serve())

    @property
    def healthy(self):return self.current is not None and self.current.healthy

    async def call(self,name,arguments=None):
        if self.stopping or self.task is None or self.task.done():
            raise PublicError(503,'CONNECTOR_NOT_READY','MCP会话未就绪，请重新验证连接。')
        future=asyncio.get_running_loop().create_future()
        try:self.queue.put_nowait((name,arguments or {},future))
        except asyncio.QueueFull:raise PublicError(409,'CAPACITY_EXCEEDED','MCP正在处理请求，请稍后重试。') from None
        # Even if HTTP requester disappears, the owned task finishes/cleans its
        # original operation; no hidden retry or cancellation in a foreign task.
        try:return await asyncio.shield(future)
        except asyncio.CancelledError:
            future.add_done_callback(lambda f:f.exception() if not f.cancelled() else None)
            raise

    async def _retire(self):
        context=self.context;self.context=None;self.current=None
        if context:
            try:await context.__aexit__(None,None,None)
            except Exception:pass  # bounded transport finally cleans owned Job

    async def _serve(self):
        try:
            while True:
                try:command=await asyncio.wait_for(self.queue.get(),timeout=.1)
                except asyncio.TimeoutError:
                    if self.current is not None and not self.current.healthy:
                        self.on_failure();await self._retire()
                    continue
                name,args,future=command
                if name is None:
                    await self._retire()
                    if not future.done():future.set_result(None)
                    return
                try:
                    if self.current is not None and not self.current.healthy:
                        self.on_failure();await self._retire()
                    if self.current is None:
                        if name!='list_tables':raise PublicError(503,'CONNECTOR_NOT_READY','长驻MCP已失效，请点击验证连接重新建立；不会重提旧查询。')
                        client=self.factory(self.auth);context=client.connected()
                        await context.__aenter__();self.context=context;self.current=client
                    value=await self.current.call(name,args)
                except Exception:
                    self.on_failure();await self._retire()
                    if not future.done():future.set_exception(PublicError(502,'CONNECTOR_UNAVAILABLE','MCP已中断并清理，旧执行上下文失效；请重新验证，不会自动重复提交。'))
                else:
                    if not future.done():future.set_result(value)
        finally:
            await self._retire()
            while not self.queue.empty():
                _,_,future=self.queue.get_nowait()
                if not future.done():future.set_exception(PublicError(503,'CONNECTOR_NOT_READY','MCP服务正在关闭。'))

    async def stop(self):
        self.stopping=True
        if self.task is None:return
        if self.task.done():await self.task;return
        future=asyncio.get_running_loop().create_future()
        await self.queue.put((None,{},future));await future;await self.task
