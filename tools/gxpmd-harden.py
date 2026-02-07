#!/usr/bin/env python3
"""
gxpmd-harden.py — GxP.MD Compliance Sweep Tool

Executes the harden mode compliance sweep defined in GxP.MD v2.0.0.
Parses annotations from source and test files, builds the traceability
matrix, validates annotation chains, and generates compliance reports.

Zero external dependencies — stdlib only.

Usage:
    python gxpmd-harden.py [--root PROJECT_ROOT] [--coverage COVERAGE_JSON]

Outputs:
    .gxp/traceability-matrix.json
    .gxp/compliance-status.md
    .gxp/gap-analysis.json
"""

import argparse
import hashlib
import json
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Annotation regex patterns
# ---------------------------------------------------------------------------

RE_GXP_REQ = re.compile(r'@gxp-req\s+(REQ-\d{3})(?:\s+"([^"]*)")?')
RE_GXP_SPEC = re.compile(r'@gxp-spec\s+(SPEC-\d{3}-\d{3})(?:\s+"([^"]*)")?')
RE_GXP_RISK = re.compile(r'@gxp-risk\s+(HIGH|MEDIUM|LOW)')
RE_TRACE = re.compile(r'@trace\s+(US-\d{3}-\d{3})')
RE_TEST_TYPE = re.compile(r'@test-type\s+(IQ|OQ|PQ)')

# File extensions to scan
SOURCE_EXTENSIONS = {
    '.ts', '.tsx', '.js', '.jsx', '.mjs', '.cjs',
    '.py', '.pyw',
    '.java', '.kt', '.kts',
    '.cs',
    '.go',
    '.rs',
    '.rb',
    '.swift',
    '.c', '.cpp', '.h', '.hpp',
}

# Directories always excluded
EXCLUDE_DIRS = {
    'node_modules', 'dist', 'build', '.git', '.gxp',
    '__pycache__', '.venv', 'venv', '.tox', 'target',
    'vendor', 'coverage', '.next', '.nuxt',
}

# ---------------------------------------------------------------------------
# Config parsing (reads GxP.MD frontmatter without PyYAML)
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    'risk_matrix': {
        'HIGH': {'coverage_threshold': 95, 'required_tiers': ['IQ', 'OQ', 'PQ']},
        'MEDIUM': {'coverage_threshold': 80, 'required_tiers': ['OQ', 'PQ']},
        'LOW': {'coverage_threshold': 60, 'required_tiers': ['OQ']},
    },
    'artifacts_dir': '.gxp',
    'required_source_tags': ['@gxp-req', '@gxp-spec', '@gxp-risk'],
    'required_test_tags': ['@gxp-spec', '@trace', '@test-type', '@gxp-risk'],
}


def parse_frontmatter(gxpmd_path: Path) -> dict:
    """Extract config from GxP.MD YAML frontmatter. Best-effort without PyYAML."""
    text = gxpmd_path.read_text(encoding='utf-8')
    first = text.find('---')
    if first == -1:
        return DEFAULT_CONFIG
    second = text.find('\n---', first + 3)
    if second == -1:
        return DEFAULT_CONFIG
    yaml_block = text[first + 3:second]

    config = dict(DEFAULT_CONFIG)

    # Parse coverage thresholds
    for level in ('HIGH', 'MEDIUM', 'LOW'):
        m = re.search(rf'{level}:\s*\n\s+coverage_threshold:\s*(\d+)', yaml_block)
        if m:
            config['risk_matrix'][level]['coverage_threshold'] = int(m.group(1))
        m = re.search(rf'{level}:\s*\n(?:\s+\w+:.*\n)*?\s+required_tiers:\s*\[([^\]]+)\]', yaml_block)
        if m:
            config['risk_matrix'][level]['required_tiers'] = [
                t.strip() for t in m.group(1).split(',')
            ]

    # Parse artifacts directory
    m = re.search(r'^\s+directory:\s*(\S+)', yaml_block, re.MULTILINE)
    if m:
        config['artifacts_dir'] = m.group(1)

    return config


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

def find_source_files(root: Path) -> list[Path]:
    """Walk project tree and collect source/test files."""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Prune excluded directories in-place
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for fname in filenames:
            ext = Path(fname).suffix.lower()
            if ext in SOURCE_EXTENSIONS:
                files.append(Path(dirpath) / fname)
    return sorted(files)


# ---------------------------------------------------------------------------
# Annotation parsing
# ---------------------------------------------------------------------------

