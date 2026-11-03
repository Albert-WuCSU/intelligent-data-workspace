"""Checkpoint only a genuinely passing stable full regression; no runtime/service operations."""
from pathlib import Path
import json,hashlib,sys,re
ROOT=Path.cwd();run=Path('project-control/modules/M04-A/evidence/20261102T061501Z')
r=json.loads((run/'results.json').read_text(encoding='utf-8'))
assert all(c['status']=='passed' and c.get('exit_code')==0 for c in r['checks'])
sys.path.insert(0,str(ROOT/'scripts'))
from check import sources
assert sources()[1]==r['code_fingerprint']
p=json.loads(Path('project-control/progress.json').read_text(encoding='utf-8'));assert p['revision']==137
m=next(x for x in p['modules'] if x['id']=='M04-A')
counts={name:int(re.search(r'(\d+) passed', (run/(name+'.txt')).read_text(encoding='utf-8')).group(1)) for name in ('backend','browser')}
counts['frontend']=16
base=Path('project-control/modules/M04-A/evidence/20261102T061500559940Z-stream-integration-readiness')
def add(id,kind,f):
 f=Path(f);m['evidence'].append({'id':id,'kind':kind,'path':f.as_posix(),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'stale':False})
add('M04A-STREAM-READINESS-FINAL-074','test',run/'results.json')
add('M04A-STREAM-READINESS-AC-075','review',base/'acceptance.md')
add('M04A-REMAINING-GATES-076','review',base/'remaining-gates.json')
review={'reviewer':'self_review','verdict':'pass','scope':'fixedsafe streamdiagnostics/busy noqueue local slice only, not wholemodule delivery','counts':counts,'types_build_pip':'actual_exit0','code_fingerprint':r['code_fingerprint'],'source_stability':'passed','actual_runtime':'glm-5.3 generationverified and enabled, still lacks stream_management; freshownership/status checked readonly; no Key read/POST paid invocation/restart','verified':['97special safe classification/poll/no new paid queue/UUIDnamespace/cancel/partial tests passed','2browser typed diagnostics success/cancel/refusal/readonly no extra budget passed','full local regression passed and original M01/M02 UI/permissions retained'],'not_run':['actualgateway stream','realuser currentsettings full lifecycle','publicsupplier/TLS','M03code/M04BmodelAgent/SQLJOIN/PGproduction'],'next_draft':'M03/PLAN_DRAFT.md unapproved adjacent preparation, module not activated','backlog':'AIPlan supported model catalog and same-connectionKey reuse remain B-MODEL-CATALOG-001','failure_history':'historicalfailed/notrun preserved; no required downgrade','cosmetic':'preexisting extra EOF blank provider line left to retain verified fingerprint, no semantic impact'}
f=run/'slice-review.json';f.write_text(json.dumps(review,ensure_ascii=False,indent=2),encoding='utf-8');add('M04A-READINESS-REVIEW-077','review',f)
by={c['id']:c for c in r['checks']}
for t in m['tests']:
 if t.get('required') and (t.get('integration')=='unit' or t['id']=='browser'):
  id=t['id'];t.update(by.get(id,by['backend']));t['id']=id;t['required']=True;t['evidence_id']='M04A-STREAM-READINESS-FINAL-074';t['scope']=f"Actualfull{counts['backend']}backend/16frontend/{counts['browser']}browser/types/build/pip stable; modelupstreamfakeKeyfixture, not actualgatewaystream/publicsupplier/TLS or wholemodule acceptance"
