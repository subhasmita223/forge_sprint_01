#!/usr/bin/env python3
"""
run.py — headless runner for the SEO Command Center (also the grader's entry point).

Runs the full pipeline on a Screaming Frog export with no Claude Code:
  load -> detect -> (starter recommendations) -> write report.json + report.html

Usage:
  python run.py sample-export/
  python run.py sample-export/ --no-dashboard

The model-driven fixes (title rewriting, redirect map) are left as a Sprint TODO; the
starter writes empty fix blocks so the contract stays valid.
"""
from __future__ import annotations
import argparse, os, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "mcp"))
sys.path.insert(0, HERE)
import server  # the MCP server module exposes every tool as a function


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("export_dir")
    ap.add_argument("--no-dashboard", action="store_true")
    args = ap.parse_args()

    if not args.no_dashboard:
        server.start_dashboard()
        print(f"[seo] dashboard: http://localhost:{server.PORT}", flush=True)
        time.sleep(1)

    t0 = time.time()
    server.seo_load(args.export_dir)
    res = server.seo_detect()

    # starter recommendations from the detected issues (the skill writes richer ones)
    issues = sorted(server.RUN["issues"], key=lambda x: {"High":0,"Medium":1,"Low":2}.get(x["severity"],3))
    recs = []
    for i in issues[:5]:
        recs.append(f"Fix the {i['count']} {i['severity']}-severity '{i['type']}' issue(s) first.")
    if not recs:
        recs.append("No issues detected on this crawl.")
    server.seo_recommend(recs)

    # champion-tier fixes: model-driven title/meta rewrites + a redirect map.
    # build_fixes never raises and never hangs — it falls back to deterministic
    # output if the local model (Ollama/qwen) is unavailable, so the run stays safe.
    from seo import fixer
    fx = fixer.build_fixes(server.RUN["rows"], server.RUN["issues"])
    server.seo_set_fixes(fx["titles"], fx["redirect_map"])
    server.RUN["model_calls"] = fx["model_calls"]
    server.RUN["duration_sec"] = round(time.time() - t0, 1)
    server.seo_report()
    server.seo_export()

    s = server.RUN["summary"]
    print("\n=== SEO AUDIT RESULT ===")
    print(f"Site         : {server.RUN['site']}  ({server.RUN['urls']} URLs)")
    print(f"Total issues : {s['total_issues']}  (High {s['by_severity'].get('High',0)} / "
          f"Medium {s['by_severity'].get('Medium',0)} / Low {s['by_severity'].get('Low',0)})")
    print("Wrote outputs/report.json and outputs/report.html")

    # Keep the dashboard server alive so the populated results stay viewable;
    # otherwise the daemon HTTP thread dies when this script exits. Hold the
    # process open until the user interrupts (Ctrl+C).
    if not args.no_dashboard:
        print(f"\n[seo] dashboard live at http://localhost:{server.PORT}  (Ctrl+C to stop)", flush=True)
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n[seo] dashboard stopped.", flush=True)


if __name__ == "__main__":
    main()
