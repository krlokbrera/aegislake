"""Offline investigation dashboard and curated ATT&CK explorer."""

from __future__ import annotations

import html
import json
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import quote

from aegislake.attack import TACTIC_IDS, TACTICS, TECHNIQUES, describe_mapping, write_attack_exports
from aegislake.report_ui import SCRIPT, STYLE

MODEL_NAMES = {"rules": "Detection rules", "isolation_forest": "Isolation Forest",
               "hybrid": "Hybrid ensemble", "logistic_regression": "Logistic regression"}


def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def pct(value: float | None) -> str:
    return "Unavailable" if value is None else f"{value:.1%}"


def metric(label: str, value: object, note: str, accent: str = "") -> str:
    return (f'<div class="metric {accent}"><span>{esc(label)}</span><strong>{esc(value)}</strong>'
            f'<small>{esc(note)}</small></div>')


def shell(report: dict, page: str, title: str, body: str, *, extra_style: str = "",
          extra_script: str = "", allow_api: bool = False) -> str:
    nav = "".join(
        f'<a href="{href}" {"aria-current=page" if page == key else ""}>'
        f'<span class="nav-icon" aria-hidden="true">{icon}</span>{label}</a>'
        for key, href, icon, label in (("overview", "report.html", "◫", "Overview"),
                                      ("dashboards", "dashboard.html", "▥", "Dashboards"),
                                      ("mitre", "mitre.html", "⌘", "MITRE ATT&CK"))
    )
    mode = "Synthetic demo" if report.get("config", {}).get("synthetic") else "Offline evaluation"
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; {'connect-src &#39;self&#39;;' if allow_api else ''} base-uri 'none'; form-action 'none'">
<title>AegisLake · {esc(title)}</title><style>{STYLE}{extra_style}</style></head>
<body><a class="skip" href="#main">Skip to content</a><aside class="sidebar">
<a class="brand" href="report.html"><span class="brandmark" aria-hidden="true">A</span>AegisLake<span class="brand-dot">.</span></a>
<div class="nav-label">INVESTIGATION WORKSPACE</div><nav aria-label="Main navigation">{nav}</nav>
<div class="side-foot"><span class="status-dot"></span> Offline &amp; self-contained<br><small>Identity analytics / human review</small></div>
</aside><div class="workspace"><header class="topbar"><span>Workspace <span class="slash">/</span> {esc(title)}</span>
<span class="pill"><span class="status-dot"></span>{mode}</span></header>
<main id="main">{body}<footer><span>AegisLake / Evidence before escalation.</span>
<span>Closed 15-minute windows · UTC · <code>{esc(report['run_id'])}</code></span></footer></main></div>
<script>{SCRIPT}{extra_script}</script></body></html>'''


def daily_chart(report: dict, alerts: list[dict]) -> str:
    counts = Counter(str(alert["window_start"])[:10] for alert in alerts)
    bounds = report.get("split_boundaries", {})
    first = bounds.get("test_first_window", "")[:10]
    last = bounds.get("test_last_window_end", "")[:10]
    if first and last:
        start, end = date.fromisoformat(first), date.fromisoformat(last)
        dates = [(start + timedelta(days=i)).isoformat() for i in range((end - start).days + 1)]
    else:
        dates = sorted(counts)
    if not dates:
        return '<div class="chart-empty">No queued alerts in this run.</div>'
    maximum = max(int(report["capacity"]), max(counts.values(), default=0), 1)
    slot = 574 / len(dates)
    bars = []
    for i, stamp in enumerate(dates):
        count = counts[stamp]
        height = count / maximum * 106
        x = 43 + i * slot + slot * .2
        bars.append(f'<rect x="{x:.2f}" y="{156-height:.2f}" width="{slot*.6:.2f}" '
                    f'height="{height:.2f}" rx="4" fill="url(#bars)"><title>{stamp}: {count} alerts</title></rect>')
        if len(dates) <= 12 or i % max(1, len(dates) // 6) == 0:
            bars.append(f'<text x="{x+slot*.3:.2f}" y="184" text-anchor="middle">{stamp[5:]}</text>')
    limit_y = 156 - int(report["capacity"]) / maximum * 106
    return ('<svg class="daily-chart" viewBox="0 0 640 200" role="img" aria-labelledby="daily-title daily-desc">'
            '<title id="daily-title">Daily investigation queue</title>'
            '<desc id="daily-desc">Queued alert windows per UTC day. Dashed line: daily review cap.</desc>'
            '<defs><linearGradient id="bars" x2="0" y2="1"><stop stop-color="#c5fa66"/>'
            '<stop offset="1" stop-color="#6d9e30"/></linearGradient></defs>'
            '<path d="M43 50H617M43 103H617M43 156H617" stroke="#293344"/>'
            f'<text x="12" y="55">{maximum}</text><text x="20" y="160">0</text>'
            f'<path d="M43 {limit_y:.2f}H617" stroke="#b7c5db" stroke-dasharray="4 5"/>'
            + "".join(bars) + '</svg>')


def alert_rows(alerts: list[dict]) -> str:
    rows = []
    for alert in alerts:
        techniques = sorted(set(alert["attack_hypotheses"]))
        tags = "".join(f'<a class="tag" href="mitre.html#{quote(technique, safe="")}">{esc(technique)}</a>'
                       if technique in TECHNIQUES else f'<span class="tag">{esc(technique)}</span>'
                       for technique in techniques) or '<span class="muted">Unmapped</span>'
        candidate_tactics = {item["tactic_id"]: item["tactic_name"]
                             for technique in describe_mapping(techniques)["techniques"]
                             for item in technique["candidate_tactics"]}
        tactic_tags = " ".join(f'<span class="tag">{esc(key)} / {esc(name)}</span>'
                               for key, name in sorted(candidate_tactics.items()))
        reasons = "".join(f'<li>{esc(reason)}</li>' for reason in alert["reasons"])
        steps = "".join(f'<li>{esc(step)}</li>' for step in alert.get("next_steps", []))
        score, stamp = float(alert["score"]), str(alert["window_start"])
        rows.append(f'''<article class="alert-row" data-alert data-user="{esc(alert['user'])}"
