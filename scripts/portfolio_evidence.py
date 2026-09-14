"""Offline diagnostic comparison; synthetic cases, no model or user documents."""
from __future__ import annotations
import argparse
import hashlib
import json
import platform
import re
import socket
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'v1.1'))
sys.path.insert(0, str(ROOT / 'packages/core/src'))
from server.agent_service import extract_rules_from_text
from paper_setting_core.rulepacks import extract_rule_pack_draft
from paper_setting_core.errors import RuleSourceInvalidError


def no_network(*args, **kwargs):
    raise RuntimeError('Network disabled for this diagnostic')


def legacy_normalize(raw):
    t = raw['typography']
    match = re.fullmatch(r'([\d.]+)(cm|mm)', raw['margins']['top'])
    return {
        'body_font': t['body_font'], 'body_size_pt': t['body_size_pt'],
        'line_spacing': t['line_spacing'], 'line_spacing_mode': 'multiple',
        'margin_top_mm': float(match[1]) * (10 if match[2] == 'cm' else 1) if match else None,
        'rejected': False,
    }


def core_run(text):
    try:
        draft = extract_rule_pack_draft(text)
    except RuleSourceInvalidError as exc:
        return {'rejected': True}, {'error_type': type(exc).__name__, 'message': str(exc)}
    body = draft.rule_pack.rule_for('body')
    result = {
        'body_font': body.character.east_asia_font if body else None,
        'body_size_pt': body.character.size_pt if body else None,
        'line_spacing': body.paragraph.line_spacing if body else None,
        'line_spacing_mode': body.paragraph.line_spacing_mode if body else None,
        'margin_top_mm': draft.rule_pack.page.margin_top_mm if 'margin_top_mm' in draft.rule_pack.explicit_page_fields else None,
        'rejected': False,
    }
    return result, draft.model_dump(mode='json')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    socket.socket.connect = no_network
    socket.create_connection = no_network
    cases_path = ROOT / 'docs/portfolio-evidence/cases.json'
    cases = json.loads(cases_path.read_text())
    default_raw = extract_rules_from_text('', 'offline')
    results = []
    for case in cases:
        raw = extract_rules_from_text(case['text'], 'deepseek')
        core, core_raw = core_run(case['text'])
        offline = extract_rules_from_text(case['text'], 'offline')
        candidates = {
            '固定默认值基线': (legacy_normalize(default_raw), default_raw),
            'v1.1标称DeepSeek': (legacy_normalize(raw), raw),
            '核心确定性解析器': (core, core_raw),
        }
        for name, (actual, output) in candidates.items():
            checks = [{'field': key, 'expected': value, 'actual': actual.get(key), 'passed': actual.get(key) == value} for key, value in case['expected'].items()]
            results.append({'case_id': case['id'], 'category': case['category'], 'backend': name, 'checks': checks, 'passed': all(c['passed'] for c in checks), 'raw_output': output})
        assert legacy_normalize(raw) == legacy_normalize(offline)
    summary = {}
    for name in candidates:
        subset = [r for r in results if r['backend'] == name]
        summary[name] = {'case_passed': sum(r['passed'] for r in subset), 'case_total': len(subset), 'checkpoint_passed': sum(c['passed'] for r in subset for c in r['checks']), 'checkpoint_total': sum(len(r['checks']) for r in subset)}
    recovery = []
    for text in ['正文：宋体。\n上边距 20mm。', '正文：宋体。\n上边距 2cm。']:
        raw = extract_rules_from_text(text, 'deepseek')
        recovery.append({'input': text, 'normalized': legacy_normalize(raw), 'raw_output': raw})
    files = ['v1.1/server/agent_service.py', 'packages/core/src/paper_setting_core/rulepacks/extraction.py', 'docs/portfolio-evidence/cases.json', 'scripts/portfolio_evidence.py']
    result = {'created_at': datetime.now(timezone.utc).isoformat(), 'python': platform.python_version(), 'scope': '10 synthetic diagnostic cases; checkpoint accuracy only; not model eval or generalization benchmark', 'normalization': 'v1.1 line_spacing interpreted as multiplier because no mode field; core unspecified values use null; conflicts require no definitive font; additional fields outside checkpoints are not scored', 'source_sha256': {f: hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in files}, 'summary': summary, 'results': results, 'manual_unit_rewrite_recovery': recovery, 'deepseek_matches_offline_all_cases': True}
    (args.output/'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    (args.output/'cases.json').write_bytes(cases_path.read_bytes())
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print('Recovery top margins:', [r['normalized']['margin_top_mm'] for r in recovery])


if __name__ == '__main__':
    main()
