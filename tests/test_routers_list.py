"""Golden ordered legacy route tuples captured from foundation base 167f7576 (TF3)."""

from autotester.ui.app import app

LEGACY_ROUTES = (
    ("GET", "/projects/{slug}/cases/new",
     "autotester.ui.routes_cases.new_case_form"),
    ("POST", "/projects/{slug}/cases",
     "autotester.ui.routes_cases.create_case"),
    ("GET", "/projects/{slug}/cases",
     "autotester.ui.routes_cases.cases_list"),
    ("POST", "/projects/{slug}/cases/{case_id}/rename",
     "autotester.ui.routes_cases.rename_case"),
    ("POST", "/projects/{slug}/cases/{case_id}/delete",
     "autotester.ui.routes_cases.delete_case"),
    ("GET", "/projects/{slug}/edit",
     "autotester.ui.routes_project_edit.edit_project_form"),
    ("POST", "/projects/{slug}/edit",
     "autotester.ui.routes_project_edit.edit_project_submit"),
    ("POST", "/projects/{slug}/secrets",
     "autotester.ui.routes_project_edit.declare_secret"),
    ("POST", "/projects/{slug}/secrets/{key}/delete",
     "autotester.ui.routes_project_edit.undeclare_secret"),
    ("POST", "/projects/{slug}/run",
     "autotester.ui.routes_runs.trigger_run"),
    ("GET", "/projects/{slug}/runs/{run_id}",
     "autotester.ui.routes_report.run_view"),
    ("GET", "/projects/{slug}/report",
     "autotester.ui.routes_report.report"),
    ("GET", "/projects/{slug}/report.xlsx",
     "autotester.ui.routes_report.download_report_excel"),
    ("GET", "/projects/{slug}/report.html",
     "autotester.ui.routes_report.download_report_html"),
    ("GET", "/projects/{slug}/runs/{run_id}/videos/{video_path:path}",
     "autotester.ui.routes_video.serve_run_video"),
    ("GET", "/projects/{slug}/flow-diagram",
     "autotester.ui.routes_flow_diagram.flow_diagram"),
    ("GET", "/projects/{slug}/crawls",
     "autotester.ui.routes_crawls.crawls"),
    ("GET", "/projects/{slug}/crawls/{crawl_id}",
     "autotester.ui.routes_crawls.crawl_page"),
    ("GET", "/projects/{slug}/crawls/{crawl_id}/report.xlsx",
     "autotester.ui.routes_crawls.download_crawl_excel"),
    ("POST", "/projects/{slug}/explore",
     "autotester.ui.routes_crawls.start_crawl"),
    ("POST", "/projects/{slug}/crawls/{crawl_id}/merge",
     "autotester.ui.routes_crawls.merge_crawl"),
    ("POST", "/projects/{slug}/login-case",
     "autotester.ui.routes_crawl_login.declare_login_case"),
    ("POST", "/projects/{slug}/env/url",
     "autotester.ui.routes_credentials.env_url_submit"),
    ("POST", "/projects/{slug}/env/add",
     "autotester.ui.routes_credentials.env_add_credential"),
    ("GET", "/projects/{slug}/env",
     "autotester.ui.routes_credentials.env_editor_view"),
    ("POST", "/projects/{slug}/env",
     "autotester.ui.routes_credentials.env_editor_submit"),
    ("POST", "/projects/{slug}/crawl-approval",
     "autotester.ui.routes_crawl_approval.crawl_approval_submit"),
    ("GET", "/settings/providers",
     "autotester.ui.routes_settings.provider_settings_view"),
    ("POST", "/settings/providers",
     "autotester.ui.routes_settings.provider_settings_submit"),
    ("GET", "/projects/{slug}/flowspec",
     "autotester.ui.routes_learn.flowspec_page"),
    ("POST", "/projects/{slug}/flowspec/approve",
     "autotester.ui.routes_learn.approve_flowspec"),
    ("POST", "/projects/{slug}/flowspec/request-edit",
     "autotester.ui.routes_learn.request_edit_flowspec"),
    ("POST", "/projects/{slug}/cases/generate",
     "autotester.ui.routes_learn.generate_cases"),
    ("GET", "/projects/{slug}/requests",
     "autotester.ui.routes_learn.requests_page"),
    ("GET", "/projects/{slug}/sources",
     "autotester.ui.routes_sources.sources_page"),
    ("POST", "/projects/{slug}/sources",
     "autotester.ui.routes_sources.add_source"),
    ("POST", "/projects/{slug}/sources/upload",
     "autotester.ui.routes_sources.upload_source"),
    ("POST", "/projects/{slug}/sources/{source_id}/analyze",
     "autotester.ui.routes_sources.analyze_source"),
    ("GET", "/projects/{slug}/product-map",
     "autotester.ui.routes_product_map.product_map_page"),
    ("GET", "/projects/{slug}/frames/{source_id}/{name:path}",
     "autotester.ui.routes_product_map.learned_frame"),
    ("GET", "/projects/{slug}/issues",
     "autotester.ui.routes_issues.issues_page"),
    ("GET", "/projects/{slug}/issues.xlsx",
     "autotester.ui.routes_issues.download_issues"),
    ("GET", "/projects/{slug}/issues/{issue_id}/pin",
     "autotester.ui.routes_issues.pin_issue_form"),
    ("POST", "/projects/{slug}/issues/{issue_id}/pin",
     "autotester.ui.routes_issues.pin_issue"),
    ("GET", "/live",
     "autotester.ui.routes_live.live_view"),
    ("GET", "/healthz",
     "autotester.ui.routes_live.healthz"),
    ("GET", "/projects/{slug}/catalog",
     "autotester.ui.routes_catalog.catalog_page"),
)


def _route_snapshot(routes):
    output = []
    for route in routes:
        inner = getattr(route, "original_router", None)
        if inner is not None:
            output.extend(_route_snapshot(inner.routes))
        elif hasattr(route, "endpoint"):
            endpoint = route.endpoint
            name = endpoint.__module__ + "." + endpoint.__qualname__
            if name in {row[2] for row in LEGACY_ROUTES}:
                output.extend((method, route.path, name) for method in sorted(route.methods))
    return output


def test_existing_route_tuples_preserve_methods_templates_endpoint_and_order() -> None:
    assert tuple(_route_snapshot(app.routes)) == LEGACY_ROUTES
