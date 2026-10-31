"""Self-contained dashboard; all external strings escaped and no remote assets."""

from __future__ import annotations

import html
import json
from pathlib import Path


def render_report(run_dir: Path, report: dict, alerts: list[dict]) -> None:
    def escape(value):
        return html.escape(str(value), quote=True)
    rows = []
    for name, value in report["test"].items():
        ap = value["average_precision"]
        rows.append(
            f"<tr><td>{escape(name)}</td><td>{ap:.3f}</td>"
            f"<td>{value['precision']:.3f}</td><td>{value['recall']:.3f}</td>"
            f"<td>{value['f1']:.3f}</td><td>{value['alerts']}</td></tr>"
            if ap is not None else f"<tr><td>{escape(name)}</td><td colspan='5'>No positive labels</td></tr>"
        )
    cards = []
    for alert in alerts:
        reasons = "".join(f"<li>{escape(reason)}</li>" for reason in alert["reasons"])
        cards.append(
            f"<article data-user='{escape(alert['user'])}'><h3>{escape(alert['user'])}</h3>"
            f"<p>{escape(alert['window_start'])} · score {alert['score']:.3f}</p>"
            f"<code>{escape(alert['alert_id'])}</code><ul>{reasons}</ul>"
            f"<p>ATT&amp;CK hypotheses: {escape(', '.join(alert['attack_hypotheses']) or 'unmapped')}</p>"
            "<p>Human review required. Validate context before escalation.</p></article>"
        )
    text = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'">
<title>AegisLake · Investigation desk</title>
<style>
:root{color-scheme:dark;font-family:system-ui,sans-serif;background:#0b1020;color:#e5e9f2}
body{max-width:1180px;margin:auto;padding:40px 24px}header{border-bottom:1px solid #33415c;padding-bottom:24px}
h1{font-size:46px;margin:8px 0}h2{margin-top:40px}p,li{line-height:1.6;color:#c0cce0}
.badge{color:#68e5c0;font-weight:600;letter-spacing:.15em}aside{padding:18px;border:1px solid #9a7633;
background:#332b1c;border-radius:12px;margin:24px 0}table{width:100%;border-collapse:collapse}
td,th{padding:15px;text-align:left;border-bottom:1px solid #33415c}th{color:#91a8cc}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:16px}
article{padding:20px;background:#131c30;border:1px solid #283750;border-radius:12px;overflow-wrap:anywhere}
code{font-size:12px;color:#68e5c0}input{padding:12px;background:#131c30;color:white;border:1px solid #5a749c;
border-radius:8px;width:min(360px,90%);margin:12px 0 20px}footer{margin-top:40px;color:#91a8cc}
</style></head><body><header><div class="badge">AEGISLAKE / IDENTITY ANALYTICS</div>
<h1>Evidence before escalation.</h1><p>Temporal model evaluation and a capacity-limited investigation queue.</p></header>"""
    text += f"<aside>{escape(report['data_notice'])} Scores are rankings, not calibrated probabilities.</aside>"
    text += f"<p>Validation-selected model: <strong>{escape(report['champion'])}</strong> · "
    text += f"daily capacity: {report['capacity']} user windows · run: {escape(report['run_id'])}</p>"
    text += "<h2>Held-out test results</h2><div style='overflow:auto'><table><thead><tr>"
    text += "<th>Model</th><th>AP</th><th>Precision</th><th>Recall</th><th>F1</th><th>Alerts</th>"
    text += "</tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    text += "<h2>Investigation queue</h2><label for='filter'>Filter by pseudonymous user</label><br>"
    text += "<input id='filter' placeholder='employee-0001'><div class='grid'>" + "".join(cards) + "</div>"
    # No raw event payloads or JSON inserted into JavaScript.
    text += """<script>
document.getElementById('filter').addEventListener('input', function(){
const q=this.value.toLowerCase();
document.querySelectorAll('article').forEach(el=>{el.hidden=!el.dataset.user.toLowerCase().includes(q)});
});
</script><footer>Offline report · 15-minute closed windows · UTC · human decisions stored by the review CLI</footer>
</body></html>"""
    (run_dir / "report.html").write_text(text, encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
