import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from plan_population import plan, summarize, loads, read_file, run, digest, BASE, BENCHMARK, SPLIT, ATTESTATION


def fixture():
    rows = []
    def row(group, benchmark, source, status='candidate', flagged=False, cost=False):
        key = source + ':' + group
        r = {'case_key': key, 'row_id': group, 'canonical_base_id': group,
             'source_file': source, 'benchmark': benchmark, 'population': 'primary',
             'split': 'development', 'construction_status': status,
             'excluded_from_inventory': False, 'official_labels_changed': False,
             'uncertainty_eligibility': 'not_assessed_before_inference',
             'reference_audit_status': 'completed_bounded_signals_only'}
        if status == 'blocked':
            r.update(construction_reason='Ambiguous missing schema for f',
                     reference_audit_status='not_assessed_due_to_construction_block')
        else:
            r['reference_audit'] = {'case_key': key, 'benchmark': benchmark,
                'changes_official_labels': False, 'excluded': False,
                'review_flags': ['reference_name_has_multiple_schema_occurrences'] if flagged else [],
                'objective_detection': {'cost_explicit_detected': cost, 'latency_explicit_detected': False}}
        rows.append(r)
    row('apibank_g', 'apibank', 'clean.jsonl', flagged=True)
    row('apibank_g', 'apibank', 'CD.jsonl', flagged=True)
    row('apibank_g', 'apibank', 'TD.jsonl', status='blocked')
    row('apibank_g', 'apibank', 'CD_NT.jsonl', cost=True)
    row('tooleyes_g', 'tooleyes', 'clean.jsonl')
    row('tooleyes_g', 'tooleyes', 'query_paraphrase.jsonl')
    summary = {'format_version': 'uqroute-development-pipeline-1.0.0', 'readiness': 'DEVELOPMENT_AUDIT_ONLY_MAIN_EXPERIMENT_NOT_READY', 'population': 'primary', 'partition': 'development', 'all_input_rows_retained': True,
        'official_labels_changed': False, 'reference_corrections_applied': False,
        'ambiguity_exclusions_applied': False, 'held_out_bundle_rows_accepted': 0,
        'raw_benchmark_files_opened_by_auditor': 0,
        'totals': summarize(rows),
        'by_benchmark': {b: summarize([r for r in rows if r['benchmark'] == b]) for b in ('apibank', 'tooleyes')},
        'by_source_file': {f: summarize([r for r in rows if r['source_file'] == f]) for f in {r['source_file'] for r in rows}},
        'reference_audit_status_counts': {'completed_bounded_signals_only': 5, 'not_assessed_due_to_construction_block': 1},
        'clean_anchor_pairing': {'perturbed_rows': 4, 'with_unique_clean_anchor': 4, 'both_constructed': 3},
        'reference_compliance_candidate_inventory': summarize(rows[:4]),
        'separate_tooleyes_relevance_candidate_inventory': summarize(rows[4:]),
        'reward_panel': {**summarize(rows[1:4]), 'objective_detection_assessed_rows': 2, 'objective_not_detected_rows': 1}}
    return rows, summary


