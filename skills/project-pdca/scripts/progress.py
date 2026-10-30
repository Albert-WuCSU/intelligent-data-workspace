#!/usr/bin/env python3
"""Local progress checkpoints. Standard library only; never invokes shells or services."""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

FILE = Path('project-control/progress.json')
STATUS = {'in_progress', 'awaiting_decision', 'blocked', 'paused', 'complete'}
MODULE_STATUS = {'pending', 'active', 'needs_recheck', 'closed'}
PHASES = {'plan', 'do', 'check', 'act'}


def now():
    return datetime.now(timezone.utc).isoformat()


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def within(root, path):
    p = Path(path)
    if p.is_absolute() or '..' in p.parts:
        raise ValueError(f'Expected project-relative path: {path}')
    p = (root / p).resolve()
    if not p.is_relative_to(root):
        raise ValueError(f'Path escapes project: {path}')
    return p


def require(condition, message):
    if not condition:
        raise ValueError(message)


def finite_deferrals(state, module, decisions):
    """Explicit user-approved local deferral; never changes required/not_run or risk facts."""
    scope = module.get('delivery_scope')
    if not scope:
        return set(), set()
    require(scope.get('kind') == 'finite_local' and module['maturity'] == 'local_ready', 'Deferral only supports finite local_ready delivery')
    approval = decisions.get(scope.get('decision_id'), {})
    require(approval.get('kind') in {'scope', 'change'} and approval.get('module_id') == module['id']
            and approval.get('cycle_id') == module['cycle_id'], 'Deferral needs matching user scope approval')
    gates = {g['id']: g for g in state.get('release_gates', [])}
    tests = {t['id']: t for t in module.get('tests', [])}
    risks = {r.get('id'): r for r in module.get('risks', [])}
    result = []
    for field, source, key in (('deferred_tests', tests, 'test_id'), ('deferred_risks', risks, 'risk_id')):
        entries = scope.get(field, [])
        require(isinstance(entries, list), 'Deferral entries must be lists')
        ids = [e.get(key) for e in entries]
        require(len(ids) == len(set(ids)), 'Duplicate deferred item')
        for entry in entries:
            item = source.get(entry.get(key))
            gate = gates.get(entry.get('release_gate_id'), {})
            require(item is not None, 'Unknown deferred item')
            require(bool(entry.get('owner')) and bool(entry.get('condition')), 'Deferral needs owner and recheck condition')
            require(gate.get('status') == 'not_run' and gate.get('decision_id') == scope['decision_id']
                    and bool(gate.get('owner')) and bool(gate.get('condition')), 'Deferral needs unresolved approved release gate')
            if field == 'deferred_tests':
                require(item.get('required') is True and item.get('status') == 'not_run'
                        and item.get('integration') == 'real', 'Only required not_run real tests can be deferred')
            else:
                require(item.get('severity') != 'critical' and item.get('resolved') is False, 'Critical/resolved risk cannot be deferred')
        result.append(set(ids))
    return tuple(result)