data-alert-id="{esc(alert['alert_id'])}" data-techniques="{esc(' '.join(techniques))}"
data-score="{score:.12f}" data-time="{esc(stamp)}">
<details><summary><span class="identity"><span class="avatar" aria-hidden="true">ID</span>
<span><strong>{esc(alert['user'])}</strong><small>{esc(stamp[:10])} / {esc(stamp[11:16])} UTC</small></span></span>
<span class="score"><span class="score-track"><span style="width:{min(1, max(0, score))*100:.2f}%"></span></span>
<b>{score:.3f}</b></span><span class="review-state">Needs review</span><span class="open-label">Inspect ↗</span></summary>
<div class="evidence"><div><span class="eyebrow">OBSERVED SIGNALS</span><ul>{reasons}</ul></div>
<div><span class="eyebrow">ANALYST NEXT STEPS</span><ul>{steps}</ul>
<p>Validate context before escalation. Ranking scores are not probabilities.</p></div>
<p class="evidence-id">Candidate tactics: {tactic_tags or "Unmapped"}</p>
<p class="evidence-id">Alert <code>{esc(alert['alert_id'])}</code></p></div></details>
<div class="alert-tags">{tags}</div></article>''')
    return "".join(rows)


def overview(report: dict, alerts: list[dict]) -> str:
    if report["champion"] not in report["test"]:
        return ('<div class="page-heading"><div><div class="eyebrow">OFFLINE EVALUATION</div>'
                '<h1>Incomplete evaluation.</h1></div></div><div class="notice"><p>'
                'Selected-model metrics are unavailable. No performance claims can be made.</p></div>'
                f'<p>Selected model: {esc(report["champion"])}</p><p>{esc(report["data_notice"])}</p>'
                '<section class="panel"><h2>Available alert evidence</h2>' + alert_rows(alerts) + '</section>')
    result = report["test"][report["champion"]]
    quality = report["quality"]
    model = MODEL_NAMES.get(report["champion"], report["champion"])
    cards = (metric("Queued alert windows", f"{len(alerts):,}", f"Review cap · {report['capacity']} / day", "accent")
             + metric("Identities to review", len({a["user"] for a in alerts}), "Distinct identities in the queue")
             + metric("Test precision", pct(result["precision"]), "Measured against held-out labels")
             + metric("Test recall", pct(result["recall"]), "Measured after the daily cap"))
    models, table = [], []
    for name, value in report["test"].items():
        ap, label = value["average_precision"], MODEL_NAMES.get(name, name)
        badge = '<span class="tiny">SELECTED</span>' if name == report["champion"] else ""
        models.append(f'<div class="model-line"><div><span>{esc(label)} {badge}</span>'
                      f'<b>{"N/A" if ap is None else f"{ap:.3f}"}</b></div>'
                      f'<div class="track"><span style="width:{0 if ap is None else ap*100:.2f}%"></span></div></div>')
        table.append(f'<tr><th scope="row">{esc(label)}</th><td>{"N/A" if ap is None else f"{ap:.3f}"}</td>'
                     f'<td>{pct(value["precision"])}</td><td>{pct(value["recall"])}</td>'
                     f'<td>{value["f1"]:.3f}</td><td>{value["alerts"]}</td></tr>')
    confusion = result["confusion_matrix"]
    precision, circumference = result["precision"] or 0, 2 * 3.14159265 * 54
    donut = (f'<svg viewBox="0 0 150 150" role="img" aria-label="Queued windows: '
             f'{confusion["tp"]} true positives, {confusion["fp"]} false positives against test labels">'
             '<circle cx="75" cy="75" r="54" fill="none" stroke="#f6b66b" stroke-width="12"/>'
             f'<circle cx="75" cy="75" r="54" fill="none" stroke="#b8ef65" stroke-width="12" '
             f'stroke-dasharray="{precision*circumference:.2f} {circumference:.2f}" transform="rotate(-90 75 75)"/>'
             f'<text class="donut-number" x="75" y="74" text-anchor="middle">{len(alerts)}</text>'
             '<text x="75" y="94" text-anchor="middle">queued windows</text></svg>')
    if not alerts:
        donut = '<div class="chart-empty">No queued windows to evaluate.</div>'
    options = "".join(f'<option value="{tech}">{tech} · {data["name"]}</option>' for tech, data in TECHNIQUES.items())
    return f'''<div class="page-heading"><div><div class="eyebrow">IDENTITY THREAT ANALYTICS</div>