def parse_annotations(filepath: Path, root: Path) -> dict:
    """Parse all GxP annotations from a single file."""
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except (OSError, UnicodeDecodeError):
        return None

    rel_path = str(filepath.relative_to(root))
    is_test = _is_test_file(rel_path)

    reqs = RE_GXP_REQ.findall(content)
    specs = RE_GXP_SPEC.findall(content)
    risks = RE_GXP_RISK.findall(content)
    traces = RE_TRACE.findall(content)
    test_types = RE_TEST_TYPE.findall(content)

    if not any([reqs, specs, risks, traces, test_types]):
        return None

    return {
        'file': rel_path,
        'is_test': is_test,
        'requirements': [{'id': r[0], 'desc': r[1]} for r in reqs],
        'specifications': [{'id': s[0], 'desc': s[1]} for s in specs],
        'risk_levels': risks,
        'traces': traces,
        'test_types': test_types,
    }


def _is_test_file(rel_path: str) -> bool:
    """Determine if a file is a test file by path or name conventions."""
    parts = rel_path.lower().replace('\\', '/')
    if any(seg in parts for seg in ['/tests/', '/test/', '/__tests__/', '/spec/',
                                     '/iq/', '/oq/', '/pq/']):
        return True
    base = Path(rel_path).stem.lower()
    return any(base.endswith(suffix) for suffix in ['.test', '.spec', '_test', '_spec'])


# ---------------------------------------------------------------------------
# Traceability matrix construction
# ---------------------------------------------------------------------------

def build_traceability(annotations: list[dict]) -> dict:
    """Build the REQ -> US -> SPEC -> CODE -> TEST traceability chains."""

    # Index: spec_id -> list of source files
    spec_to_source = defaultdict(list)
    # Index: spec_id -> list of test files
    spec_to_tests = defaultdict(list)
    # Index: req_id -> list of source files
    req_to_source = defaultdict(list)
    # Index: req_id -> set of risk levels
    req_risk = defaultdict(set)
    # Index: spec_id -> set of test types (tiers)
    spec_tiers = defaultdict(set)
    # Index: spec_id -> set of traced user stories
    spec_traces = defaultdict(set)
    # All known IDs
    all_req_ids = set()
    all_spec_ids = set()
    all_us_ids = set()

    for ann in annotations:
        f = ann['file']
        for r in ann['requirements']:
            all_req_ids.add(r['id'])
            if not ann['is_test']:
                req_to_source[r['id']].append(f)
        for s in ann['specifications']:
            all_spec_ids.add(s['id'])
            if ann['is_test']:
                spec_to_tests[s['id']].append(f)
            else:
                spec_to_source[s['id']].append(f)
        for risk in ann['risk_levels']:
            for r in ann['requirements']:
                req_risk[r['id']].add(risk)
            for s in ann['specifications']:
                req_id = _spec_to_req(s['id'])
                if req_id:
                    req_risk[req_id].add(risk)
        for tier in ann['test_types']:
            for s in ann['specifications']:
                spec_tiers[s['id']].add(tier)
        for us in ann['traces']:
            all_us_ids.add(us)
            for s in ann['specifications']:
                spec_traces[s['id']].add(us)

    # Group specs by requirement using ID convention
    req_to_specs = defaultdict(set)
    for spec_id in all_spec_ids:
        req_id = _spec_to_req(spec_id)
        if req_id:
            req_to_specs[req_id].add(spec_id)

    # Infer user stories from spec IDs (SPEC-NNN-MMM -> US-NNN-MMM)
    req_to_us = defaultdict(set)
    for us_id in all_us_ids:
        req_id = _us_to_req(us_id)
        if req_id:
            req_to_us[req_id].add(us_id)

    # Also infer from spec IDs
    for spec_id in all_spec_ids:
        us_id = _spec_to_us(spec_id)
        if us_id:
            req_id = _us_to_req(us_id)
            if req_id:
                req_to_us[req_id].add(us_id)

    # Ensure all referenced REQs exist
    for spec_id in all_spec_ids:
        req_id = _spec_to_req(spec_id)
        if req_id:
            all_req_ids.add(req_id)

    # Build chains
    chains = []
    for req_id in sorted(all_req_ids):
        specs = sorted(req_to_specs.get(req_id, set()))
        user_stories = sorted(req_to_us.get(req_id, set()))
        source_files = sorted(set(
            f for sid in specs for f in spec_to_source.get(sid, [])
        ) | set(req_to_source.get(req_id, [])))
        test_files = sorted(set(
            f for sid in specs for f in spec_to_tests.get(sid, [])
        ))
        tiers_present = sorted(set(
            t for sid in specs for t in spec_tiers.get(sid, set())
        ))
        risk = _resolve_risk(req_risk.get(req_id, set()))
        traced_us = sorted(set(
            us for sid in specs for us in spec_traces.get(sid, set())
        ))

        has_source = len(source_files) > 0
        has_tests = len(test_files) > 0
        has_specs = len(specs) > 0

        if has_source and has_tests and has_specs:
            status = 'COMPLETE'
        elif has_source or has_tests or has_specs:
            status = 'PARTIAL'
        else:
            status = 'MISSING'

        chains.append({
            'requirement': req_id,
            'user_stories': user_stories,
            'specifications': specs,
            'source_files': source_files,
            'test_files': test_files,
            'risk_level': risk,
            'tiers_present': tiers_present,
            'traced_user_stories': traced_us,
            'status': status,
        })

    return {
        'chains': chains,
        'all_req_ids': sorted(all_req_ids),
        'all_spec_ids': sorted(all_spec_ids),
        'all_us_ids': sorted(all_us_ids),
    }


