"""The raw CSS/font-link template for every page. Split out of `theme.py`
(which was pushing past the 300-line design limit once the flow-diagram
tree CSS was added) — `theme.py` keeps the Python component functions that
build page fragments; this module is pure style, imported once.
"""

from __future__ import annotations

PAGE_STYLE = """
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,650;1,500&display=swap"
      rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&display=swap"
      rel="stylesheet">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&display=swap"
      rel="stylesheet">
<style>
  :root {
    color-scheme: light dark;
    --bg: #faf7f2; --surface: #ffffff; --surface-raised: #ffffff; --border: #e6e0d4;
    --text: #201d16; --text-dim: #6b6455; --muted: #a49c8a;
    --accent: #c2410c; --accent-hover: #9a3412; --accent-text: #fff8f0; --accent-dim: #fbe7d9;
    --success: #15803d; --success-bg: #eaf5ec; --danger: #b91c1c; --danger-bg: #fbebeb;
    --blocked: #b45309; --blocked-bg: #fdf0dc; --neutral-bg: #efece3;
    --radius: 6px; --radius-lg: 10px;
    --shadow: 0 1px 2px rgba(32,29,22,.05), 0 2px 8px rgba(32,29,22,.06);
    --shadow-lift: 0 4px 16px rgba(32,29,22,.10);
    --font-display: "Fraunces", Georgia, serif;
    --font-body: "IBM Plex Sans", -apple-system, "Segoe UI", sans-serif;
    --font-mono: "IBM Plex Mono", ui-monospace, "SF Mono", Consolas, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --bg: #17140f; --surface: #211d16; --surface-raised: #2a251c; --border: #3a3323;
      --text: #f3ede0; --text-dim: #b3a890; --muted: #7d735c;
      --accent: #f0803c; --accent-hover: #f79a63; --accent-text: #1a0f04; --accent-dim: #3a2210;
      --success: #4ade80; --success-bg: #142a1c; --danger: #f87171; --danger-bg: #2e1616;
      --blocked: #fbbf24; --blocked-bg: #2e2210; --neutral-bg: #2a251c;
      --shadow: 0 1px 2px rgba(0,0,0,.3); --shadow-lift: 0 8px 24px rgba(0,0,0,.4);
    }
  }
  * { box-sizing: border-box; }
  body {
    background: var(--bg); color: var(--text); margin: 0; font-family: var(--font-body);
    line-height: 1.55; -webkit-font-smoothing: antialiased;
    background-image: radial-gradient(var(--border) 0.6px, transparent 0.6px);
    background-size: 22px 22px; background-attachment: fixed;
  }
  .layout { display: flex; align-items: flex-start; }
  main { max-width: 960px; margin: 0 auto; padding: 2.5rem 1.75rem 5rem; flex: 1; min-width: 0; }

  .sidebar { width: 220px; flex-shrink: 0; border-right: 1px solid var(--border);
             background: var(--surface); padding: 1.6rem 1.1rem; position: sticky;
             top: 65px; align-self: flex-start; max-height: calc(100vh - 65px);
             overflow-y: auto; }
  .sidebar-header { font-family: var(--font-mono); font-size: .68rem; text-transform: uppercase;
                     letter-spacing: .06em; color: var(--text-dim); margin-bottom: .8rem; }
  .sidebar-nav { display: flex; flex-direction: column; gap: .15rem; }
  .sidebar-link { display: block; padding: .45rem .6rem; border-radius: var(--radius);
                   color: var(--text-dim); text-decoration: none; font-size: .88rem;
                   font-weight: 500; }
  .sidebar-link:hover { background: var(--neutral-bg); color: var(--text); }
  .sidebar-link.active { background: var(--accent-dim); color: var(--accent-hover);
                          font-weight: 600; }
  .sidebar-sub { display: block; padding: .3rem .6rem .3rem 1.3rem; color: var(--text-dim);
                  text-decoration: none; font-size: .8rem; }
  .sidebar-sub:hover { color: var(--accent-hover); }
  .sidebar-empty { color: var(--muted); font-size: .84rem; margin: 0 0 1rem; }
  .sidebar-add { display: block; margin-top: 1rem; padding-top: 1rem;
                 border-top: 1px solid var(--border); color: var(--accent);
                 text-decoration: none; font-size: .84rem; font-weight: 600; }
  .sidebar-add:hover { color: var(--accent-hover); }
  @media (max-width: 780px) {
    .sidebar { display: none; }
  }

  .topbar {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1rem 1.75rem; background: var(--surface); border-bottom: 1px solid var(--border);
    position: sticky; top: 0; z-index: 10; backdrop-filter: blur(6px);
  }
  .brand { display: flex; align-items: center; gap: .55rem; text-decoration: none;
           color: var(--text); }
  .brand-mark {
    display: inline-grid; place-items: center; width: 30px; height: 30px; border-radius: 7px;
    background: var(--accent); color: var(--accent-text); font-family: var(--font-mono);
    font-weight: 600; font-size: .75rem; letter-spacing: .02em;
  }
  .brand-name { font-family: var(--font-display); font-weight: 650; font-size: 1.2rem;
                font-style: italic; letter-spacing: -.01em; }
  .topbar nav { display: flex; gap: 1.6rem; align-items: center; }
  .topbar nav a { color: var(--text-dim); text-decoration: none; font-size: .88rem;
                  font-weight: 500; }
  .topbar nav a:hover { color: var(--text); }
  .nav-live { color: var(--success) !important; font-family: var(--font-mono); }

  h1 { font-family: var(--font-display); font-weight: 650; font-size: 2.1rem; margin: 0 0 .3rem;
       letter-spacing: -.015em; line-height: 1.15; }
  .page-header { display: flex; align-items: flex-end; justify-content: space-between;
                 gap: 1rem; margin-bottom: 1.75rem; flex-wrap: wrap; }
  .subtitle { color: var(--text-dim); margin: 0; font-size: .98rem; }
  .breadcrumb { font-family: var(--font-mono); font-size: .78rem; color: var(--muted);
                text-transform: uppercase; letter-spacing: .04em; }
  .breadcrumb a { color: var(--muted); text-decoration: none; }
  .breadcrumb a:hover { color: var(--accent); }

  /* The trail alone read as a location label, not a control -- every non-home
     page gets a real back button beside it. */
  .crumbs { display: flex; align-items: center; gap: .85rem; margin-bottom: 1.1rem;
            flex-wrap: wrap; }
  .btn-back { padding: .34rem .85rem; font-size: .82rem; flex: none; }

  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius-lg);
    padding: 1.4rem 1.6rem; box-shadow: var(--shadow); margin-bottom: 1.4rem;
  }
  .card h2 { font-family: var(--font-display); font-weight: 600; font-size: 1.2rem;
             margin: 0 0 1rem; }
  .card-actions { display: flex; gap: .6rem; flex-wrap: wrap; margin-top: 1.1rem; }

  .project-grid {
    display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 1rem;
  }
  .project-card {
    position: relative; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 1.3rem 1.4rem 1.3rem 1.6rem; text-decoration: none;
    color: var(--text); box-shadow: var(--shadow); transition: box-shadow .15s, transform .15s;
    overflow: hidden;
  }
  .project-card::before {
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px;
    background: var(--accent);
  }
  .project-card:hover { box-shadow: var(--shadow-lift); transform: translateY(-2px); }
  .project-card .name { font-family: var(--font-display); font-weight: 600; font-size: 1.15rem;
                         margin-bottom: .4rem; display: block; }
  .project-card .meta { color: var(--text-dim); font-family: var(--font-mono); font-size: .8rem; }
  .project-card .card-status { display: block; margin-top: .6rem; }
  .project-card .card-status .badge { font-size: .72rem; margin-right: .35rem; }

  .stat-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.75rem; }
  .stat {
    flex: 1 1 140px; background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius-lg); padding: 1.1rem 1.3rem; box-shadow: var(--shadow);
  }
  .stat .value { font-family: var(--font-display); font-size: 1.9rem; font-weight: 650;
                 line-height: 1.1; }
  .stat .label { color: var(--text-dim); font-size: .78rem; margin-top: .3rem;
                 text-transform: uppercase; letter-spacing: .04em; }

  table { border-collapse: collapse; width: 100%; }
  th { text-align: left; font-family: var(--font-mono); font-size: .74rem;
       text-transform: uppercase; letter-spacing: .05em; color: var(--text-dim);
       padding: .55rem .7rem; border-bottom: 1px solid var(--border); }
  td { padding: .7rem .7rem; border-bottom: 1px solid var(--border); font-size: .92rem; }
  td code { font-family: var(--font-mono); font-size: .85rem; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--neutral-bg); }
  .run-results { display: flex; gap: .4rem; flex-wrap: wrap; }
  .run-date { color: var(--text-dim); font-size: .82rem; font-family: var(--font-mono); }

  .case-meta { display: flex; align-items: center; gap: .6rem; flex-wrap: wrap;
               margin-bottom: .5rem; }
  .scoreboard { font-size: .88rem; color: var(--text-dim); margin: 0 0 .5rem; }
  .failure-list { margin: 0 0 .75rem; padding-left: 1.1rem; font-size: .86rem; }
  .failure-list li { margin-bottom: .3rem; }
  .failure-list code { font-family: var(--font-mono); font-size: .82rem; }

  .flow { display: flex; flex-wrap: wrap; align-items: center; margin-top: .5rem; }
  .flow-step { display: block; width: 150px; text-decoration: none; color: inherit; }
  .flow-step .thumb { border: 1px solid var(--border); border-radius: var(--radius);
                       overflow: hidden; background: var(--neutral-bg);
                       transition: border-color .15s; }
  .flow-step:hover .thumb { border-color: var(--accent); }
  .flow-step img { width: 100%; height: auto; display: block; cursor: zoom-in; }
  .flow-step .step-label { display: block; padding: .3rem .1rem 0; font-size: .72rem;
                            color: var(--text-dim); font-family: var(--font-mono);
                            text-align: center; }
  .flow-arrow { color: var(--border); font-size: 1.3rem; padding: 0 .25rem; flex-shrink: 0; }

  .lightbox { display: none; position: fixed; inset: 0; background: rgba(20,16,12,.87);
              z-index: 1000; align-items: center; justify-content: center; padding: 2.5rem; }
  .lightbox:target { display: flex; }
  .lightbox img { max-width: 94vw; max-height: 88vh; border-radius: var(--radius);
                   box-shadow: 0 20px 60px rgba(0,0,0,.5); display: block; }
  .lightbox .lightbox-caption { position: absolute; bottom: 1.6rem; left: 50%;
                                 transform: translateX(-50%); color: #fff;
                                 font-family: var(--font-mono); font-size: .8rem;
                                 background: rgba(0,0,0,.55); padding: .3rem .85rem;
                                 border-radius: 999px; }

  .flow-tree, .flow-tree ul { list-style: none; margin: 0; padding-left: 1.6rem;
                               position: relative; }
  .flow-tree { padding-left: 0; }
  .flow-tree li { position: relative; padding: .4rem 0 .4rem 1rem; }
  .flow-tree li::before { content: ''; position: absolute; left: 0; top: 0; bottom: 50%;
                           width: 1rem; border-left: 1px solid var(--border);
                           border-bottom: 1px solid var(--border); }
  .flow-tree li::after { content: ''; position: absolute; left: 0; top: 50%; bottom: 0;
                          border-left: 1px solid var(--border); }
  .flow-tree li:last-child::after { display: none; }
  .flow-tree > li::before, .flow-tree > li::after { display: none; }
  .tree-node { display: inline-flex; align-items: center; gap: .5rem; font-size: .88rem; }
  .tree-node .step-label { font-family: var(--font-mono); font-size: .82rem;
                            color: var(--text-dim); }
  .tree-leaf { font-weight: 600; }

  form { margin: 0; }
  .field { margin-bottom: 1.2rem; }
  .field label { display: block; font-size: .85rem; font-weight: 600; margin-bottom: .4rem; }
  .field .hint { display: block; color: var(--muted); font-size: .8rem; margin-top: .35rem; }
  input[type=text], input[type=password], input[type=url], input:not([type]) {
    width: 100%; padding: .6rem .75rem; border: 1px solid var(--border);
    border-radius: var(--radius); background: var(--bg); color: var(--text);
    font-size: .95rem; font-family: var(--font-body);
    transition: border-color .12s, box-shadow .12s;
  }
  input:focus { outline: none; border-color: var(--accent);
                box-shadow: 0 0 0 3px var(--accent-dim); }

  .btn {
    display: inline-flex; align-items: center; gap: .45rem; padding: .6rem 1.2rem;
    border-radius: var(--radius); border: 1px solid var(--border); background: var(--surface);
    color: var(--text); font-size: .9rem; font-weight: 600; cursor: pointer;
    text-decoration: none; line-height: 1; font-family: var(--font-body);
    transition: border-color .12s, transform .08s;
  }
  .btn:hover { border-color: var(--accent); }
  .btn:active { transform: scale(.97); }
  .btn-primary { background: var(--accent); color: var(--accent-text);
                 border-color: var(--accent); }
  .btn-primary:hover { background: var(--accent-hover); border-color: var(--accent-hover); }
  .btn-sm { padding: .38rem .75rem; font-size: .82rem; }

  .badge {
    display: inline-flex; align-items: center; gap: .3rem; padding: .2rem .65rem;
    border-radius: 999px; font-size: .74rem; font-weight: 600; font-family: var(--font-mono);
    text-transform: uppercase; letter-spacing: .03em;
  }
  .badge-pass { background: var(--success-bg); color: var(--success); }
  .badge-fail { background: var(--danger-bg); color: var(--danger); }
  .badge-blocked { background: var(--blocked-bg); color: var(--blocked); }
  .badge-inconclusive { background: var(--neutral-bg); color: var(--text-dim); }

  .empty-state {
    text-align: center; padding: 3.5rem 1.5rem; color: var(--text-dim);
    border: 1px dashed var(--border); border-radius: var(--radius-lg); background: var(--surface);
  }
  .empty-state .icon { font-size: 2.2rem; margin-bottom: .7rem; }
  .empty-state p { margin: .3rem 0 1.3rem; font-size: .98rem; }

  .live-shell { border: 1px solid var(--border); border-radius: var(--radius-lg);
                overflow: hidden; box-shadow: var(--shadow); }
  .live-shell iframe { width: 100%; height: 68vh; border: none; display: block; }
  .live-tip { background: var(--surface); border: 1px solid var(--border);
              border-radius: var(--radius-lg); padding: 1.1rem 1.3rem; margin-bottom: 1.4rem; }
  .live-tip code { font-family: var(--font-mono); background: var(--neutral-bg);
                    padding: .15rem .4rem; border-radius: 4px; font-size: .85rem; }
  .live-tip-muted { color: var(--text-dim); font-size: .9rem; }

  /* Destructive action: readable, never the loudest thing on the page. */
  .btn-danger { color: var(--danger); border-color: var(--danger); }
  .btn-danger:hover { background: var(--danger-bg); }
  .row-form { display: flex; gap: .5rem; align-items: center; }
  .row-form input { flex: 1 1 auto; min-width: 12rem; }

  /* Crawl pages (T-144). A screen graph is mostly tabular; the one place it
     is not is the tree, where indentation carries the discovery depth. */
  .meta { color: var(--text-dim); font-size: .85rem; }
  .data-table { width: 100%; border-collapse: collapse; font-size: .9rem; }
  .data-table th, .data-table td { text-align: left; padding: .45rem .6rem;
    border-bottom: 1px solid var(--border); vertical-align: top; }
  .data-table thead th { color: var(--text-dim); font-weight: 600;
    text-transform: uppercase; font-size: .72rem; letter-spacing: .06em; }
  .data-table tbody tr:last-child td { border-bottom: none; }
  .crawl-tree { list-style: none; margin: 0; padding: 0; }
  .crawl-node { display: flex; gap: .75rem; align-items: flex-start;
    padding: .6rem 0; border-bottom: 1px solid var(--border);
    margin-left: calc(var(--depth, 0) * 1.25rem); }
  .crawl-node:last-child { border-bottom: none; }
  .crawl-node .thumb { flex: 0 0 auto; }
  .crawl-node .thumb img { width: 7rem; border: 1px solid var(--border);
    border-radius: var(--radius); display: block; }
  .crawl-node-body { min-width: 0; overflow-wrap: anywhere; }
</style>
"""
