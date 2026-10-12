"""Checker-only falsification of recovery completion; no product writes."""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'tests'))
from crawl_fake import grant_crawl_approval, make_project, make_session
from autotester.browser.observe import PageObserver
from autotester.schema.enums import NodeStatus
from autotester.schema.screen_graph import ScreenNode
from autotester.stages import explore_node
from autotester.stages.explore import run_crawl
from autotester.stages.explore_status import terminal_status, is_success
from autotester.store.project_store import ProjectStore

os.environ['AUTOTESTER_APPROVAL_KEY'] = 'checker-local-fixture-only-key'

n = ScreenNode(crawl_id='fixture', project='demo', url_example='https://demo.test/dashboard',
               url_template='/dashboard', signature='abc', status=NodeStatus.ABORTED_ERROR)
print('TERMINAL', terminal_status(completed=True, actions_used=0, denied=0, nodes=[n],
      edges=[], login_case=None, current_stop_reason='frontier empty'))
with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as scratch:
    root = Path(scratch)
    project = make_project()
    session, _ = make_session(root, project)
    store = ProjectStore('demo', root)
    grant_crawl_approval(store, project)
    real = explore_node.return_to
    explore_node.return_to = lambda rt, node: False
    try:
        crawl = run_crawl(project, session, store, observer=PageObserver())
        print('RUN', json.dumps({'status': crawl.status.value, 'stop_reason': crawl.stop_reason,
              'actions': crawl.actions, 'nodes': [x.status.value for x in store.list_nodes(crawl.id)],
              'success': is_success(crawl), 'issues': crawl.issues}))
    finally:
        explore_node.return_to = real

for crawl_id in ['crawl_01M3S02YPQRV6S65GEY5TTCCVK', 'crawl_01M3S0K5CZCKYR4M1J3BPNPHMX']:
    path = Path(__file__).resolve().parents[2] / 'projects/pathlynks/crawl' / crawl_id
    data = json.loads((path / 'crawl.json').read_text(encoding='utf-8'))
    nodes = [json.loads(line) for line in (path / 'nodes.jsonl').read_text(encoding='utf-8').splitlines() if line]
    print('STORED', json.dumps({'id': crawl_id, 'status': data['status'],
          'actions': data['actions'], 'stop_reason': data['stop_reason'],
          'nodes': [x['status'] for x in nodes],
          'coverage': {k: data.get('coverage', {}).get(k) for k in
                       ['controls_discovered', 'controls_exercised', 'percent']}}))