<h1>See the signal.<br><span>Investigate with context.</span></h1>
<p>Your evidence desk for identity activity, model evaluation and analyst review.</p></div>
<a class="button primary" href="mitre.html">Explore ATT&amp;CK <span aria-hidden="true">↗</span></a></div>
<div class="notice"><span class="notice-icon" aria-hidden="true">i</span><p>{esc(report['data_notice'])}
<span>Offline snapshot. No live monitoring or automatic response.</span></p></div>
<section class="metrics" aria-label="Run metrics">{cards}</section>
<div class="charts"><section class="panel"><div class="section-heading"><div><span class="eyebrow">REVIEW WORKLOAD</span>
<h2>Daily investigation queue</h2></div><span class="legend"><i></i> Alert windows <span>─ ─ Daily cap</span></span></div>
{daily_chart(report, alerts)}<div class="panel-foot"><span>UTC dates / held-out test period</span>
<strong>{report['capacity']} windows per day</strong></div></section>
<section class="panel model-panel"><span class="eyebrow">MODEL BENCHMARK</span><h2>Ranking performance</h2>
<p class="muted compact">Average precision · held-out test</p>{''.join(models)}
<p class="muted compact">Selection used validation F1 under the daily review cap.</p></section></div>
<div class="insights"><section class="panel outcomes"><div><span class="eyebrow">LABEL-BASED EVALUATION</span>
<h2>Inside the review queue</h2><p class="muted compact">{esc(model)} / held-out labels</p>
<div class="outcome-key"><span><i class="good"></i> {confusion['tp']} true positives</span>
<span><i class="warm"></i> {confusion['fp']} false positives</span></div></div><div class="donut">{donut}</div></section>
<section class="panel data-health"><span class="eyebrow">DATA QUALITY</span><h2>A traceable data foundation</h2>
<div class="quality-grid"><div><strong>{quality['accepted']:,}</strong><small>accepted events</small></div>
<div><strong>{quality['duplicates']}</strong><small>duplicate lines</small></div>
<div><strong>{quality['rejected']}</strong><small>quarantined lines</small></div></div>
<p class="muted compact">{quality['input_lines']:,} input lines reconciled across accepted, duplicate and rejected records.</p></section></div>
<section id="queue" class="panel queue-panel"><div class="section-heading"><div><span class="eyebrow">HUMAN-LED INVESTIGATION</span>
<h2>Investigation queue <span class="count-badge">{len(alerts)}</span></h2></div><a class="text-link" href="mitre.html">View technique map ↗</a></div>
<div class="filters"><label class="search-field"><span>Search identity or alert ID</span>
<input id="filter" type="search" placeholder="Search identity or alert ID…" autocomplete="off"></label>
<label><span>Technique</span><select id="technique"><option value="">All techniques</option>{options}
<option value="unmapped">Unmapped</option></select></label>
<label><span>Sort by</span><select id="sort"><option value="score">Highest score</option><option value="time">Most recent</option></select></label>
<button id="reset" class="button quiet" type="button">Reset</button></div>
<div class="queue-head" aria-hidden="true"><span>Identity / window</span><span>Ranking score</span><span>Review state</span><span>Evidence</span></div>
<div id="alert-list">{alert_rows(alerts)}</div><p id="empty" class="empty" hidden>No alerts match these filters. Try another identity or technique.</p>
<div class="pagination"><span id="queue-status" role="status" aria-live="polite"></span><div>
<button id="previous" class="button quiet" type="button">Previous</button><button id="next" class="button quiet" type="button">Next</button></div></div></section>
<details class="panel benchmark"><summary>Explore all benchmark metrics <span aria-hidden="true">＋</span></summary>
<div class="table-scroll"><table><thead><tr><th scope="col">Model</th><th scope="col">AP</th><th scope="col">Precision</th>
<th scope="col">Recall</th><th scope="col">F1</th><th scope="col">Alert windows</th></tr></thead><tbody>{''.join(table)}</tbody></table></div>
<p class="muted">Scores rank windows; they are not calibrated probabilities. Test labels support these metrics, not confirmation of an operational incident.</p></details>'''


def mitre(report: dict, alerts: list[dict]) -> str:
    counts = Counter(technique for alert in alerts for technique in set(alert["attack_hypotheses"]))
    mapped = sum(bool(set(alert["attack_hypotheses"]) & TECHNIQUES.keys()) for alert in alerts)
    cards = (metric("Mapped alert windows", mapped, "At least one supported technique", "accent")
             + metric("Observed techniques", sum(counts[key] > 0 for key in TECHNIQUES), "Of 2 hypotheses implemented")
             + metric("Without a supported mapping", len(alerts) - mapped, "Still available for human review")
             + metric("Curated tactical columns", len(TACTICS), "A focused identity view, not the full matrix"))
    columns, detail = [], []
    for tactic in TACTICS:
        cells = "".join(f'<button class="tech-cell" data-technique="{tech}" aria-pressed="false" type="button">'
                        f'<code>{tech}</code><strong>{data["name"]}</strong>'
                        f'<span>{counts[tech]} alert windows <b aria-hidden="true">↗</b></span></button>'
                        for tech, data in TECHNIQUES.items() if tactic in data["tactics"])
        columns.append(f'<div class="tactic"><h3><span class="muted">{TACTIC_IDS[tactic]}</span><br>{tactic}</h3>{cells}</div>')
    for tech, data in TECHNIQUES.items():
        detail.append(f'''<section class="tech-detail" id="{tech}" data-detail="{tech}">