def validate(s, root):
    require(s.get('schema_version') == 1, 'Unsupported schema_version; migrate explicitly')
    require(type(s.get('revision')) is int and s['revision'] >= 0, 'Invalid revision')
    require(s.get('status') in STATUS, 'Invalid project status')
    require(isinstance(s.get('project'), dict) and s['project'].get('id'), 'Missing project identity')
    modules = s.get('modules', [])
    require(bool(modules), 'No modules')
    ids = [m['id'] for m in modules]
    require(len(ids) == len(set(ids)), 'Duplicate module IDs')
    index = {m['id']: m for m in modules}
    decisions = s.get('decisions', [])
    dindex = {d['id']: d for d in decisions}
    require(len(dindex) == len(decisions), 'Duplicate decision IDs')
    for d in decisions:
        require(d.get('source') == 'user' and bool(d.get('user_statement')), 'Decisions require actual user evidence')
        require(d.get('kind') in {'scope', 'plan', 'delivery', 'change', 'permission', 'method', 'risk'}, 'Unknown decision kind')
        require(bool(d.get('selected_option')), 'Missing decision selection')
    pending = s.get('pending_decision')
    if pending:
        require(pending['id'] not in dindex, 'Answered decision still pending')
        require(pending.get('blocking') is True and pending.get('options'), 'Invalid pending decision')
        require(s['status'] == 'awaiting_decision', 'Blocking decision must set awaiting_decision')
    active = s.get('active_module')
    require(active is None or active in index, 'Unknown active module')
    for m in modules:
        require(m.get('status') in MODULE_STATUS and m.get('phase') in PHASES, 'Invalid module state')
        require(m.get('cycle_id'), 'Missing cycle_id')
        require(m.get('maturity') in {'not_verified', 'local_ready', 'staging_verified', 'production_verified'}, 'Invalid maturity')
        require(all(dep in index and dep != m['id'] for dep in m.get('depends_on', [])), 'Unknown/self dependency')
        approvals = m.get('approvals', {})
        if m['phase'] in {'do', 'check', 'act'} or m['status'] == 'closed':
            did = approvals.get('plan')
            require(did in dindex and dindex[did]['kind'] == 'plan' and dindex[did].get('module_id') == m['id']
                    and dindex[did].get('cycle_id') == m['cycle_id'], f'{m["id"]}: missing current-cycle plan approval')
            require(m.get('plan_ref') and within(root, m['plan_ref']).is_file(), f'{m["id"]}: approved plan file missing')
        if m['status'] in {'active', 'closed'}:
            require(all(index[x]['status'] == 'closed' for x in m.get('depends_on', [])), f'{m["id"]}: unmet dependency')
        deferred_tests, deferred_risks = finite_deferrals(s, m, dindex)
        if m['status'] == 'closed':
            did = approvals.get('delivery')
            require(did in dindex and dindex[did]['kind'] == 'delivery' and dindex[did].get('module_id') == m['id']
                    and dindex[did].get('cycle_id') == m['cycle_id'], f'{m["id"]}: missing delivery approval')
            require(m.get('audit', {}).get('verdict') == 'pass', f'{m["id"]}: audit not passed')
            if deferred_tests or deferred_risks:
                require(m['audit'].get('scope') == 'finite_local' and m['audit'].get('decision_id') == m['delivery_scope']['decision_id'], 'Finite delivery needs matching scoped audit')
            required = [t for t in m.get('tests', []) if t.get('required')]
            require(bool(required) and any(t.get('status') == 'passed' for t in required)
                    and all(t.get('status') == 'passed' or t['id'] in deferred_tests for t in required), f'{m["id"]}: required tests incomplete')
            ev = {e['id']: e for e in m.get('evidence', []) if not e.get('stale')}
            require(m['audit'].get('evidence_id') in ev, f'{m["id"]}: audit evidence missing')
            require(all(t.get('evidence_id') in ev for t in required if t['id'] not in deferred_tests), f'{m["id"]}: test evidence missing')
            require(not any(r.get('severity') in {'critical', 'high'} and not r.get('resolved') and r.get('id') not in deferred_risks for r in m.get('risks', [])), f'{m["id"]}: blocking risks')
        if m['maturity'] in {'staging_verified', 'production_verified'}:
            require(any(t.get('status') == 'passed' and t.get('environment') == m['maturity'].split('_')[0]
                        and t.get('integration') == 'real' for t in m.get('tests', [])), f'{m["id"]}: real environment evidence missing')
        for e in m.get('evidence', []):
            require(e.get('kind') in {'test', 'audit', 'demo', 'implementation', 'review'}, 'Unknown evidence kind')
            path = within(root, e['path'])
            if not e.get('stale'):
                require(path.is_file(), f'Missing evidence: {e["path"]}')
                require(e.get('sha256') == digest(path), f'Stale/changed evidence: {e["path"]}')
        for t in m.get('tests', []):
            require(t.get('status') in {'passed', 'failed', 'not_run', 'stale'}, 'Invalid test status')
            if t['status'] == 'passed':
                require(t.get('command') and t.get('exit_code') == 0 and t.get('code_fingerprint'), 'Incomplete test execution record')
                require(any(e['id'] == t.get('evidence_id') and not e.get('stale') for e in m.get('evidence', [])), 'Passing test has no current evidence')
    # Detect dependency cycles.
    visiting, visited = set(), set()
    def visit(mid):
        require(mid not in visiting, 'Dependency cycle')
        if mid in visited:
            return
        visiting.add(mid)
        for dep in index[mid].get('depends_on', []):
            visit(dep)
        visiting.remove(mid)
        visited.add(mid)
    for mid in ids:
        visit(mid)
    live = [m['id'] for m in modules if m['status'] in {'active', 'needs_recheck'}]
    require(live == ([active] if active else []), 'Exactly the active module must be active/needs_recheck')
    action = s.get('next_action', {})
    require(action.get('description') and action.get('kind'), 'Missing actionable next_action')
    if action.get('decision_id'):
        require(pending and action['decision_id'] == pending['id'], 'Next action references wrong pending decision')
    for ref in action.get('read_refs', []):
        require(within(root, ref).is_file(), f'Missing next-action reference: {ref}')
    if s['status'] == 'complete':
        require(all(m['status'] == 'closed' for m in modules), 'Incomplete modules')
        require(not any(m.get('delivery_scope', {}).get('deferred_tests') or m.get('delivery_scope', {}).get('deferred_risks') for m in modules), 'Deferred verification must be reconciled before complete')
        require(s.get('release_gates') and all(g['status'] == 'passed' for g in s['release_gates']), 'Release gates incomplete')
    return s


