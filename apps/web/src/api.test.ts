import { describe, it, expect, vi, afterEach } from 'vitest';
import { request, ApiError, example } from './api';
afterEach(()=>vi.unstubAllGlobals());
describe('API contract transport',()=>{
  it('sends anti-CSRF header without a client tenant identity',async()=>{
    const fetcher=vi.fn().mockResolvedValue({ok:true,json:async()=>({valid:true})});vi.stubGlobal('fetch',fetcher);
    await request('/api/v1/query-spec/validate',example);
    const args=fetcher.mock.calls[0][1];expect(args.headers['X-Workspace-Request']).toBe('1');
    expect(JSON.parse(args.body)).not.toHaveProperty('tenant_id');
  });
  it('preserves safe errors and traces',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,json:async()=>({code:'INVALID_REQUEST',safe_message:'safe',trace_id:'trace'})}));
    await expect(request('/api',{})).rejects.toMatchObject({code:'INVALID_REQUEST',traceId:'trace'});
  });
  it('retains HTTP status for actionable outdated endpoint detection',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue({ok:false,status:404,json:async()=>({code:'HTTP_ERROR',safe_message:'safe',trace_id:'t'})}));
    await expect(request('/api/v1/semantics')).rejects.toMatchObject({code:'HTTP_ERROR',status:404,traceId:'t'});
  });
  it('normalizes connection failures',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('raw secret')));
    await expect(request('/api')).rejects.toEqual(new ApiError('CONNECTION_ERROR','无法连接后端服务，请确认 API 已启动。',''));
  });
});