<div class="tech-title"><div><span class="eyebrow">TECHNIQUE HYPOTHESIS / {tech}</span><h2>{data['name']}</h2></div>
<span class="big-count">{counts[tech]}<small>alert windows</small></span></div>
<p class="tech-description">{data['description']}</p><div class="evidence-block"><span class="eyebrow">WHAT TRIGGERS THE MAPPING</span><p>{data['signal']}</p></div>
<div class="evidence-block muted-block"><span class="eyebrow">WHAT TO VALIDATE</span><p>{data['caveat']}</p></div>
<p class="muted">Required canonical fields: <code>{esc(", ".join(data["required_fields"]))}</code>.</p>
<p class="muted">Associated tactics: {', '.join(data['tactics'])}. Tactical membership does not establish that any of these objectives occurred.</p>
<div class="detail-actions"><a class="button primary" href="report.html?technique={tech}#queue">Investigate matching alerts ↗</a>
<a class="text-link" href="{data['url']}" target="_blank" rel="noopener noreferrer">Official MITRE reference ↗</a></div></section>''')
    return f'''<div class="page-heading"><div><div class="eyebrow">MITRE ATT&amp;CK / IDENTITY LENS</div>
<h1>Map the signal.<br><span>Understand the technique.</span></h1><p>Connect investigation hypotheses to the evidence behind each alert.</p></div>
<a class="button quiet" href="report.html#queue">Back to investigation ↗</a></div>
<div class="notice"><span class="notice-icon" aria-hidden="true">i</span><p>Hypotheses, not confirmed attacks.
<span>This curated view shows two implemented mappings. It does not measure ATT&amp;CK detection coverage.</span></p></div>
<section class="metrics" aria-label="ATT&CK mapping metrics">{cards}</section>
<section class="panel"><div class="section-heading"><div><span class="eyebrow">EXPLORE BY TACTIC</span><h2>Identity technique map</h2></div>
<span class="pill">Select a technique</span></div><div class="matrix-scroll" role="region" aria-label="Curated ATT&CK tactical map" tabindex="0">
<div class="matrix">{''.join(columns)}</div></div>
<p class="muted compact">A technique can belong to several tactics. Repeated cells share the same alert count; counts overlap and must not be added.</p></section>
<section class="panel dettect-panel"><div class="section-heading"><div><span class="eyebrow">SOC / SIEM INTEROPERABILITY</span>
<h2>DeTT&amp;CT assessment handoff</h2></div><span class="pill">Operational assessment pending</span></div>
<p class="compact muted">Export candidate techniques, tactic IDs and required authentication fields for your detection inventory.
The YAML starts with no deployed detection (-1) and no registered visibility (0); these are conservative draft placeholders, not a production assessment.</p>
<div class="detail-actions"><a class="button primary" href="dettect-techniques.yaml" download>Download DeTT&amp;CT YAML</a>
<a class="button quiet" href="attack-mapping.json" download>Download alert mappings</a>
<a class="text-link" href="https://github.com/rabobank-cdc/DeTTECT" target="_blank" rel="noopener noreferrer">DeTT&amp;CT framework</a></div></section>
<div class="tech-layout"><div class="panel technique-details">{''.join(detail)}</div>
<aside class="panel reading-guide"><span class="eyebrow">INVESTIGATION GUIDE</span><h2>From mapping to evidence</h2>
<ol><li><strong>Read the signal</strong><p>Review the exact rule behind the hypothesis.</p></li>
<li><strong>Check the context</strong><p>Compare approved changes, identity activity and endpoint telemetry.</p></li>
<li><strong>Make a human decision</strong><p>Open matching alerts, inspect evidence and record the review using the CLI.</p></li></ol>
<div class="reference-note">Metadata checked against official MITRE pages on 31 October 2026.
The source pages may change; this offline snapshot does not update automatically.</div></aside></div>'''


def render_report(run_dir: Path, report: dict, alerts: list[dict], *, kind: str = "evaluation") -> None:
    from aegislake.dashboard import write_dashboard

    write_attack_exports(run_dir, report, alerts)
    (run_dir / "report.html").write_text(shell(report, "overview", "Threat overview", overview(report, alerts)),
                                         encoding="utf-8")
    (run_dir / "mitre.html").write_text(shell(report, "mitre", "MITRE ATT&CK", mitre(report, alerts)),
                                        encoding="utf-8")
    (run_dir / "report.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    write_dashboard(run_dir, report, alerts, kind=kind)
