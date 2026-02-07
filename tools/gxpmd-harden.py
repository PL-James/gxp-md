#!/usr/bin/env python3
"""
gxpmd-harden.py — GxP.MD Compliance Sweep Tool

Executes the harden mode compliance sweep defined in GxP.MD v2.1.0.
Parses annotations from source and test files, builds the traceability
matrix, validates annotation chains, and generates compliance reports.

Zero external dependencies — stdlib only.

Usage:
    python gxpmd-harden.py [--root PROJECT_ROOT] [--coverage COVERAGE_JSON]

Outputs:
    .gxp/traceability-matrix.json
    .gxp/compliance-status.md
    .gxp/gap-analysis.json
    .gxp/requirements/REQ-NNN.md   (stubs, when formal files don't exist)
    .gxp/specs/SPEC-NNN-NNN.md     (stubs, when formal files don't exist)
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
RE_GXP_RISK_CONCERN = re.compile(r'@gxp-risk-concern\s+"([^"]*)"')
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
    risk_concerns = RE_GXP_RISK_CONCERN.findall(content)
    traces = RE_TRACE.findall(content)
    test_types = RE_TEST_TYPE.findall(content)

    if not any([reqs, specs, risks, traces, test_types, risk_concerns]):
        return None

    return {
        'file': rel_path,
        'is_test': is_test,
        'requirements': [{'id': r[0], 'desc': r[1]} for r in reqs],
        'specifications': [{'id': s[0], 'desc': s[1]} for s in specs],
        'risk_levels': risks,
        'risk_concerns': risk_concerns,
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
        'gxpmd_version': '2.1.0',
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
                                annotations: list, config: dict,
                                risk_concerns: list | None = None,
                                stub_summary: dict | None = None) -> str:
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
        'GxP.MD Version: 2.1.0',
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

    # Risk concerns section
    if risk_concerns:
        lines.extend([
            '## Risk Classification Concerns',
            '',
            '| File | Current Risk | Concern |',
            '|------|-------------|---------|',
        ])
        for rc in risk_concerns:
            lines.append(f'| {rc["file"]} | {rc["current_risk"]} | {rc["concern"]} |')
        lines.append('')
        lines.append('*These concerns require human review. See `.gxp/risk_assessment.log` for details.*')
        lines.append('')

    # Artifact stubs section
    if stub_summary:
        created = (stub_summary.get('created_requirements', []) +
                   stub_summary.get('created_specifications', []))
        if created:
            lines.extend([
                '## Generated Artifact Stubs',
                '',
            ])
            for f in created:
                lines.append(f'- `{f}` (draft — review recommended)')
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
        'gxpmd_version': '2.1.0',
        'total_issues': len(all_issues),
        'errors': len([i for i in all_issues if i.get('severity') == 'ERROR']),
        'warnings': len([i for i in all_issues if i.get('severity') == 'WARNING']),
        'validation_issues': validation_issues,
        'orphan_issues': orphan_issues,
        'coverage_issues': coverage_issues,
    }


# ---------------------------------------------------------------------------
# Artifact stub generation
# ---------------------------------------------------------------------------

def generate_artifact_stubs(traceability: dict, annotations: list[dict],
                             config: dict, project_root: Path) -> dict:
    """Generate stub REQ-NNN.md and SPEC-NNN-NNN.md files for annotations
    that lack corresponding formal artifact files. Returns summary of actions."""
    gxp_dir = project_root / config['artifacts_dir']
    req_dir = gxp_dir / 'requirements'
    spec_dir = gxp_dir / 'specs'
    req_dir.mkdir(parents=True, exist_ok=True)
    spec_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    created_reqs = []
    created_specs = []
    skipped = []

    # Collect all requirement descriptions from annotations
    req_descs = {}
    req_risks = {}
    req_specs_map = defaultdict(set)
    spec_descs = {}
    spec_sources = defaultdict(list)
    spec_tests = defaultdict(list)

    for ann in annotations:
        for r in ann['requirements']:
            if r['desc']:
                req_descs[r['id']] = r['desc']
        for s in ann['specifications']:
            if s['desc']:
                spec_descs[s['id']] = s['desc']
            req_id = _spec_to_req(s['id'])
            if req_id:
                req_specs_map[req_id].add(s['id'])
            if ann['is_test']:
                spec_tests[s['id']].append(ann['file'])
            else:
                spec_sources[s['id']].append(ann['file'])
        for risk in ann['risk_levels']:
            for r in ann['requirements']:
                req_risks[r['id']] = risk

    # Generate requirement stubs
    for chain in traceability['chains']:
        req_id = chain['requirement']
        req_file = req_dir / f'{req_id}.md'

        if req_file.exists():
            skipped.append(str(req_file.relative_to(project_root)))
            continue

        desc = req_descs.get(req_id, 'No description available from annotations')
        risk = chain['risk_level']
        specs = sorted(chain['specifications'])

        content = (
            f'---\n'
            f'gxp_id: {req_id}\n'
            f'title: "{desc}"\n'
            f'parent_id: null\n'
            f'description: "{desc}"\n'
            f'risk_level: {risk}\n'
            f'acceptance_criteria:\n'
            f'  - "TODO: Define acceptance criteria"\n'
            f'validation_status: draft\n'
            f'created: "{now}"\n'
            f'updated: "{now}"\n'
            f'author: "generated-by-gxpmd-harden"\n'
            f'---\n\n'
            f'# {req_id}: {desc}\n\n'
            f'> This stub was auto-generated by `gxpmd-harden.py` from source annotations.\n'
            f'> Review and flesh out for HIGH risk components.\n\n'
            f'## Linked Specifications\n\n'
        )
        for sid in specs:
            content += f'- {sid}\n'
        content += (
            f'\n## Regulatory Basis\n\n'
            f'TODO: Document the regulatory basis for this requirement.\n\n'
            f'## Risk Justification\n\n'
            f'Classified as **{risk}** risk.\n'
            f'TODO: Document impact analysis and risk justification.\n'
        )

        req_file.write_text(content, encoding='utf-8')
        created_reqs.append(str(req_file.relative_to(project_root)))

    # Generate specification stubs
    all_spec_ids = set(traceability['all_spec_ids'])
    for spec_id in sorted(all_spec_ids):
        spec_file = spec_dir / f'{spec_id}.md'

        if spec_file.exists():
            skipped.append(str(spec_file.relative_to(project_root)))
            continue

        desc = spec_descs.get(spec_id, 'No description available from annotations')
        us_id = _spec_to_us(spec_id)
        sources = sorted(set(spec_sources.get(spec_id, [])))
        tests = sorted(set(spec_tests.get(spec_id, [])))

        content = (
            f'---\n'
            f'gxp_id: {spec_id}\n'
            f'title: "{desc}"\n'
            f'parent_id: {us_id or "null"}\n'
            f'verification_tier: OQ\n'
            f'design_approach: "TODO: Describe implementation approach"\n'
            f'source_files:\n'
        )
        for src in sources:
            content += f'  - "{src}"\n'
        if not sources:
            content += f'  - "TODO: Link source files"\n'
        content += f'test_files:\n'
        for tst in tests:
            content += f'  - "{tst}"\n'
        if not tests:
            content += f'  - "TODO: Link test files"\n'
        content += (
            f'validation_status: draft\n'
            f'created: "{now}"\n'
            f'updated: "{now}"\n'
            f'author: "generated-by-gxpmd-harden"\n'
            f'---\n\n'
            f'# {spec_id}: {desc}\n\n'
            f'> This stub was auto-generated by `gxpmd-harden.py` from source annotations.\n'
            f'> Review and flesh out for HIGH risk components.\n\n'
            f'## Design Approach\n\n'
            f'TODO: Document the technical design.\n\n'
            f'## Data Flow\n\n'
            f'TODO: Document data flows and security considerations.\n'
        )

        spec_file.write_text(content, encoding='utf-8')
        created_specs.append(str(spec_file.relative_to(project_root)))

    return {
        'created_requirements': created_reqs,
        'created_specifications': created_specs,
        'skipped_existing': skipped,
    }


def collect_risk_concerns(annotations: list[dict]) -> list[dict]:
    """Collect all @gxp-risk-concern annotations across the codebase."""
    concerns = []
    for ann in annotations:
        for concern in ann.get('risk_concerns', []):
            concerns.append({
                'file': ann['file'],
                'current_risk': ann['risk_levels'][0] if ann['risk_levels'] else 'UNKNOWN',
                'concern': concern,
            })
    return concerns


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='GxP.MD v2.1.0 Compliance Sweep Tool',
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

    # 8. Generate artifact stubs
    print('Generating artifact stubs...')
    stub_summary = generate_artifact_stubs(traceability, annotations, config, root)
    if stub_summary['created_requirements']:
        for f in stub_summary['created_requirements']:
            print(f'  Created {f}')
    if stub_summary['created_specifications']:
        for f in stub_summary['created_specifications']:
            print(f'  Created {f}')
    if not stub_summary['created_requirements'] and not stub_summary['created_specifications']:
        print('  No stubs needed (all formal files exist or no annotations found)')

    # 9. Collect risk concerns
    risk_concerns = collect_risk_concerns(annotations)
    if risk_concerns:
        print(f'Found {len(risk_concerns)} risk classification concern(s)')

    # 10. Generate outputs
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
        annotations, config, risk_concerns=risk_concerns,
        stub_summary=stub_summary,
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