class PopulationTests(unittest.TestCase):
    def test_panels_pairs_flags_and_unassessed_are_separate(self):
        rows, summary = fixture()
        before = copy.deepcopy((rows, summary))
        report, index, pairs = plan(rows, summary)
        self.assertEqual(report['source_inventory']['rows'], 6)
        self.assertEqual(report['official_reference_compliance']['rows'], 4)
        self.assertEqual(report['tooleyes_relevance']['rows'], 2)
        self.assertEqual(report['reward_overlap']['rows'], 3)
        self.assertEqual(report['construction_pairs']['both_constructed'], 3)
        self.assertEqual(report['reward_objective_unassessed'], 1)
        self.assertEqual(sum(bool(r['reference_review_signal']) for r in index), 2)
        self.assertEqual(len(index), 6)
        self.assertIsNone(next(r for r in index if r['construction_status'] == 'blocked')['cost_objective_detected'])
        self.assertFalse(report['main_experiment_ready'])
        self.assertNotIn('reference_audit', index[0])
        self.assertEqual((rows, summary), before)

    def test_audit_readiness_tampering_rejected(self):
        rows, summary = fixture(); summary['readiness'] = 'READY'
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_mixed_held_out_row_rejected(self):
        rows, summary = fixture(); rows[-1]['split'] = 'test'
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_non_development_summary_rejected(self):
        rows, summary = fixture(); summary['partition'] = 'test'
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_duplicate_key_rejected(self):
        rows, summary = fixture(); rows.append(copy.deepcopy(rows[0]))
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_missing_clean_anchor_rejected(self):
        rows, summary = fixture(); rows.pop(0)
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_duplicate_clean_anchor_rejected(self):
        rows, summary = fixture(); extra = copy.deepcopy(rows[0]); extra['row_id'] += '_x'; extra['case_key'] += '_x'; rows.append(extra)
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_summary_count_tampering_rejected(self):
        rows, summary = fixture(); summary['totals']['rows'] += 1
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_pair_count_tampering_rejected(self):
        rows, summary = fixture(); summary['clean_anchor_pairing']['both_constructed'] += 1
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_reward_denominator_tampering_rejected(self):
        rows, summary = fixture(); summary['reward_panel']['objective_detection_assessed_rows'] = 3
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_blocked_objective_assessment_rejected(self):
        rows, summary = fixture(); rows[2]['reference_audit_status'] = 'completed_bounded_signals_only'
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_outcome_fields_rejected(self):
        rows, summary = fixture(); rows[0]['prediction'] = 'do not accept outcomes'
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_reference_exclusion_rejected(self):
        rows, summary = fixture(); rows[0]['reference_audit']['excluded'] = True
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_nondetection_is_boolean_not_inferred(self):
        rows, summary = fixture(); rows[0]['reference_audit']['objective_detection']['cost_explicit_detected'] = 'false'
        with self.assertRaises(ValueError): plan(rows, summary)

    def test_json_duplicates_and_nonfinite_rejected(self):
        for text in ('{"x": 1, "x": 2}', '{"x": NaN}'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError): loads(text)

    def test_existing_output_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            with self.assertRaises(ValueError): run(p, p, 'a'*64, 'b'*64, p)

    def test_output_cannot_be_repository_code(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)
            with self.assertRaises(ValueError): run(p, p/'audit', 'a'*64, 'b'*64, p/'tools'/'output')

    def test_cli_hash_mismatch_does_not_modify_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp); audit = repo/'artifacts/local_development_audits/original'
            audit.mkdir(parents=True); f = audit/'summary.json'; f.write_bytes(b'{}')
            with patch('plan_population.subprocess.run'), patch('plan_population.subprocess.check_output', side_effect=lambda args, **kwargs: __import__('plan_population').loads(Path(__file__).with_name('source_manifest.json').read_bytes())['source_git_blobs'][args[-1].split(':', 1)[1]]):
                with self.assertRaises(ValueError): run(repo, audit, 'a'*64, 'b'*64, audit.parent/'new')
            self.assertEqual(f.read_bytes(), b'{}')
            self.assertFalse((audit.parent/'new').exists())

    def test_full_count_synthetic_cli_integration_preserves_inputs(self):
        from plan_population import SOURCE_FILES, REWARD, COMPLETED, BLOCKED_STATUS
        template = fixture()[0][0]
        rows = []
        def add(group, benchmark, source, blocked=False):
            r = copy.deepcopy(template)
            r.update(case_key=source+':'+group, row_id=group, canonical_base_id=group,
                     benchmark=benchmark, source_file=source)
            r['reference_audit'].update(case_key=r['case_key'], benchmark=benchmark, review_flags=[])
            if blocked:
                r.update(construction_status='blocked', construction_reason='retained block',
                         reference_audit_status=BLOCKED_STATUS)
                del r['reference_audit']
            rows.append(r)
        official = ['apibank_g'+str(i) for i in range(104)]
        eyes = ['tooleyes_g'+str(i) for i in range(36)]
        for g in official: add(g, 'apibank', 'clean.jsonl')
        for g in eyes: add(g, 'tooleyes', 'clean.jsonl')
        reward_slots = [(g, f) for f in sorted(REWARD) for g in official][:498]
        for i, (g, f) in enumerate(reward_slots): add(g, 'apibank', f, i < 12)
        other = sorted(SOURCE_FILES - REWARD - {'clean.jsonl'})
        for i, (g, f) in enumerate([(g, f) for f in other for g in official][:936]):
            add(g, 'apibank', f, i < 14)
        for f in other[:5]:
            for g in eyes: add(g, 'tooleyes', f)
        selected = lambda pred: [r for r in rows if pred(r)]
        reward = selected(lambda r: r['source_file'] in REWARD)
        summary = fixture()[1]
        summary.update(totals=summarize(rows),
            by_benchmark={b:summarize(selected(lambda r:r['benchmark']==b)) for b in ('apibank','tooleyes')},
            by_source_file={f:summarize(selected(lambda r:r['source_file']==f)) for f in {r['source_file'] for r in rows}},
            reference_audit_status_counts={COMPLETED:1728, BLOCKED_STATUS:26},
            clean_anchor_pairing={'perturbed_rows':1614,'with_unique_clean_anchor':1614,'both_constructed':1588},
            reference_compliance_candidate_inventory=summarize(selected(lambda r:r['benchmark']=='apibank')),
            separate_tooleyes_relevance_candidate_inventory=summarize(selected(lambda r:r['benchmark']=='tooleyes')),
            reward_panel={**summarize(reward),'objective_detection_assessed_rows':486,'objective_not_detected_rows':486},
            provenance={'benchmark_revision':BENCHMARK,'split_sha256':SPLIT,'attestation_sha256':ATTESTATION})
        with tempfile.TemporaryDirectory() as tmp:
            repo=Path(tmp); audit=repo/'artifacts/local_development_audits/original';audit.mkdir(parents=True)
            payloads={'summary.json':json.dumps(summary).encode(),'inventory.json':json.dumps(rows).encode()}
            for name, raw in payloads.items(): (audit/name).write_bytes(raw)
            manifest=loads(Path(__file__).with_name('source_manifest.json').read_bytes())
            with patch('plan_population.subprocess.run'), patch('plan_population.subprocess.check_output', side_effect=lambda args, **kwargs: manifest['source_git_blobs'][args[-1].split(':',1)[1]]):
                report=run(repo,audit,digest(payloads['summary.json']),digest(payloads['inventory.json']),audit.parent/'new')
            self.assertEqual(report['source_inventory']['rows'],1754)
            self.assertEqual(report['construction_pairs']['both_constructed'],1588)
            self.assertEqual({p.name for p in (audit.parent/'new').iterdir()}, {'denominators.json','case_index.json','construction_pairs.json'})
            for name, raw in payloads.items(): self.assertEqual((audit/name).read_bytes(),raw)


if __name__ == '__main__': unittest.main()