def atomic(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8', newline='\n') as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())
    os.replace(temp, path)


def handoff(s):
    m = next((m for m in s['modules'] if m['id'] == s.get('active_module')), None)
    a = s['next_action']
    lines = ['# 项目续接档案', '', f'状态版本 revision {s["revision"]}，更新时间 {s.get("updated_at", "未登记")} UTC。',
             '', '先校验 progress.json 并核对实际文件；本档案由脚本生成，主进度为唯一状态真源。', '',
             f'- 项目：{s["project"]["name"]}', f'- 当前：{m["id"] + " " + m["name"] + " / " + m["phase"] if m else "无活动模块"}',
             f'- 状态：{s["status"]}', f'- 下一步：{a["description"]}']
    if s.get('pending_decision'):
        d = s['pending_decision']
        lines += ['', f'## 待用户选择 {d["id"]}', d['question']]
        lines += [f'- {o["id"]} {o["label"]}：{o["tradeoff"]}' for o in d['options']]
    lines += ['', '## 优先读取'] + [f'- {p}' for p in a.get('read_refs', [])]
    lines += ['', '## 工作状态'] + [f'- {x}' for x in s.get('working_state', [])]
    lines += ['', '## 阻碍'] + [f'- {x}' for x in s.get('blockers', [])]
    lines += ['', '## 上下文建议', s.get('session', {}).get('new_chat_reason', '在模块边界保存后按需切换。'),
              '', '在同一项目目录使用 $project-pdca，读取 project-control/progress.json 和 HANDOFF.md，核对实际文件后继续推进；遵守已登记决策，不重建项目。', '']
    return '\n'.join(lines)


def checkpoint(root, draft, expected):
    path = root / FILE
    lock = path.with_name('checkpoint.lock')
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.write(fd, str(os.getpid()).encode())
        previous = load(path)
        require(previous['revision'] == expected, 'Revision conflict: reload progress before retrying')
        s = load(draft)
        require(s.get('revision') == expected, 'Draft revision differs from expected revision')
        require(s['project']['id'] == previous['project']['id'], 'Project identity cannot change')
        old = previous.get('decisions', [])
        require(s.get('decisions', [])[:len(old)] == old, 'Existing human decisions are append-only')
        previous_active = previous.get('active_module')
        next_active = s.get('active_module')
        if previous_active and previous_active != next_active:
            current = next((m for m in s['modules'] if m['id'] == previous_active), None)
            new_changes = s.get('decisions', [])[len(old):]
            require((current and current['status'] == 'closed') or
                    any(d.get('kind') == 'change' for d in new_changes),
                    'Cannot abandon current module without delivery or explicit user change')
        oldmods = {m['id']: m for m in previous['modules']}
        require(set(oldmods).issubset({m['id'] for m in s['modules']}), 'Do not silently remove modules; use explicit scope change')
        changed = []
        for m in s['modules']:
            before = oldmods.get(m['id'])
            if before and before['status'] == 'closed' and before != m:
                changed.append(m['id'])
        if changed:
            records = s.get('change_impacts', [])[len(previous.get('change_impacts', [])):]
            require(all(any(mid in r.get('modules', []) and r.get('reason') for r in records) for mid in changed), 'Closed module change requires impact record')
        s['revision'] = expected + 1
        s['updated_at'] = now()
        validate(s, root)
        history = root / 'project-control/checkpoints' / f'revision-{expected:06d}.json'
        require(not history.exists(), 'Checkpoint history exists; investigate conflicting progress')
        atomic(history, json.dumps(previous, ensure_ascii=False, indent=2) + '\n')
        atomic(path, json.dumps(s, ensure_ascii=False, indent=2) + '\n')
        # If interrupted here, render-handoff reconstructs this derived file.
        atomic(root / 'project-control/HANDOFF.md', handoff(s))
        return s
    finally:
        os.close(fd)
        lock.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['show', 'validate', 'checkpoint', 'render-handoff', 'hash'])
    parser.add_argument('--root', required=True)
    parser.add_argument('--draft')
    parser.add_argument('--expected-revision', type=int)
    parser.add_argument('--path')
    args = parser.parse_args()
    root = Path(args.root).resolve()
    if args.command == 'hash':
        require(bool(args.path), '--path required')
        print(digest(within(root, args.path)))
        return
    s = load(root / FILE)
    if args.command == 'checkpoint':
        require(args.draft is not None and args.expected_revision is not None, '--draft and --expected-revision required')
        s = checkpoint(root, Path(args.draft).resolve(), args.expected_revision)
        print(f'Checkpoint committed: revision {s["revision"]}')
    elif args.command == 'validate':
        validate(s, root)
        print(f'Progress valid: revision {s["revision"]}')
    elif args.command == 'render-handoff':
        validate(s, root)
        atomic(root / 'project-control/HANDOFF.md', handoff(s))
        print('HANDOFF regenerated')
    else:
        print(handoff(s))


if __name__ == '__main__':
    try:
        main()
    except (ValueError, KeyError, OSError, json.JSONDecodeError) as exc:
        print(f'ERROR: {exc}', file=sys.stderr)
        sys.exit(1)
