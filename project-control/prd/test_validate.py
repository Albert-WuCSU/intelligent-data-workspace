"""Isolated behavioral checks for PRD audit guardrails, no product mutations."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
spec=importlib.util.spec_from_file_location('prd_validator',Path(__file__).with_name('validate.py'))
audit=importlib.util.module_from_spec(spec);spec.loader.exec_module(audit)

class DocumentationChecks(unittest.TestCase):
    def test_approved_dependency_order_is_acyclic(self):
        audit.graph_check([{'id':'M02','depends_on':[]},{'id':'M04-A','depends_on':['M02']},{'id':'M03','depends_on':['M04-A']},{'id':'M04','depends_on':['M02','M04-A','M03']}])
    def test_cycle_is_rejected(self):
        with self.assertRaises(ValueError):audit.graph_check([{'id':'A','depends_on':['B']},{'id':'B','depends_on':['A']}])
    def test_unknown_dependency_is_rejected(self):
        with self.assertRaises(ValueError):audit.graph_check([{'id':'A','depends_on':['missing']}])
    def test_duplicate_module_is_rejected(self):
        with self.assertRaises(ValueError):audit.graph_check([{'id':'A','depends_on':[]},{'id':'A','depends_on':[]}])
    def test_path_escape_and_missing_document_are_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            for p in ['../outside','missing.md']:
                with self.assertRaises(ValueError):audit.within(root,p)
            (root/'inside.md').write_text('valid',encoding='utf-8')
            self.assertEqual(audit.within(root,'inside.md'),root/'inside.md')

if __name__=='__main__':unittest.main()
