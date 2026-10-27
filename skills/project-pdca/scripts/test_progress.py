#!/usr/bin/env python3
"""Behavioral tests for progress gates and resumable local checkpoints."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
import progress


def module(mid, deps=None):
    return {'id':mid,'name':mid,'depends_on':deps or [],'status':'pending','phase':'plan',
            'cycle_id':mid+'-C01','maturity':'not_verified','approvals':{},'plan_ref':None,
            'tests':[],'evidence':[],'audit':{'verdict':'not_run'},'risks':[]}


def decision(did, kind, mid='M01'):
    # Synthetic human choices used only in isolated unit fixtures.
    return {'id':did,'kind':kind,'module_id':mid,'cycle_id':mid+'-C01','source':'user',
            'user_statement':'synthetic user fixture: approve this exact test scope', 'selected_option':'A'}


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pdca-unit-')
        self.root = Path(self.temp.name).resolve()
        (self.root/'project-control').mkdir()
        (self.root/'brief.md').write_text('fixture brief',encoding='utf-8')
        self.s = {'schema_version':1,'revision':0,'status':'in_progress','project':{'id':'test','name':'Fixture'},
                  'active_module':'M01','modules':[module('M01'),module('M02',['M01'])],
                  'decisions':[], 'pending_decision':None, 'change_impacts':[],
                  'next_action':{'kind':'plan','description':'Plan current module','read_refs':['brief.md']},
                  'release_gates':[{'id':'real','status':'not_run'}]}
        self.s['modules'][0]['status']='active'
        self.save(self.root/progress.FILE,self.s)

    def tearDown(self):
        self.temp.cleanup()

    def save(self,p,s):
        p.write_text(json.dumps(s),encoding='utf-8')

    def commit(self,s,expected=0):
        draft=self.root/'draft.json';self.save(draft,s)
        return progress.checkpoint(self.root,draft,expected)

    def approve_plan(self,s):
        (self.root/'plan.md').write_text('fixture approved plan',encoding='utf-8')
        s['decisions'].append(decision('DP','plan'))
        s['modules'][0]['plan_ref']='plan.md'
        s['modules'][0]['approvals']['plan']='DP'
        s['modules'][0]['phase']='do'

    def add_evidence(self,s):
        for eid in ('T','A'):
            p=self.root/(eid+'.txt');p.write_text('fixture evidence '+eid,encoding='utf-8')
            s['modules'][0]['evidence'].append({'id':eid,'kind':'test' if eid=='T' else 'audit',
                                              'path':p.name,'sha256':progress.digest(p),'stale':False})
        s['modules'][0]['tests']=[{'id':'unit','required':True,'status':'passed','environment':'local',
            'integration':'unit','command':'python -m unittest','exit_code':0,'code_fingerprint':'fixture-hash','evidence_id':'T'}]
        s['modules'][0]['audit']={'verdict':'pass','evidence_id':'A','reviewer':'self_review'}

    def close_and_advance(self,s):
        self.approve_plan(s);self.add_evidence(s)
        s['decisions'].append(decision('DD','delivery'))
        s['modules'][0]['approvals']['delivery']='DD'
        s['modules'][0]['status']='closed';s['modules'][0]['phase']='act'
        s['modules'][1]['status']='active';s['active_module']='M02'
        s['next_action']={'kind':'plan','description':'Plan M02','read_refs':['brief.md']}

    def test_valid_initial_state(self):
        progress.validate(self.s,self.root)

    def test_atomic_checkpoint_and_handoff(self):
        out=self.commit(self.s)
        self.assertEqual(out['revision'],1)
        self.assertTrue((self.root/'project-control/checkpoints/revision-000000.json').is_file())
        self.assertIn('Plan current module',(self.root/'project-control/HANDOFF.md').read_text(encoding='utf-8'))

    def test_revision_conflict_preserves_state(self):
        self.commit(self.s)
        before=(self.root/progress.FILE).read_bytes()
        with self.assertRaisesRegex(ValueError,'Revision conflict'):
            self.commit(self.s)
        self.assertEqual(before,(self.root/progress.FILE).read_bytes())
        self.assertFalse((self.root/'project-control/checkpoint.lock').exists())

    def test_do_requires_user_plan(self):
        self.s['modules'][0]['phase']='do'
        with self.assertRaisesRegex(ValueError,'plan approval'):
            self.commit(self.s)
        self.assertEqual(progress.load(self.root/progress.FILE)['revision'],0)

    def test_approved_plan_can_enter_do(self):
        self.approve_plan(self.s)
        self.assertEqual(self.commit(self.s)['modules'][0]['phase'],'do')

    def test_existing_decision_cannot_be_rewritten(self):
        self.s['decisions']=[decision('D0','scope')];self.save(self.root/progress.FILE,self.s)
        self.s['decisions'][0]['selected_option']='B'
        with self.assertRaisesRegex(ValueError,'append-only'):
            self.commit(self.s)

    def test_model_recommendation_is_not_user_decision(self):
        self.s['decisions']=[decision('D0','scope')];self.s['decisions'][0]['source']='agent'
        with self.assertRaisesRegex(ValueError,'actual user evidence'):
            self.commit(self.s)

    def test_unaccepted_module_cannot_be_abandoned(self):
        self.s['active_module']='M02';self.s['modules'][0]['status']='pending';self.s['modules'][1]['status']='active'
        with self.assertRaisesRegex(ValueError,'abandon current module'):
            self.commit(self.s)

    def test_unclosed_dependency_blocks_activation(self):
        self.s['active_module']='M02';self.s['modules'][0]['status']='pending';self.s['modules'][1]['status']='active'
        with self.assertRaisesRegex(ValueError,'unmet dependency'):
            progress.validate(self.s,self.root)

    def test_test_evidence_cannot_change_silently(self):
        self.approve_plan(self.s);self.add_evidence(self.s)
        (self.root/'T.txt').write_text('changed',encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'Stale/changed evidence'):
            self.commit(self.s)

    def test_real_maturity_cannot_use_mock(self):
        self.approve_plan(self.s);self.add_evidence(self.s)
        self.s['modules'][0]['maturity']='production_verified'
        with self.assertRaisesRegex(ValueError,'real environment evidence missing'):
            self.commit(self.s)

    def test_delivery_and_evidence_allow_next_module(self):
        self.close_and_advance(self.s)
        result=self.commit(self.s)
        self.assertEqual(result['active_module'],'M02')
        self.assertEqual(result['modules'][0]['status'],'closed')

    def test_delivery_approval_required(self):
        self.close_and_advance(self.s)
        self.s['modules'][0]['approvals']['delivery']=None
        with self.assertRaisesRegex(ValueError,'delivery approval'):
            self.commit(self.s)

    def test_not_run_required_test_blocks_closure(self):
        self.close_and_advance(self.s);self.s['modules'][0]['tests'][0]['status']='not_run'
        with self.assertRaisesRegex(ValueError,'required tests incomplete'):
            self.commit(self.s)

    def test_high_risk_blocks_closure(self):
        self.close_and_advance(self.s)
        self.s['modules'][0]['risks']=[{'severity':'high','resolved':False}]
        with self.assertRaisesRegex(ValueError,'blocking risks'):
            self.commit(self.s)

    def test_path_traversal_is_rejected(self):
        self.s['next_action']['read_refs']=['../outside.txt']
        with self.assertRaisesRegex(ValueError,'project-relative'):
            self.commit(self.s)

    def test_dependency_cycle_is_rejected(self):
        self.s['modules'][0]['depends_on']=['M02']
        # pending nodes for standalone graph validation
        self.s['modules'][0]['status']='pending';self.s['active_module']=None
        with self.assertRaisesRegex(ValueError,'Dependency cycle'):
            progress.validate(self.s,self.root)

    def test_lock_contention_does_not_remove_other_lock(self):
        lock=self.root/'project-control/checkpoint.lock';lock.write_text('other owner')
        with self.assertRaises(FileExistsError):
            self.commit(self.s)
        self.assertTrue(lock.exists())

    def test_closed_module_change_needs_impact(self):
        self.close_and_advance(self.s);out=self.commit(self.s)
        out['modules'][0]['name']='new label'
        with self.assertRaisesRegex(ValueError,'impact record'):
            self.commit(out,expected=1)

    def test_missing_evidence_blocks_closure(self):
        self.close_and_advance(self.s);(self.root/'A.txt').unlink()
        with self.assertRaisesRegex(ValueError,'Missing evidence'):
            self.commit(self.s)

    def test_pending_decision_is_resumeable(self):
        self.s['status']='awaiting_decision'
        self.s['pending_decision']={'id':'DS','blocking':True,'question':'Choose scope',
                                   'options':[{'id':'A','label':'Small','tradeoff':'Fast'}]}
        self.s['next_action']={'kind':'user_decision','description':'Wait for DS','decision_id':'DS','read_refs':['brief.md']}
        out=self.commit(self.s)
        self.assertIn('DS',progress.handoff(progress.load(self.root/progress.FILE)))
        self.assertEqual(out['pending_decision']['id'],'DS')


if __name__=='__main__':
    unittest.main(verbosity=2)
