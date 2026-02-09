#!/usr/bin/env python3
"""
gxpmd-harden.py — GxP.MD Compliance Sweep Tool

Executes the harden mode compliance sweep defined in GxP.MD v3.0.0.
Parses annotations from source and test files, builds a directed acyclic graph (DAG)
of traceability relationships using explicit edge tags, validates annotations,
and generates compliance reports.

v3 Key Changes:
- Replaces hierarchical ID-scheme-inferred traceability with explicit edge tags
- Uses @gxp-satisfies, @gxp-implements, @gxp-verifies, @gxp-derives-from
- Node IDs are opaque (REQ-NNN, US-NNN, SPEC-NNN) — no parent encoding
- Supports v2 legacy tags during migration period
- Graph-based coverage calculation via reachability analysis

Zero external dependencies — stdlib only.

Usage:
    python gxpmd-harden.py [--root PROJECT_ROOT] [--coverage COVERAGE_JSON]

Outputs:
    .gxp/traceability-matrix.json
    .gxp/compliance-status.md
    .gxp/gap-analysis.json
    .gxp/requirements/REQ-NNN.md   (stubs, when formal files don't exist)
    .gxp/specs/SPEC-NNN.md         (stubs, when formal files don't exist)
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
# Annotation regex patterns (v3 and legacy v2)
# ---------------------------------------------------------------------------

# v3 Edge tags — declare relationships between nodes
RE_GXP_SATISFIES = re.compile(r'@gxp-satisfies\s+((?:REQ-\d{3})(?:\s*,\s*REQ-\d{3})*)')
RE_GXP_IMPLEMENTS = re.compile(r'@gxp-implements\s+((?:(?:US|SPEC)-\d{3})(?:\s*,\s*(?:US|SPEC)-\d{3})*)')
RE_GXP_VERIFIES = re.compile(r'@gxp-verifies\s+((?:SPEC-\d{3})(?:\s*,\s*SPEC-\d{3})*)')
RE_GXP_DERIVES_FROM = re.compile(r'@gxp-derives-from\s+((?:(?:REQ|US|SPEC)-\d{3})(?:\s*,\s*(?:REQ|US|SPEC)-\d{3})*)')

# Legacy v2 tags for backward compatibility during migration
RE_GXP_REQ_LEGACY = re.compile(r'@gxp-req\s+(REQ-\d{3})(?:\s+"([^"]*)")?')
RE_GXP_SPEC_LEGACY = re.compile(r'@gxp-spec\s+(SPEC-\d{3}(?:-\d{3})?)(?:\s+"([^"]*)")?')
RE_TRACE_LEGACY = re.compile(r'@trace\s+(US-\d{3}(?:-\d{3})?)')

# Common tags (v2 and v3)
RE_GXP_RISK = re.compile(r'@gxp-risk\s+(HIGH|MEDIUM|LOW)')
RE_GXP_RISK_CONCERN = re.compile(r'@gxp-risk-concern\s+"([^"]*)"')
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
    'required_source_tags': ['@gxp-satisfies', '@gxp-implements', '@gxp-risk'],
    'required_test_tags': ['@gxp-verifies', '@test-type', '@gxp-risk'],
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

def _parse_id_list(match_str: str) -> list[str]:
    """Parse 'REQ-001, REQ-003' into ['REQ-001', 'REQ-003']"""
    return [id.strip() for id in match_str.split(',') if id.strip()]


def parse_annotations(filepath: Path, root: Path) -> dict:
    """Parse all GxP annotations from a single file.

    Returns dict with v3 edge tags and legacy v2 tags for backward compatibility.
    """
    try:
        content = filepath.read_text(encoding='utf-8', errors='replace')
    except (OSError, UnicodeDecodeError):
        return None

    rel_path = str(filepath.relative_to(root))
    is_test = _is_test_file(rel_path)

    # Parse v3 edge tags
    satisfies_match = RE_GXP_SATISFIES.search(content)
    satisfies_ids = _parse_id_list(satisfies_match.group(1)) if satisfies_match else []

    implements_match = RE_GXP_IMPLEMENTS.search(content)
    implements_ids = _parse_id_list(implements_match.group(1)) if implements_match else []

    verifies_match = RE_GXP_VERIFIES.search(content)
    verifies_ids = _parse_id_list(verifies_match.group(1)) if verifies_match else []

    derives_from_match = RE_GXP_DERIVES_FROM.search(content)
    derives_from_ids = _parse_id_list(derives_from_match.group(1)) if derives_from_match else []

    # Parse common tags
    risks = RE_GXP_RISK.findall(content)
    risk_concerns = RE_GXP_RISK_CONCERN.findall(content)
    test_types = RE_TEST_TYPE.findall(content)

    # Parse legacy v2 tags
    legacy_reqs = RE_GXP_REQ_LEGACY.findall(content)
    legacy_specs = RE_GXP_SPEC_LEGACY.findall(content)
    legacy_traces = RE_TRACE_LEGACY.findall(content)

    has_annotations = any([
        satisfies_ids, implements_ids, verifies_ids, derives_from_ids,
        legacy_reqs, legacy_specs, risks, risk_concerns, legacy_traces, test_types
    ])

    if not has_annotations:
        return None

    return {
        'file': rel_path,
        'is_test': is_test,
        'satisfies': satisfies_ids,
        'implements': implements_ids,
        'verifies': verifies_ids,
        'derives_from': derives_from_ids,
        'risk_levels': risks,
        'risk_concerns': risk_concerns,
        'test_types': test_types,
        # Legacy fields for backward compat:
        'requirements': [{'id': r[0], 'desc': r[1]} for r in legacy_reqs],
        'specifications': [{'id': s[0], 'desc': s[1]} for s in legacy_specs],
        'traces': legacy_traces,
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
# Traceability graph construction
# ---------------------------------------------------------------------------

_RISK_ORDER = {'HIGH': 3, 'MEDIUM': 2, 'LOW': 1, 'UNKNOWN': 0}


def _ensure_node(nodes, node_id, phase, risk=None, title=None, file=None):
    """Ensure a node exists in the graph with given properties."""
    if node_id not in nodes:
        nodes[node_id] = {'phase': phase, 'risk': risk, 'files': [], 'title': title, 'tiers': set()}
    if risk:
        existing_risk = nodes[node_id].get('risk')
        if not existing_risk or _RISK_ORDER.get(risk, 0) > _RISK_ORDER.get(existing_risk, 0):
            nodes[node_id]['risk'] = risk
    if title and not nodes[node_id].get('title'):
        nodes[node_id]['title'] = title
    if file and file not in nodes[node_id]['files']:
        nodes[node_id]['files'].append(file)


def _file_node_id(filepath: str) -> str:
    """Generate a deterministic node ID from a filepath."""
    return f'FILE:{filepath}'


def _infer_phase(node_id: str) -> str:
    """Infer the phase of a node from its ID prefix."""
    if node_id.startswith('REQ-'):
        return 'requirement'
    if node_id.startswith('US-'):
        return 'user_story'
    if node_id.startswith('SPEC-'):
        return 'specification'
    return 'unknown'


def build_traceability(annotations: list[dict]) -> dict:
    """Build the traceability DAG from explicit edge tags.

    v3: Uses @gxp-satisfies, @gxp-implements, @gxp-verifies edge tags
    instead of inferring relationships from ID encoding.
    """
    # Build adjacency list (DAG)
    nodes = {}  # id -> {phase, risk, title, files, tiers}
    edges = []  # list of {from, to, type, source_file}

    for ann in annotations:
        f = ann['file']
        risk = ann['risk_levels'][0] if ann['risk_levels'] else 'UNKNOWN'

        # Register nodes from edge tags
        for req_id in ann.get('satisfies', []):
            _ensure_node(nodes, req_id, 'requirement', risk=risk)
            # The file satisfies this requirement
            file_node_id = _file_node_id(f)
            _ensure_node(nodes, file_node_id, 'test' if ann['is_test'] else 'code', risk=risk, file=f)
            edges.append({'from': file_node_id, 'to': req_id, 'type': 'satisfies', 'source_file': f})

        for impl_id in ann.get('implements', []):
            phase = 'user_story' if impl_id.startswith('US-') else 'specification'
            _ensure_node(nodes, impl_id, phase, risk=risk)
            file_node_id = _file_node_id(f)
            _ensure_node(nodes, file_node_id, 'test' if ann['is_test'] else 'code', risk=risk, file=f)
            edges.append({'from': file_node_id, 'to': impl_id, 'type': 'implements', 'source_file': f})

        for ver_id in ann.get('verifies', []):
            _ensure_node(nodes, ver_id, 'specification', risk=risk)
            file_node_id = _file_node_id(f)
            _ensure_node(nodes, file_node_id, 'test' if ann['is_test'] else 'code', risk=risk, file=f)
            edges.append({'from': file_node_id, 'to': ver_id, 'type': 'verifies', 'source_file': f})
            # Record test tiers for this verification
            for tier in ann.get('test_types', []):
                nodes[file_node_id].setdefault('tiers', set()).add(tier)

        for der_id in ann.get('derives_from', []):
            phase = _infer_phase(der_id)
            _ensure_node(nodes, der_id, phase)
            # @gxp-derives-from creates a dependency edge: the artifact declared
            # by this file's other edge tags (satisfies/implements/verifies) depends
            # on der_id. E.g., if file declares @gxp-implements SPEC-002 and
            # @gxp-derives-from SPEC-001, the edge is SPEC-002 → SPEC-001
            # (meaning SPEC-002 derives from / depends on SPEC-001).
            for own_id in ann.get('satisfies', []) + ann.get('implements', []) + ann.get('verifies', []):
                edges.append({'from': own_id, 'to': der_id, 'type': 'derives_from', 'source_file': f})

        # Legacy v2 compat: convert old tags to edges
        for r in ann.get('requirements', []):
            _ensure_node(nodes, r['id'], 'requirement', title=r.get('desc'))
            file_node_id = _file_node_id(f)
            _ensure_node(nodes, file_node_id, 'test' if ann['is_test'] else 'code', risk=risk, file=f)
            edges.append({'from': file_node_id, 'to': r['id'], 'type': 'satisfies', 'source_file': f})

        for s in ann.get('specifications', []):
            _ensure_node(nodes, s['id'], 'specification', title=s.get('desc'))
            file_node_id = _file_node_id(f)
            _ensure_node(nodes, file_node_id, 'test' if ann['is_test'] else 'code', risk=risk, file=f)
            edge_type = 'verifies' if ann['is_test'] else 'implements'
            edges.append({'from': file_node_id, 'to': s['id'], 'type': edge_type, 'source_file': f})

        for us_id in ann.get('traces', []):
            _ensure_node(nodes, us_id, 'user_story')
            file_node_id = _file_node_id(f)
            _ensure_node(nodes, file_node_id, 'test' if ann['is_test'] else 'code', risk=risk, file=f)
            edges.append({'from': file_node_id, 'to': us_id, 'type': 'verifies', 'source_file': f})

    # Calculate coverage via graph reachability
    coverage = _calculate_coverage(nodes, edges)

    return {
        'nodes': nodes,
        'edges': edges,
        'coverage': coverage,
    }


def _calculate_coverage(nodes, edges):
    """Calculate which requirements are covered via graph reachability.

    A requirement is covered if there exists a path connecting a test node
    to the requirement through the edge graph (undirected traversal).

    Undirected traversal is necessary because edges point from satisfier
    to satisfied (e.g., FILE:src → REQ, FILE:test → SPEC, FILE:src → SPEC).
    A typical multi-hop path crosses through shared SPEC nodes:
    FILE:test → SPEC ← FILE:src → REQ. Reverse-only traversal from REQ
    would reach FILE:src but dead-end without discovering the test node.
    """
    # Build undirected adjacency list (both directions)
    undirected_adj = defaultdict(list)
    for edge in edges:
        undirected_adj[edge['to']].append(edge['from'])
        undirected_adj[edge['from']].append(edge['to'])

    # For each requirement, check if any test node is connected
    req_nodes = {nid: n for nid, n in nodes.items() if n['phase'] == 'requirement'}
    coverage = {}

    for req_id, req_node in req_nodes.items():
        # BFS: find all nodes connected to this requirement
        visited = set()
        queue = [req_id]
        visited.add(req_id)
        test_nodes_found = []

        while queue:
            current = queue.pop(0)
            for neighbor in undirected_adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    # Check if this is a test node
                    if neighbor in nodes:
                        if nodes[neighbor].get('phase') == 'test':
                            test_nodes_found.append(neighbor)
                        elif neighbor.startswith('FILE:') and _is_test_file(neighbor[5:]):
                            test_nodes_found.append(neighbor)

        coverage[req_id] = {
            'risk': req_node.get('risk', 'UNKNOWN'),
            'covered': len(test_nodes_found) > 0,
            'test_nodes': test_nodes_found,
            'reachable_nodes': len(visited),
        }

    return coverage


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_annotations(annotations: list[dict], config: dict) -> list[dict]:
    """Validate annotation format and completeness. Returns list of issues."""
    issues = []

    for ann in annotations:
        f = ann['file']
        risk_levels = ann['risk_levels']
        has_edges = (ann.get('satisfies') or ann.get('implements') or
                     ann.get('verifies') or ann.get('derives_from'))
        has_legacy = (ann.get('requirements') or ann.get('specifications') or ann.get('traces'))

        if ann['is_test']:
            if not ann.get('verifies') and not ann.get('specifications'):
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Test file missing @gxp-verifies (or legacy @gxp-spec) annotation'
                })
            if not ann['test_types']:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Test file missing @test-type annotation'
                })
            if not risk_levels:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Test file missing @gxp-risk annotation'
                })
        else:
            if not has_edges and not has_legacy:
                if risk_levels and risk_levels[0] != 'LOW':
                    issues.append({
                        'file': f, 'severity': 'ERROR',
                        'message': 'Source file has no traceability edge tags (@gxp-satisfies, @gxp-implements)'
                    })
            if not risk_levels:
                issues.append({
                    'file': f, 'severity': 'ERROR',
                    'message': 'Source file missing @gxp-risk annotation'
                })

        # Warn about legacy tags (v2)
        if has_legacy and not has_edges:
            issues.append({
                'file': f, 'severity': 'WARNING',
                'message': 'File uses v2 legacy tags (@gxp-req/@gxp-spec/@trace). Migrate to v3 edge tags (@gxp-satisfies/@gxp-implements/@gxp-verifies)'
            })

        if len(set(risk_levels)) > 1:
            issues.append({
                'file': f, 'severity': 'WARNING',
                'message': f'File has mixed risk levels: {", ".join(set(risk_levels))}'
            })

    return issues


def find_orphans(traceability: dict, _annotations: list[dict]) -> list[dict]:
    """Find nodes with no incoming or outgoing edges (disconnected from graph)."""
    issues = []
    nodes = traceability['nodes']
    edges = traceability['edges']

    # Build sets of nodes with edges
    nodes_with_outgoing = set(e['from'] for e in edges)
    nodes_with_incoming = set(e['to'] for e in edges)

    for node_id, node in nodes.items():
        if node_id.startswith('FILE:'):
            continue  # File nodes are always connected by definition

        has_outgoing = node_id in nodes_with_outgoing
        has_incoming = node_id in nodes_with_incoming

        if not has_outgoing and not has_incoming:
            issues.append({
                'node': node_id,
                'severity': 'ERROR' if node.get('risk') == 'HIGH' else 'WARNING',
                'message': f'{node_id} is completely disconnected from the traceability graph',
            })
        elif node['phase'] == 'requirement' and not has_incoming:
            # Requirements should have at least one incoming edge (something satisfies them)
            issues.append({
                'node': node_id,
                'severity': 'WARNING',
                'message': f'{node_id} has no code or specs satisfying it',
            })
        elif node['phase'] == 'specification' and not has_incoming:
            issues.append({
                'node': node_id,
                'severity': 'WARNING',
                'message': f'{node_id} has no tests verifying it',
            })

    return issues


def analyze_coverage(traceability: dict, config: dict,
                     coverage_data: dict | None) -> list[dict]:
    """Check coverage thresholds and tier requirements."""
    issues = []
    matrix = config['risk_matrix']
    nodes = traceability['nodes']
    edges = traceability['edges']

    # Extract requirement nodes
    req_nodes = {nid: n for nid, n in nodes.items() if n['phase'] == 'requirement'}

    # Build undirected adjacency once for all requirements
    undirected_adj = defaultdict(list)
    for edge in edges:
        undirected_adj[edge['to']].append(edge['from'])
        undirected_adj[edge['from']].append(edge['to'])

    for req_id, req_node in req_nodes.items():
        risk = req_node.get('risk', 'UNKNOWN')
        if risk == 'UNKNOWN':
            issues.append({
                'requirement': req_id,
                'severity': 'WARNING',
                'message': 'No risk level assigned',
            })
            continue

        level_config = matrix.get(risk, {})
        required_tiers = set(level_config.get('required_tiers', []))

        # Find all test nodes connected to this requirement via undirected BFS
        test_tiers = set()
        queue = [req_id]
        visited = set([req_id])
        test_files = []

        while queue:
            current = queue.pop(0)
            for neighbor in undirected_adj.get(current, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)
                    if neighbor in nodes and nodes[neighbor].get('phase') == 'test':
                        test_tiers.update(nodes[neighbor].get('tiers', set()))
                        if 'files' in nodes[neighbor]:
                            test_files.extend(nodes[neighbor]['files'])

        missing_tiers = required_tiers - test_tiers
        if missing_tiers:
            issues.append({
                'requirement': req_id,
                'severity': 'ERROR',
                'message': f'{risk} risk requires tiers {sorted(required_tiers)} '
                           f'but only {sorted(test_tiers)} present. '
                           f'Missing: {sorted(missing_tiers)}',
            })

        if not test_files:
            issues.append({
                'requirement': req_id,
                'severity': 'ERROR',
                'message': 'No test files found for this requirement',
            })

        # Coverage threshold check (if coverage data available)
        if coverage_data:
            threshold = level_config.get('coverage_threshold', 0)
            for src in req_node.get('files', []):
                file_cov = _get_file_coverage(src, coverage_data)
                if file_cov is not None and file_cov < threshold:
                    issues.append({
                        'requirement': req_id,
                        'severity': 'ERROR',
                        'message': f'{src}: coverage {file_cov:.1f}% < '
                                   f'{threshold}% threshold for {risk} risk',
                    })

    return issues


def _get_file_coverage(filepath: str, coverage_data: dict) -> float | None:
    """Extract coverage percentage for a file from coverage-summary.json format."""
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

def generate_traceability_matrix(traceability, config, project_root):
    """Generate the .gxp/traceability-matrix.json output."""
    now = datetime.now(timezone.utc).isoformat()
    nodes = traceability['nodes']
    edges = traceability['edges']
    coverage = traceability['coverage']

    nodes_output = {}
    for nid, n in sorted(nodes.items()):
        nodes_output[nid] = {
            'phase': n['phase'],
            'risk': n.get('risk'),
            'title': n.get('title'),
            'files': n.get('files', []),
            'tiers': sorted(n.get('tiers', set())),
            'covered': coverage.get(nid, {}).get('covered', False) if n['phase'] == 'requirement' else None,
        }

    edges_output = []
    for e in edges:
        edges_output.append({
            'from': e['from'],
            'to': e['to'],
            'type': e['type'],
            'source_file': e.get('source_file')
        })

    # Coverage summary by risk
    coverage_by_risk = defaultdict(lambda: {'total': 0, 'covered': 0})
    for req_id, cov in coverage.items():
        risk = cov.get('risk', 'UNKNOWN')
        coverage_by_risk[risk]['total'] += 1
        if cov.get('covered'):
            coverage_by_risk[risk]['covered'] += 1

    for risk in coverage_by_risk:
        t = coverage_by_risk[risk]['total']
        c = coverage_by_risk[risk]['covered']
        coverage_by_risk[risk]['percentage'] = round((c / t * 100) if t > 0 else 0, 1)

    return {
        'gxpmd_version': '3.0.0',
        'generated_at': now,
        'project_root': str(project_root),
        'summary': {
            'total_nodes': len(nodes_output),
            'total_edges': len(edges_output),
            'total_requirements': len(coverage),
            'covered_requirements': sum(1 for c in coverage.values() if c.get('covered')),
            'coverage_by_risk': dict(coverage_by_risk),
        },
        'nodes': nodes_output,
        'edges': edges_output,
        'coverage': {k: {
            'risk': v['risk'],
            'covered': v['covered'],
            'test_nodes': v.get('test_nodes', []),
            'reachable_nodes': v.get('reachable_nodes', 0),
        } for k, v in coverage.items()},
    }


def generate_compliance_status(traceability, validation_issues, orphan_issues, coverage_issues,
                                annotations, _config, risk_concerns=None, stub_summary=None):
    """Generate .gxp/compliance-status.md report."""
    now = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
    nodes = traceability['nodes']
    coverage = traceability['coverage']

    # Count coverage by status
    total_reqs = len(coverage)
    covered_reqs = sum(1 for c in coverage.values() if c.get('covered'))
    uncovered_reqs = total_reqs - covered_reqs

    annotated_source = sum(1 for a in annotations if not a['is_test'])
    annotated_test = sum(1 for a in annotations if a['is_test'])

    all_issues = validation_issues + orphan_issues + coverage_issues
    errors = [i for i in all_issues if i.get('severity') == 'ERROR']
    warnings = [i for i in all_issues if i.get('severity') == 'WARNING']

    # Risk distribution
    req_nodes = {nid: n for nid, n in nodes.items() if n['phase'] == 'requirement'}
    high_risk = [nid for nid, n in req_nodes.items() if n.get('risk') == 'HIGH']
    medium_risk = [nid for nid, n in req_nodes.items() if n.get('risk') == 'MEDIUM']
    low_risk = [nid for nid, n in req_nodes.items() if n.get('risk') == 'LOW']

    lines = [
        '# Compliance Status Report',
        '',
        f'Generated: {now}',
        'GxP.MD Version: 3.0.0',
        '',
        '---',
        '',
        '## Summary',
        '',
        '| Metric | Value |',
        '|--------|-------|',
        f'| Total requirements | {total_reqs} |',
        f'| Covered requirements | {covered_reqs}/{total_reqs} |',
        f'| Uncovered requirements | {uncovered_reqs}/{total_reqs} |',
        f'| Annotated source files | {annotated_source} |',
        f'| Annotated test files | {annotated_test} |',
        f'| Errors | {len(errors)} |',
        f'| Warnings | {len(warnings)} |',
        '',
        '## Risk Distribution',
        '',
        '| Risk Level | Requirements | Covered |',
        '|------------|-------------|---------|',
        f'| HIGH | {len(high_risk)} | {sum(1 for r in high_risk if coverage[r].get("covered"))}/{len(high_risk)} |',
        f'| MEDIUM | {len(medium_risk)} | {sum(1 for r in medium_risk if coverage[r].get("covered"))}/{len(medium_risk)} |',
        f'| LOW | {len(low_risk)} | {sum(1 for r in low_risk if coverage[r].get("covered"))}/{len(low_risk)} |',
        '',
    ]

    if errors:
        lines.extend([
            '## Errors',
            '',
        ])
        for issue in errors:
            loc = issue.get('file', issue.get('node', issue.get('requirement', '?')))
            lines.append(f'- **{loc}**: {issue["message"]}')
        lines.append('')

    if warnings:
        lines.extend([
            '## Warnings',
            '',
        ])
        for issue in warnings:
            loc = issue.get('file', issue.get('node', issue.get('requirement', '?')))
            lines.append(f'- **{loc}**: {issue["message"]}')
        lines.append('')

    # Traceability details
    lines.extend([
        '## Traceability Coverage',
        '',
    ])
    for req_id in sorted(req_nodes.keys()):
        cov = coverage.get(req_id, {})
        status_icon = 'PASS' if cov.get('covered') else 'FAIL'
        risk = req_nodes[req_id].get('risk', 'UNKNOWN')
        lines.append(f'### {req_id} [{status_icon}]')
        lines.append('')
        lines.append(f'- **Risk**: {risk}')
        lines.append(f'- **Coverage**: {"Verified" if cov.get("covered") else "Not verified"}')
        if cov.get('test_nodes'):
            lines.append(f'- **Test Nodes**: {", ".join(cov["test_nodes"][:5])}')
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


def generate_gap_analysis(validation_issues, orphan_issues, coverage_issues):
    """Generate .gxp/gap-analysis.json output."""
    now = datetime.now(timezone.utc).isoformat()
    all_issues = validation_issues + orphan_issues + coverage_issues

    return {
        'generated_at': now,
        'gxpmd_version': '3.0.0',
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

def generate_artifact_stubs(traceability, annotations, config, project_root):
    """Generate stub REQ-NNN.md and SPEC-NNN.md files for annotations
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

    nodes = traceability['nodes']
    edges = traceability['edges']

    # Collect all requirement descriptions from annotations
    req_descs = {}
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
            if ann['is_test']:
                spec_tests[s['id']].append(ann['file'])
            else:
                spec_sources[s['id']].append(ann['file'])

    # Generate requirement stubs
    req_nodes = {nid: n for nid, n in nodes.items() if n['phase'] == 'requirement'}
    for req_id, req_node in req_nodes.items():
        req_file = req_dir / f'{req_id}.md'

        if req_file.exists():
            skipped.append(str(req_file.relative_to(project_root)))
            continue

        desc = req_descs.get(req_id, 'No description available from annotations')
        risk = req_node.get('risk', 'UNKNOWN')

        # Find specs that implement this requirement via edges
        linked_specs = []
        for edge in edges:
            if edge['to'] == req_id and edge['type'] == 'satisfies':
                # Find what satisfies this req
                for e2 in edges:
                    if e2['from'] == edge['from'] and e2['type'] == 'implements':
                        linked_specs.append(e2['to'])

        content = (
            '---\n'
            f'gxp_id: {req_id}\n'
            f'title: "{desc}"\n'
            f'description: "{desc}"\n'
            f'risk_level: {risk}\n'
            'acceptance_criteria:\n'
            '  - "TODO: Define acceptance criteria"\n'
            'validation_status: draft\n'
            f'created: "{now}"\n'
            f'updated: "{now}"\n'
            'author: "generated-by-gxpmd-harden"\n'
            '---\n\n'
            f'# {req_id}: {desc}\n\n'
            '> This stub was auto-generated by `gxpmd-harden.py` from source annotations.\n'
            '> Review and flesh out for HIGH risk components.\n\n'
        )

        if linked_specs:
            content += '## Linked Specifications\n\n'
            for sid in sorted(set(linked_specs)):
                content += f'- {sid}\n'
            content += '\n'

        content += (
            '## Regulatory Basis\n\n'
            'TODO: Document the regulatory basis for this requirement.\n\n'
            '## Risk Justification\n\n'
            f'Classified as **{risk}** risk.\n'
            'TODO: Document impact analysis and risk justification.\n'
        )

        req_file.write_text(content, encoding='utf-8')
        created_reqs.append(str(req_file.relative_to(project_root)))

    # Generate specification stubs
    spec_nodes = {nid: n for nid, n in nodes.items() if n['phase'] == 'specification'}
    for spec_id, spec_node in spec_nodes.items():
        spec_file = spec_dir / f'{spec_id}.md'

        if spec_file.exists():
            skipped.append(str(spec_file.relative_to(project_root)))
            continue

        desc = spec_descs.get(spec_id, 'No description available from annotations')
        sources = sorted(set(spec_sources.get(spec_id, [])))
        tests = sorted(set(spec_tests.get(spec_id, [])))

        content = (
            '---\n'
            f'gxp_id: {spec_id}\n'
            f'title: "{desc}"\n'
            'verification_tier: OQ\n'
            'design_approach: "TODO: Describe implementation approach"\n'
            'source_files:\n'
        )
        for src in sources:
            content += f'  - "{src}"\n'
        if not sources:
            content += '  - "TODO: Link source files"\n'
        content += 'test_files:\n'
        for tst in tests:
            content += f'  - "{tst}"\n'
        if not tests:
            content += '  - "TODO: Link test files"\n'
        content += (
            'validation_status: draft\n'
            f'created: "{now}"\n'
            f'updated: "{now}"\n'
            'author: "generated-by-gxpmd-harden"\n'
            '---\n\n'
            f'# {spec_id}: {desc}\n\n'
            '> This stub was auto-generated by `gxpmd-harden.py` from source annotations.\n'
            '> Review and flesh out for HIGH risk components.\n\n'
            '## Design Approach\n\n'
            'TODO: Document the technical design.\n\n'
            '## Data Flow\n\n'
            'TODO: Document data flows and security considerations.\n'
        )

        spec_file.write_text(content, encoding='utf-8')
        created_specs.append(str(spec_file.relative_to(project_root)))

    return {
        'created_requirements': created_reqs,
        'created_specifications': created_specs,
        'skipped_existing': skipped,
    }