m['audit']={'verdict':'partial','reviewer':'self_review','evidence_id':'M04A-READINESS-REVIEW-077','scope':'streamdiagnostics/noqueue local pass; actualstream and module user delivery still incomplete'}
p['working_state'].append(f"Latest full check {counts['backend']} backend/16frontend/{counts['browser']}browser/types/build/pip actual pass, source stable (061501Z). Stream safeclassification and busy immediate refusal prevent extra queuedpaid test. Live runtime glm-5.3 still old no stream_management, no actual modelrequest or Keyread/restart. M03PLAN_DRAFT prepared, not approved/activated; currentM04A DO/partial. Local modifications not commit/push.")
p['next_action']={'kind':'user_actual_stream_then_scope_review','description':'当前glm-5.3非流式验证保持，不重复验证。用户本人核原启动器加载新增stream版本，在设置显式一次固定文本流式test收完成/partial与安全诊断；不在聊天给Key、不复制宿主Token、不盲杀/自动收费。真实AC02及历史协议scope/用户流程审查后请求M04-A验收；验收后审M03PLAN_DRAFT并确认最小语义包才DO，再M04-BLangGraph治理取数。目录Keyreuse待办/预算与PG生产延期不重问。','read_refs':['project-control/HANDOFF_DETAILS.md','project-control/STATUS.md','project-control/PRODUCT_UX_PRINCIPLES.md','project-control/ROADMAP.md','project-control/prd/M04-A.md','project-control/modules/M04-A/plan.md','project-control/BACKLOG.md','project-control/modules/M03/PLAN_DRAFT.md','MODEL_SERVICE.md',f.as_posix(),(run/'results.json').as_posix(),(base/'remaining-gates.json').as_posix()],'commands':['services/api/.venv/Scripts/python.exe skills/project-pdca/scripts/progress.py validate --root .','services/api/.venv/Scripts/python.exe skills/project-pdca/scripts/progress.py show --root .','services/api/.venv/Scripts/python.exe scripts/check.py --module M04-A --browser']}
summary=f"""# 最新续接摘要（2026-11-02，流式安全诊断与不排队修复）

- M01/M02有限本机验收不变；M04-A仍DO/partial未整体验收，不跳M03或宣称MVP闭环。
- 最新完整实跑{counts['backend']}后端、16前端、{counts['browser']}浏览器、types/build/pip退出0、源码稳定：061501Z。模型上游fakeKey/独立fixture，非真实gateway/TLS。
- 新增固定流式诊断reason/仅HTTP401403429，不回显上游正文/模型/Key；同UUID只读回执不追加预算。stream/config busy的新普通test立即拒绝，不排队收费；现context已有普通test回执可读。
- fresh只读当前API仍glm-5.3非流式generation_verified/enabled，但没有stream_management；用户未加载本轮流式。未读取Key/env、实际收费调用、服务重启或网关modelcatalog请求。
- 需要用户本人在原启动器加载新版、网页安全输入Key、设置显式一次固定流式测试收回执，后续诊断只读不用反复测试或索价格。Key不能发聊天，不自动替用户搬运/持久化。
- M03/PLAN_DRAFT已准备单表语义count/sum/ratio、真实字段映射、人工发布版本/非秘密存储候选；只是草稿，未批准/激活。M04-A范围审查＋人工验收后才确认M03PLAN，再M04-B LangGraph＋治理Harness调用模型/执行SQL。
- 真实网关stream/用户完整Key生命周期/公网TLS/Agent业务调用/SQLJOIN/PG生产仍未验；历史Responsesfailed与不同rootauth候选门禁不改required。AIPlan模型目录/复用Key切换保留BACKLOG，不批量扫描。
- 本轮源码/交接未commit/push；进度关键checkpoint137和最终138。PID/exec不可继承，不自动创建新聊天或调度任务。

"""
Path('project-control/STATUS.md').write_text(summary,encoding='utf-8')
details=Path('project-control/HANDOFF_DETAILS.md');details.write_text(summary+'---\n历史不覆盖上述当前状态。\n\n'+details.read_text(encoding='utf-8'),encoding='utf-8')
Path('project-control/NEW_WINDOW_PROMPT.md').write_text('在 D:\\Users\\luqianwu\\Desktop\\智能问数 使用 $project-pdca，先项目内progress.py validate/show并读progress/HANDOFF/DETAILS/STATUS/原则/ROADMAP/M04A PRDplan及M03PLAN_DRAFT，不重建。M01M02有限本机已验收，M04A仍DOpartial。当前glm-5.3非流式真验证启用但runtime仍缺stream_management；stream实现/固定safe诊断/不排队新收费已全回归过，实际网关stream未验。用户本人加载新版安全网页Key后显式一次固定stream收回执，不盲杀/继承PID/索聊天Key/复制Token/重复问预算和PG延期。M03草稿未批准/激活，M04A验收后再确认语义切片→M04BLangGraph治理取数，SQLJOIN/MVP未完成。目录Keyreuse待办保留，历史failed/notrun不降级，每节点保存，源码交接未push。\n',encoding='utf-8')
Path('project-control/progress.draft.json').write_text(json.dumps(p,ensure_ascii=False,indent=2),encoding='utf-8')
print('Prepared next checkpoint from stable full results:',counts,r['code_fingerprint'])
