"""Notebook CPU checks: no environment installation, token downloads or HTTP."""
import ast
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile
import stage
from preflight import context_report

REPO=Path(__file__).resolve().parents[3]
NOTEBOOK=REPO/'notebooks/development/UQRoute_TC_Qwen15B_Coverage_v1.ipynb'

class NotebookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.notebook=json.loads(NOTEBOOK.read_text(encoding='utf-8'))
        cls.codes=[''.join(c['source']) for c in cls.notebook['cells'] if c['cell_type']=='code']

    def test_all_cells_compile_without_saved_outputs(self):
        self.assertEqual(len(self.codes),10)
        for code in self.codes:compile(code,'notebook','exec')
        for cell in self.notebook['cells']:
            if cell['cell_type']=='code':self.assertEqual(cell['outputs'],[]);self.assertIsNone(cell['execution_count'])

    def test_preflight_embeds_tested_function_exactly(self):
        tree=ast.parse(next(c for c in self.codes if 'context_script = ' in c))
        script=next(n.value.value for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='context_script' for t in n.targets))
        node=next(n for n in ast.parse(script).body if isinstance(n,ast.FunctionDef) and n.name=='context_report')
        scope={};exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),'preflight','exec'),scope)
        self.assertEqual(scope['context_report']([7168,7169],2),context_report([7168,7169],2))
        self.assertIn("if not CONTEXT_REPORT['all_fit']:",self.codes[4])
        self.assertIn('start', ''.join(self.notebook['cells'][0]['source']))

    def test_transfer_extracts_only_expected_two_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);prepared=root/'prepared';archive=root/'transfer.zip'
            requests=[{'synthetic':i} for i in range(5)]
            manifest={'selection':'coverage','held_out_access_enabled':False,'requests_sha256':hashlib.sha256(stage.canonical(requests).encode()).hexdigest()}
            raw=stage.canonical(manifest).encode()
            with zipfile.ZipFile(archive,'w') as z:
                z.writestr('manifest.json',raw);z.writestr('requests.json',stage.canonical(requests))
            code=self.codes[2].replace('/content/corrected_qwen15b_coverage_transfer_v1.zip',archive.as_posix())
            scope={'PREPARED':prepared,'Path':Path,'zipfile':zipfile,'json':json,'EXPECTED_MANIFEST':hashlib.sha256(raw).hexdigest(),
                   'APPROVED_REQUEST_COUNT':5,'sha':stage.sha,'canonical':lambda x:stage.canonical(x).encode()}
            exec(compile(code,'transfer','exec'),scope)
            before={p:p.read_bytes() for p in prepared.iterdir()}
            exec(compile(code,'transfer','exec'),scope)
            self.assertEqual({p:p.read_bytes() for p in before},before)
            self.assertEqual({p.name for p in prepared.iterdir()},{'manifest.json','requests.json'})

    def test_coverage_namespace_and_generation_binding(self):
        source='\n'.join(self.codes)
        self.assertIn(stage.BASE,source)
        self.assertNotIn('corrected_qwen15b_feasibility_v1',source)
        self.assertIn('corrected_qwen15b_coverage_run_v1',source)
        self.assertIn('--execute-development',source)
        self.assertIn('ALL_INTENTS_PRESENT',source)
        self.assertNotIn('score_corrected.py',source)

if __name__=='__main__':unittest.main()