def _spec_to_req(spec_id: str) -> str | None:
    """SPEC-001-002 -> REQ-001"""
    m = re.match(r'SPEC-(\d{3})-\d{3}', spec_id)
    return f'REQ-{m.group(1)}' if m else None


def _spec_to_us(spec_id: str) -> str | None:
    """SPEC-001-002 -> US-001-002"""
    m = re.match(r'SPEC-(\d{3}-\d{3})', spec_id)
    return f'US-{m.group(1)}' if m else None


def _us_to_req(us_id: str) -> str | None:
    """US-001-002 -> REQ-001"""
    m = re.match(r'US-(\d{3})-\d{3}', us_id)
    return f'REQ-{m.group(1)}' if m else None


def _resolve_risk(risks: set) -> str:
    """Given a set of risk levels, return the highest."""
    if 'HIGH' in risks:
        return 'HIGH'
    if 'MEDIUM' in risks:
        return 'MEDIUM'
    if 'LOW' in risks:
        return 'LOW'
    return 'UNKNOWN'


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_annotations(annotations: list[dict], config: dict) -> list[dict]:
    """Validate annotation format and completeness. Returns list of issues."""
    issues = []

    for ann in annotations:
        f = ann['file']
        risk_levels = ann['risk_levels']
        specs = [s['id'] for s in ann['specifications']]

        if ann['is_test']:
            # Test files need: @gxp-spec, @trace, @test-type, @gxp-risk
            if not specs:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Test file missing @gxp-spec annotation',
                })
            if not ann['traces']:
                issues.append({
                    'file': f, 'severity': 'WARNING',
                    'message': 'Test file missing @trace annotation',
                })
            if not ann['test_types']:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Test file missing @test-type annotation',
                })
            if not risk_levels:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Test file missing @gxp-risk annotation',
                })
        else:
            # Source files need: @gxp-req, @gxp-spec, @gxp-risk
            if not ann['requirements']:
                # Only warning — LOW risk files MAY omit @gxp-req
                if risk_levels and risk_levels[0] != 'LOW':
                    issues.append({
                        'file': f, 'severity': 'WARNING',
                        'message': 'Source file missing @gxp-req annotation',
                    })
            if not specs:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Source file missing @gxp-spec annotation',
                })
            if not risk_levels:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Source file missing @gxp-risk annotation',
                })

        # Check for inconsistent risk levels within a file
        if len(set(risk_levels)) > 1:
            issues.append({
                'file': f, 'severity': 'WARNING',
                'message': f'File has mixed risk levels: {", ".join(set(risk_levels))}',
            })

    return issues


def find_orphans(traceability: dict, annotations: list[dict]) -> list[dict]:
    """Find annotation IDs that don't resolve to any other annotation."""
    issues = []
    all_req_ids = set(traceability['all_req_ids'])
    all_spec_ids = set(traceability['all_spec_ids'])
    all_us_ids = set(traceability['all_us_ids'])

    for ann in annotations:
        f = ann['file']
        for spec in ann['specifications']:
            # Every SPEC should have a corresponding source or test file
            req_id = _spec_to_req(spec['id'])
            if req_id and req_id not in all_req_ids:
                # SPEC references a REQ that has no @gxp-req annotation
                issues.append({
                    'file': f, 'severity': 'WARNING',
                    'message': f'{spec["id"]} implies {req_id} but no @gxp-req {req_id} found',
                })

        for us in ann['traces']:
            # Every @trace US should have a corresponding SPEC
            expected_spec_prefix = 'SPEC-' + us[3:]  # US-001-002 -> SPEC-001-002
            if expected_spec_prefix not in all_spec_ids:
                issues.append({
                    'file': f, 'severity': 'WARNING',
                    'message': f'@trace {us} has no corresponding {expected_spec_prefix} annotation',
                })

    return issues


