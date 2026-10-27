"""Read-only PRD/roadmap coverage audit; not a product integration test."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def require(condition,message):
    if not condition:raise ValueError(message)

def within(root,relative):
    p=Path(relative)
    require(not p.is_absolute() and '..' not in p.parts,'Document path must be project relative')
    resolved=(root/p).resolve()
    require(resolved.is_relative_to(root),'Document path escaped root')
    require(resolved.is_file(),f'Missing document: {relative}')
    return resolved


def graph_check(rows):
    indexed={r['id']:r for r in rows}
    require(len(indexed)==len(rows),'Duplicate modules')
    active=set();done=set()
    def visit(id):
        require(id in indexed,'Unknown dependency')
        require(id not in active,'Cyclic dependency')
        if id in done:return
        active.add(id)
        for dep in indexed[id]['depends_on']:visit(dep)
        active.remove(id);done.add(id)
    for id in indexed:visit(id)


def validate(root,installed_skill=None):
    root=Path(root).resolve()
    progress=json.loads(within(root,'project-control/progress.json').read_text(encoding='utf-8'))
    index=json.loads(within(root,'project-control/prd/index.json').read_text(encoding='utf-8'))
    requirements=json.loads(within(root,index['requirements_ref']).read_text(encoding='utf-8'))['requirements']
    modules={m['id']:m for m in progress['modules']}
    ids={r['id'] for r in requirements}
    require(len(ids)==len(requirements),'Duplicate requirements')
    require(all(re.fullmatch(r'R-[A-Z][0-9]{2}',r) for r in ids),'Invalid requirement ID')
    rows=index['modules'];graph_check(rows)
    specifications=json.loads(within(root,'project-control/prd/modules.json').read_text(encoding='utf-8'))['modules']
    require({m['id']:m['deps'] for m in specifications}=={m['id']:m['depends_on'] for m in rows},'PRD specifications disagree with dependency index')
    require(set(m['id'] for m in rows)==set(modules),'PRD index must cover all progress modules')
    require(index['roadmap_decision_id'] in {d['id'] for d in progress['decisions']},'Roadmap lacks user decision')
    decisions={d['id'] for d in progress['decisions']}
    pending=progress.get('pending_decision');all_decisions=decisions|({pending['id']} if pending else set())
    covered=set();references=set()
    for row in rows:
        module=modules[row['id']]
        require(row['depends_on']==module['depends_on'],'PRD dependencies disagree with progress')
        require(module.get('prd_ref')==row['prd_ref'],'PRD reference disagrees with progress')
        file=within(root,row['prd_ref']);text=file.read_text(encoding='utf-8')
        require(len(text)>500,'PRD has no substantive requirements')
        require('not_run' in text,'PRD omitted unverified integration boundary')
        require(any(re.match(r'- \*\*.+-AC[0-9]{2}\*\*：',line) for line in text.splitlines()),'PRD has no observable acceptance criteria')
        expected={r['id'] for r in requirements if row['id'] in r['modules']}
        require(set(row['requirement_ids'])==expected,'Requirement/module assignment mismatch')
        require(expected<=set(re.findall(r'R-[A-Z][0-9]{2}',text)),'PRD lost assigned requirements')
        if module['status']=='pending':
            require(module['maturity']=='not_verified','Future PRD claimed verification')
        covered.update(expected);references.add(file)
    require(covered==ids,'Orphan requirement')
    for r in requirements:
        require(bool(r['requirement']) and bool(r['source_refs']),'Requirement missing source')
        require(set(r['modules'])<=set(modules),'Requirement points to non-existent module')
        for ref in r['source_refs']:references.add(within(root,ref))
        require(set(r['decision_ids'])<=all_decisions,'Requirement invents user decision')
    require(modules['M04']['delivery_slice']=='M04-B' and 'M04-B' not in modules,'Lost original M04 identity or duplicate Agent')
    sequence=progress['project']['scope']['approved_execution_sequence']
    require(sequence.index('M02')<sequence.index('M04-A')<sequence.index('M03')<sequence.index('M04'),'Approved model ordering not followed')
    require(modules['M04-A']['depends_on']==['M02'],'Model onboarding incorrectly waits for semantics')
    require('M04-A' in modules['M03']['depends_on'],'M03 order was not updated')
    require({'M02','M03','M04-A'}<=set(modules['M04']['depends_on']),'Agent missing hard inputs')
    require(modules['M01']['status']=='closed' and progress['active_module'] in modules,'Documentation lost accepted M01 or active module')
    require('D-M02-RETENTION-013' in decisions or (pending and pending['id']=='D-M02-RETENTION-013'),'Documentation bypassed unresolved retention decision')
    skill_root=root/'skills/project-pdca'
    skill_paths=['SKILL.md','references/data-platform-roadmap.md','references/delivery-cycle.md','references/product-user-thinking.md']
    for rel in skill_paths:
        file=within(root,'skills/project-pdca/'+rel);references.add(file)
        for match in re.finditer(r'\[[^\]]+\]\((references/[^)]+)\)',file.read_text(encoding='utf-8')):
            require((skill_root/match.group(1)).is_file(),'Skill reference missing')
    text=(skill_root/'SKILL.md').read_text(encoding='utf-8')
    header=text.split('---',2)[1]
    require(re.search(r'^name: project-pdca$',header,re.M) and re.search(r'^description: .+',header,re.M),'Invalid known Skill frontmatter')
    require('universal-data-agent' in text and 'D-ROADMAP-MODEL-014' in text,'Project-specific Skill rule unscoped')
    if installed_skill:
        installed=Path(installed_skill).resolve()
        for rel in skill_paths:require((installed/rel).read_bytes()==(skill_root/rel).read_bytes(),'Installed Skill mismatch')
    references.update(within(root,p) for p in ['AGENTS.md','project-control/ROADMAP.md','project-control/prd/README.md','project-control/prd/REQUIREMENTS.md','project-control/prd/index.json','project-control/prd/requirements.json'])
    # Progress is a tested snapshot reference, not an immutable document fingerprint;
    # the next checkpoint legitimately changes it. Keep document-only hashes.
    for path in ['project-control/prd/modules.json','project-control/prd/validate.py','project-control/prd/test_validate.py','project-control/PROJECT_BRIEF.md','project-control/modules/M02/plan.md']:references.add(within(root,path))
    manifest={f.relative_to(root).as_posix():hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(references) if f.name!='progress.json'}
    return {'status':'passed','audited_revision':progress['revision'],'kind':'documentation_consistency','module_prds':len(rows),'requirements':len(ids),'roadmap_decision':index['roadmap_decision_id'],'m04_identity_preserved':True,'pending_retention_preserved':True,'installed_skill_synced':bool(installed_skill),'product_integration':'not_run (documentation audit only)','skill_creator_official_validator':'not_run (PyYAML unavailable; narrow frontmatter/references/sync checks performed here)','manifest':manifest}

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',required=True);parser.add_argument('--installed-skill');args=parser.parse_args()
    print(json.dumps(validate(args.root,args.installed_skill),ensure_ascii=False,indent=2))