def collect_risk_concerns(annotations):
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
        description='GxP.MD v3.0.0 Compliance Sweep Tool',
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
        sys.exit(2)

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
    print('Building traceability graph...')
    traceability = build_traceability(annotations)

    # 6. Find orphans
    print('Checking for orphan nodes...')
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

    # 11. Summary
    all_issues = validation_issues + orphan_issues + coverage_issues
    errors = [i for i in all_issues if i.get('severity') == 'ERROR']
    warnings = [i for i in all_issues if i.get('severity') == 'WARNING']

    nodes = traceability['nodes']
    coverage = traceability['coverage']
    req_nodes = {nid: n for nid, n in nodes.items() if n['phase'] == 'requirement'}
    covered = sum(1 for r in req_nodes if coverage.get(r, {}).get('covered'))

    print()
    print('=' * 60)
    print('  GxP.MD COMPLIANCE SWEEP COMPLETE')
    print('=' * 60)
    print(f'  Requirements:       {len(req_nodes)}')
    print(f'  Covered:            {covered}/{len(req_nodes)}')
    print(f'  Errors:             {len(errors)}')
    print(f'  Warnings:           {len(warnings)}')
    print(f'  Annotated files:    {len(annotations)}')
    print('=' * 60)

    if errors:
        print()
        print('ERRORS:')
        for issue in errors:
            loc = issue.get('file', issue.get('node', issue.get('requirement', '?')))
            print(f'  [{loc}] {issue["message"]}')

    if args.json:
        output = {
            'traceability_matrix': matrix,
            'gap_analysis': gaps,
            'summary': {
                'total_requirements': len(req_nodes),
                'covered_requirements': covered,
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