# ---------------------------------------------------------------------------
# Coverage analysis
# ---------------------------------------------------------------------------

def analyze_coverage(traceability: dict, config: dict,
                     coverage_data: dict | None) -> list[dict]:
    """Check coverage thresholds and tier requirements."""
    issues = []
    matrix = config['risk_matrix']

    for chain in traceability['chains']:
        risk = chain['risk_level']
        if risk == 'UNKNOWN':
            issues.append({
                'requirement': chain['requirement'],
                'severity': 'WARNING',
                'message': 'No risk level assigned',
            })
            continue

        level_config = matrix.get(risk, {})
        required_tiers = set(level_config.get('required_tiers', []))
        present_tiers = set(chain['tiers_present'])
        missing_tiers = required_tiers - present_tiers

        if missing_tiers:
            issues.append({
                'requirement': chain['requirement'],
                'severity': 'ERROR',
                'message': f'{risk} risk requires tiers {sorted(required_tiers)} '
                           f'but only {sorted(present_tiers)} present. '
                           f'Missing: {sorted(missing_tiers)}',
            })

        if not chain['test_files']:
            issues.append({
                'requirement': chain['requirement'],
                'severity': 'ERROR',
                'message': 'No test files found for this requirement chain',
            })

        # Coverage threshold check (if coverage data available)
        if coverage_data:
            threshold = level_config.get('coverage_threshold', 0)
            for src in chain['source_files']:
                file_cov = _get_file_coverage(src, coverage_data)
                if file_cov is not None and file_cov < threshold:
                    issues.append({
                        'requirement': chain['requirement'],
                        'severity': 'ERROR',
                        'message': f'{src}: coverage {file_cov:.1f}% < '
                                   f'{threshold}% threshold for {risk} risk',
                    })

    return issues


def _get_file_coverage(filepath: str, coverage_data: dict) -> float | None:
    """Extract coverage percentage for a file from coverage-summary.json format."""
    # Support Istanbul/nyc coverage-summary.json format
    if isinstance(coverage_data, dict):
        for key in [filepath, './' + filepath, '/' + filepath]:
            if key in coverage_data:
                entry = coverage_data[key]
                if isinstance(entry, dict) and 'statements' in entry:
                    return entry['statements'].get('pct', None)
                if isinstance(entry, dict) and 'lines' in entry:
                    return entry['lines'].get('pct', None)
    return None


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_traceability_matrix(traceability: dict, config: dict,
                                  project_root: Path) -> dict:
    """Generate the .gxp/traceability-matrix.json output."""
    now = datetime.now(timezone.utc).isoformat()

    chains_output = []
    for chain in traceability['chains']:
        chains_output.append({
            'requirement': chain['requirement'],
            'user_stories': chain['user_stories'],
            'specifications': chain['specifications'],
            'source_files': chain['source_files'],
            'test_files': chain['test_files'],
            'risk_level': chain['risk_level'],
            'tiers_present': chain['tiers_present'],
            'status': chain['status'],
        })

    complete = sum(1 for c in chains_output if c['status'] == 'COMPLETE')
    partial = sum(1 for c in chains_output if c['status'] == 'PARTIAL')
    missing = sum(1 for c in chains_output if c['status'] == 'MISSING')

    return {
        'generated_at': now,
        'gxpmd_version': '2.0.0',
        'project_root': str(project_root),
        'chains': chains_output,
        'summary': {
            'total_requirements': len(chains_output),
            'complete_chains': complete,
            'partial_chains': partial,
            'missing_chains': missing,
        },
    }


