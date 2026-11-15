"""Contracts between deployment declarations; prevent silent runtime drift."""
import json
from pathlib import Path
import tomllib
ROOT=Path(__file__).resolve().parents[2]

def test_runtime_dependencies_match_vercel_and_requirements():
 project=tomllib.loads((ROOT/'website/pyproject.toml').read_text())
 requirements={line.strip() for line in (ROOT/'website/backend/requirements.txt').read_text().splitlines() if line.strip() and not line.startswith('#')}
 assert set(project['project']['dependencies'])==requirements
 assert project['project']['requires-python']=='>=3.12,<3.13'
 assert (ROOT/'website/backend/Dockerfile').read_text().startswith('FROM python:3.12-slim\n')

def test_build_defaults_to_vercel_but_preserves_live_sites():
 scripts=json.loads((ROOT/'website/site/package.json').read_text())['scripts']
 assert scripts['build']=='node build-static.mjs'
 assert scripts['build:static']=='npm run build'
 assert scripts['build:sites']=='node build.mjs'

def test_pinned_development_tools_are_separate_from_production():
 lines=(ROOT/'website/backend/requirements-dev.txt').read_text().splitlines()
 assert all('==' in line for line in lines if line and not line.startswith('#'))
 assert any(line.startswith('pytest==') for line in lines)
 assert 'ruff' not in (ROOT/'website/backend/requirements.txt').read_text()

def test_fixture_server_is_outside_vercel_root_and_excluded_from_production():
 fixture=ROOT/'tests/browser/support/server.py'
 assert fixture.exists()
 assert not fixture.is_relative_to(ROOT/'website')
 config=json.loads((ROOT/'website/vercel.json').read_text())
 assert 'backend/tests/**' in config['functions']['backend/site.py']['excludeFiles']