def generate_compliance_status(traceability: dict, validation_issues: list,
                                orphan_issues: list, coverage_issues: list,
                                annotations: list, config: dict) -> str:
    """Generate .gxp/compliance-status.md report."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    chains = traceability['chains']

    total_reqs = len(chains)
    complete = sum(1 for c in chains if c['status'] == 'COMPLETE')
    partial = sum(1 for c in chains if c['status'] == 'PARTIAL')
    missing = sum(1 for c in chains if c['status'] == 'MISSING')

    annotated_source = sum(1 for a in annotations if not a['is_test'])
    annotated_test = sum(1 for a in annotations if a['is_test'])

    all_issues = validation_issues + orphan_issues + coverage_issues
    errors = [i for i in all_issues if i.get('severity') == 'ERROR']
    warnings = [i for i in all_issues if i.get('severity') == 'WARNING']

    high_risk = [c for c in chains if c['risk_level'] == 'HIGH']
    medium_risk = [c for c in chains if c['risk_level'] == 'MEDIUM']
    low_risk = [c for c in chains if c['risk_level'] == 'LOW']

    lines = [
        '# Compliance Status Report',
        '',
        f'Generated: {now}',
        'GxP.MD Version: 2.0.0',
        '',
        '---',
        '',
        '## Summary',
        '',
        '| Metric | Value |',
        '|--------|-------|',
        f'| Total requirements | {total_reqs} |',
        f'| Complete chains | {complete}/{total_reqs} |',
        f'| Partial chains | {partial}/{total_reqs} |',
        f'| Missing chains | {missing}/{total_reqs} |',
        f'| Annotated source files | {annotated_source} |',
        f'| Annotated test files | {annotated_test} |',
        f'| Errors | {len(errors)} |',
        f'| Warnings | {len(warnings)} |',
        '',
        '## Risk Distribution',
        '',
        '| Risk Level | Requirements | Complete |',
        '|------------|-------------|----------|',
        f'| HIGH | {len(high_risk)} | {sum(1 for c in high_risk if c["status"] == "COMPLETE")}/{len(high_risk)} |',
        f'| MEDIUM | {len(medium_risk)} | {sum(1 for c in medium_risk if c["status"] == "COMPLETE")}/{len(medium_risk)} |',
        f'| LOW | {len(low_risk)} | {sum(1 for c in low_risk if c["status"] == "COMPLETE")}/{len(low_risk)} |',
        '',
    ]

    if errors:
        lines.extend([
            '## Errors',
            '',
        ])
        for issue in errors:
            loc = issue.get('file', issue.get('requirement', '?'))
            lines.append(f'- **{loc}**: {issue["message"]}')
        lines.append('')

    if warnings:
        lines.extend([
            '## Warnings',
            '',
        ])
        for issue in warnings:
            loc = issue.get('file', issue.get('requirement', '?'))
            lines.append(f'- **{loc}**: {issue["message"]}')
        lines.append('')

    # Traceability chain details
    lines.extend([
        '## Traceability Chains',
        '',
    ])
    for chain in chains:
        status_icon = {'COMPLETE': 'PASS', 'PARTIAL': 'PARTIAL', 'MISSING': 'FAIL'}
        icon = status_icon.get(chain['status'], '?')
        lines.append(f'### {chain["requirement"]} [{icon}]')
        lines.append('')
        lines.append(f'- **Risk**: {chain["risk_level"]}')
        lines.append(f'- **Specs**: {", ".join(chain["specifications"]) or "none"}')
        lines.append(f'- **User Stories**: {", ".join(chain["user_stories"]) or "none"}')
        lines.append(f'- **Source Files**: {", ".join(chain["source_files"]) or "none"}')
        lines.append(f'- **Test Files**: {", ".join(chain["test_files"]) or "none"}')
        lines.append(f'- **Tiers**: {", ".join(chain["tiers_present"]) or "none"}')
        lines.append('')

    # Sign-off section
    lines.extend([
        '---',
        '',
        '## Sign-off',
        '',
        '| Role | Name | Date | Signature |',
        '|------|------|------|-----------|',
        '| QA Lead | _____ | _____ | _____ |',
        '| Project Owner | _____ | _____ | _____ |',
        '',
        '*Sign-off is completed by humans, not agents.*',
        '',
    ])

    return '\n'.join(lines)


def generate_gap_analysis(validation_issues: list, orphan_issues: list,
                           coverage_issues: list) -> dict:
    """Generate .gxp/gap-analysis.json output."""
    now = datetime.now(timezone.utc).isoformat()
    all_issues = validation_issues + orphan_issues + coverage_issues

    return {
        'generated_at': now,
        'gxpmd_version': '2.0.0',
        'total_issues': len(all_issues),
        'errors': len([i for i in all_issues if i.get('severity') == 'ERROR']),
        'warnings': len([i for i in all_issues if i.get('severity') == 'WARNING']),
        'validation_issues': validation_issues,
        'orphan_issues': orphan_issues,
        'coverage_issues': coverage_issues,
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='GxP.MD v2.0.0 Compliance Sweep Tool',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='Outputs are written to the .gxp/ directory in the project root.',
    )
    parser.add_argument(
        '--root', type=Path, default=Path('.'),
        help='Project root directory (default: current directory)',
    )
    parser.add_argument(
        '--coverage', type=Path, default=None,
        help='Path to coverage-summary.json (Istanbul/nyc format)',
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output results as JSON to stdout (in addition to files)',
    )
    args = parser.parse_args()

    root = args.root.resolve()

    # 1. Parse config
    gxpmd_path = root / 'GxP.MD'
    if not gxpmd_path.exists():
        print(f'ERROR: No GxP.MD file found at {gxpmd_path}', file=sys.stderr)
        sys.exit(1)

    print(f'Reading config from {gxpmd_path}')
    config = parse_frontmatter(gxpmd_path)

    # 2. Scan files
    print(f'Scanning source files in {root}...')
    source_files = find_source_files(root)
    print(f'  Found {len(source_files)} source/test files')

    # 3. Parse annotations
    print('Parsing annotations...')
    annotations = []
    for f in source_files:
        ann = parse_annotations(f, root)
        if ann:
            annotations.append(ann)
    print(f'  Found annotations in {len(annotations)} files')

    if not annotations:
        print('WARNING: No GxP annotations found in any files.', file=sys.stderr)

    # 4. Validate
    print('Validating annotations...')
    validation_issues = validate_annotations(annotations, config)

    # 5. Build traceability
    print('Building traceability matrix...')
    traceability = build_traceability(annotations)

    # 6. Find orphans
    print('Checking for orphan annotations...')
    orphan_issues = find_orphans(traceability, annotations)

    # 7. Coverage analysis
    coverage_data = None
    if args.coverage and args.coverage.exists():
        print(f'Reading coverage from {args.coverage}...')
        coverage_data = json.loads(args.coverage.read_text(encoding='utf-8'))
    coverage_issues = analyze_coverage(traceability, config, coverage_data)

    # 8. Generate outputs
    gxp_dir = root / config['artifacts_dir']
    gxp_dir.mkdir(parents=True, exist_ok=True)

    # Traceability matrix
    matrix = generate_traceability_matrix(traceability, config, root)
    matrix_path = gxp_dir / 'traceability-matrix.json'
    matrix_path.write_text(json.dumps(matrix, indent=2) + '\n', encoding='utf-8')
    print(f'  Wrote {matrix_path}')

    # Gap analysis
    gaps = generate_gap_analysis(validation_issues, orphan_issues, coverage_issues)
    gaps_path = gxp_dir / 'gap-analysis.json'
    gaps_path.write_text(json.dumps(gaps, indent=2) + '\n', encoding='utf-8')
    print(f'  Wrote {gaps_path}')

    # Compliance status report
    status_report = generate_compliance_status(
        traceability, validation_issues, orphan_issues, coverage_issues,
        annotations, config,
    )
    status_path = gxp_dir / 'compliance-status.md'
    status_path.write_text(status_report, encoding='utf-8')
    print(f'  Wrote {status_path}')

    # 9. Summary
    all_issues = validation_issues + orphan_issues + coverage_issues
    errors = [i for i in all_issues if i.get('severity') == 'ERROR']
    warnings = [i for i in all_issues if i.get('severity') == 'WARNING']

    chains = traceability['chains']
    complete = sum(1 for c in chains if c['status'] == 'COMPLETE')

    print()
    print('=' * 60)
    print('  GxP.MD COMPLIANCE SWEEP COMPLETE')
    print('=' * 60)
    print(f'  Requirements:     {len(chains)}')
    print(f'  Complete chains:  {complete}/{len(chains)}')
    print(f'  Errors:           {len(errors)}')
    print(f'  Warnings:         {len(warnings)}')
    print(f'  Annotated files:  {len(annotations)}')
    print('=' * 60)

    if errors:
        print()
        print('ERRORS:')
        for issue in errors:
            loc = issue.get('file', issue.get('requirement', '?'))
            print(f'  [{loc}] {issue["message"]}')

    if args.json:
        output = {
            'traceability_matrix': matrix,
            'gap_analysis': gaps,
            'summary': {
                'total_requirements': len(chains),
                'complete_chains': complete,
                'errors': len(errors),
                'warnings': len(warnings),
                'annotated_files': len(annotations),
            },
        }
        print()
        print(json.dumps(output, indent=2))

    # Exit with error code if there are errors
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
