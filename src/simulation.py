"""
Queuing System Simulation — M/M/c Model
=========================================
Author  : Almas Shahriar
Degree  : B.Sc. Industrial & Production Engineering, BUET ('26)
GitHub  : github.com/almasshahriar

Simulates a multi-server queuing system (M/M/c) for a hospital outpatient
department using discrete-event simulation + analytical M/M/c formulas.

Outputs:
  - Console summary
  - output/dashboard.html  (interactive dashboard)
  - data/simulation_log.csv

Usage:
    python src/simulation.py
"""

import math, random, json, csv, os
from datetime import datetime
from collections import defaultdict

random.seed(42)

# ── PATHS ──
BASE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT = os.path.join(BASE, "output", "dashboard.html")
LOG    = os.path.join(BASE, "data", "simulation_log.csv")
os.makedirs(os.path.join(BASE, "output"), exist_ok=True)
os.makedirs(os.path.join(BASE, "data"), exist_ok=True)

# ══════════════════════════════════════════════
# SCENARIO DEFINITIONS
# ══════════════════════════════════════════════
SCENARIOS = [
    {"name": "Morning Rush",   "lambda": 12, "mu": 5,  "c": 3, "label": "High demand, 3 servers"},
    {"name": "Afternoon Calm", "lambda": 6,  "mu": 5,  "c": 2, "label": "Moderate demand, 2 servers"},
    {"name": "Evening Surge",  "lambda": 10, "mu": 5,  "c": 2, "label": "High demand, 2 servers (understaffed)"},
    {"name": "Night Shift",    "lambda": 3,  "mu": 5,  "c": 1, "label": "Low demand, 1 server"},
    {"name": "Emergency Peak", "lambda": 18, "mu": 5,  "c": 4, "label": "Peak load, 4 servers"},
    {"name": "Optimal Config", "lambda": 12, "mu": 5,  "c": 4, "label": "High demand, 4 servers (optimized)"},
]

SIM_DURATION = 480   # minutes (8-hour shift)
HOURS        = [f"{7+i}:00" for i in range(9)]  # 7AM–3PM labels

# ══════════════════════════════════════════════
# M/M/c ANALYTICAL FORMULAS
# ══════════════════════════════════════════════
def erlang_c(lam, mu, c):
    """P0 and Erlang C formula for M/M/c queue."""
    rho = lam / (c * mu)
    if rho >= 1:
        return None, None, None  # unstable

    a = lam / mu  # offered load
    # P0
    sum_terms = sum((a**n) / math.factorial(n) for n in range(c))
    last_term = (a**c) / (math.factorial(c) * (1 - rho))
    p0 = 1.0 / (sum_terms + last_term)

    # Erlang C (prob of waiting)
    C = ((a**c) / (math.factorial(c) * (1 - rho))) * p0

    Lq  = C * rho / (1 - rho)          # avg queue length
    Wq  = Lq / lam                     # avg wait time (min)
    W   = Wq + 1/mu                    # avg system time
    L   = lam * W                      # avg in system
    util = rho                         # server utilization

    return {
        "rho":       round(rho, 4),
        "p0":        round(p0, 4),
        "C_erlang":  round(C, 4),
        "Lq":        round(Lq, 3),
        "Wq":        round(Wq * 60, 2),   # seconds→ keep as minutes*60
        "Wq_min":    round(Wq, 3),
        "W_min":     round(W, 3),
        "L":         round(L, 3),
        "util_pct":  round(util * 100, 1),
    }, p0, C

# ══════════════════════════════════════════════
# DISCRETE-EVENT SIMULATION (M/M/c)
# ══════════════════════════════════════════════
def simulate(lam, mu, c, duration=SIM_DURATION):
    """
    Event-driven simulation.
    Returns per-patient records + hourly snapshots.
    """
    # State
    servers_free = c
    queue        = []
    clock        = 0.0
    events       = []   # (time, type)  type: 'arrival' | 'departure'
    patients     = []
    hourly       = defaultdict(lambda: {"arrivals":0,"departures":0,"wait_sum":0,"queue_sum":0,"n":0})

    # Schedule first arrival
    next_arr = random.expovariate(lam / 60)  # lam per hour → per minute
    events.append((next_arr, "arrival", None))

    pid = 0
    active = {}   # server_id → (pid, finish_time)

    while clock < duration:
        if not events:
            break
        events.sort(key=lambda x: x[0])
        ev = events.pop(0)
        clock, etype = ev[0], ev[1]
        if clock > duration:
            break

        hour_bucket = min(int(clock // 60), 8)

        if etype == "arrival":
            pid += 1
            arr_time = clock
            hourly[hour_bucket]["arrivals"] += 1

            if servers_free > 0:
                servers_free -= 1
                svc = random.expovariate(mu / 60)
                finish = clock + svc
                patients.append({
                    "pid": pid, "arrival": round(arr_time,2),
                    "service_start": round(clock,2),
                    "wait": 0.0,
                    "service_time": round(svc,2),
                    "finish": round(finish,2),
                    "sojourn": round(svc,2),
                })
                events.append((finish, "departure", pid))
            else:
                queue.append((pid, arr_time))

            hourly[hour_bucket]["queue_sum"] += len(queue)
            hourly[hour_bucket]["n"] += 1

            # Schedule next arrival
            next_arr = clock + random.expovariate(lam / 60)
            if next_arr < duration + 30:
                events.append((next_arr, "arrival", None))

        elif etype == "departure":
            hourly[hour_bucket]["departures"] += 1
            if queue:
                next_pid, arr_time = queue.pop(0)
                wait = clock - arr_time
                svc = random.expovariate(mu / 60)
                finish = clock + svc
                hourly[hour_bucket]["wait_sum"] += wait
                patients.append({
                    "pid": next_pid, "arrival": round(arr_time,2),
                    "service_start": round(clock,2),
                    "wait": round(wait,2),
                    "service_time": round(svc,2),
                    "finish": round(finish,2),
                    "sojourn": round(wait+svc,2),
                })
                events.append((finish, "departure", next_pid))
            else:
                servers_free += 1

    # Aggregate
    n = len(patients)
    if n == 0:
        return {}, []

    avg_wait    = sum(p["wait"] for p in patients) / n
    avg_sojourn = sum(p["sojourn"] for p in patients) / n
    avg_svc     = sum(p["service_time"] for p in patients) / n
    pct_waited  = sum(1 for p in patients if p["wait"] > 0) / n * 100
    max_wait    = max(p["wait"] for p in patients)

    hourly_out = []
    for h in range(9):
        b = hourly[h]
        hourly_out.append({
            "hour":       HOURS[h] if h < len(HOURS) else f"{7+h}:00",
            "arrivals":   b["arrivals"],
            "departures": b["departures"],
            "avg_queue":  round(b["queue_sum"] / b["n"],2) if b["n"] > 0 else 0,
            "avg_wait":   round(b["wait_sum"] / b["arrivals"],2) if b["arrivals"] > 0 else 0,
        })

    return {
        "n_patients":   n,
        "avg_wait_min": round(avg_wait, 2),
        "avg_sojourn":  round(avg_sojourn, 2),
        "avg_svc":      round(avg_svc, 2),
        "pct_waited":   round(pct_waited, 1),
        "max_wait":     round(max_wait, 2),
        "throughput":   round(n / (SIM_DURATION/60), 1),
    }, hourly_out


# ══════════════════════════════════════════════
# RUN ALL SCENARIOS
# ══════════════════════════════════════════════
results = []
for sc in SCENARIOS:
    analytic, p0, Cerl = erlang_c(sc["lambda"], sc["mu"], sc["c"])
    sim_stats, hourly  = simulate(sc["lambda"], sc["mu"], sc["c"])
    results.append({
        "scenario":  sc["name"],
        "label":     sc["label"],
        "lambda":    sc["lambda"],
        "mu":        sc["mu"],
        "c":         sc["c"],
        "analytic":  analytic,
        "sim":       sim_stats,
        "hourly":    hourly,
        "stable":    analytic is not None,
    })

# ── SAVE LOG CSV ──
with open(LOG, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["Scenario","Servers","Lambda","Mu","Rho","Util%","Lq","Wq_min",
                "W_min","ErlangC","SimAvgWait","SimSojourn","SimPctWaited","SimThroughput"])
    for r in results:
        a = r["analytic"] or {}
        s = r["sim"] or {}
        w.writerow([
            r["scenario"], r["c"], r["lambda"], r["mu"],
            a.get("rho","—"), a.get("util_pct","—"),
            a.get("Lq","—"), a.get("Wq_min","—"),
            a.get("W_min","—"), a.get("C_erlang","—"),
            s.get("avg_wait_min","—"), s.get("avg_sojourn","—"),
            s.get("pct_waited","—"), s.get("throughput","—"),
        ])

# ══════════════════════════════════════════════
# CONSOLE SUMMARY
# ══════════════════════════════════════════════
print("=" * 65)
print("  Queuing System Simulation — M/M/c Model")
print("  Hospital Outpatient Department · 8-Hour Shift")
print("=" * 65)
for r in results:
    a = r["analytic"] or {}
    s = r["sim"] or {}
    stable = "✓ Stable" if r["stable"] else "✗ UNSTABLE"
    print(f"\n  [{r['scenario']}] λ={r['lambda']}/hr  μ={r['mu']}/hr  c={r['c']}  {stable}")
    print(f"    Utilization : {a.get('util_pct','—')}%   Erlang C : {a.get('C_erlang','—')}")
    print(f"    Avg Queue   : {a.get('Lq','—')} patients")
    print(f"    Avg Wait    : {a.get('Wq_min','—')} min (analytical)  |  {s.get('avg_wait_min','—')} min (simulated)")
    print(f"    Avg Sojourn : {s.get('avg_sojourn','—')} min   Throughput: {s.get('throughput','—')} pts/hr")
print("\n" + "=" * 65)

# ══════════════════════════════════════════════
# BUILD HTML DASHBOARD
# ══════════════════════════════════════════════
results_json = json.dumps(results)
sc_names_json = json.dumps([r["scenario"] for r in results])

# Analytic KPI rows
def safe(d, k, fmt=str):
    if d is None: return "—"
    v = d.get(k)
    return fmt(v) if v is not None else "—"

analytic_rows = ""
for r in results:
    a = r["analytic"] or {}
    s = r["sim"] or {}
    stab_color = "#10b981" if r["stable"] else "#ef4444"
    stab_txt   = "Stable" if r["stable"] else "Unstable"
    util = a.get("util_pct", 0) or 0
    util_color = "#ef4444" if util >= 90 else "#f59e0b" if util >= 75 else "#10b981"
    analytic_rows += f"""<tr>
      <td class="mono accent">{r['scenario']}</td>
      <td class="mono">{r['lambda']}</td>
      <td class="mono">{r['mu']}</td>
      <td class="mono">{r['c']}</td>
      <td class="mono" style="color:{util_color}">{a.get('util_pct','—')}%</td>
      <td class="mono">{a.get('C_erlang','—')}</td>
      <td class="mono">{a.get('Lq','—')}</td>
      <td class="mono">{a.get('Wq_min','—')}</td>
      <td class="mono">{a.get('W_min','—')}</td>
      <td class="mono">{s.get('avg_wait_min','—')}</td>
      <td class="mono">{s.get('pct_waited','—')}%</td>
      <td class="mono">{s.get('throughput','—')}</td>
      <td style="color:{stab_color};font-family:var(--mono);font-size:11px;font-weight:600">{stab_txt}</td>
    </tr>"""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Queuing Simulation — Almas Shahriar</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<link href="https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;600;700&family=IBM+Plex+Mono:wght@400;600&display=swap" rel="stylesheet"/>
<style>
:root{{
  --bg:#05080f;--bg2:#0b0f1a;--bg3:#101525;--bg4:#161d2e;
  --border:#1a2236;--border2:#222d45;
  --accent:#6366f1;--a2:#06b6d4;--green:#22d3ee;--red:#f43f5e;--yellow:#fbbf24;--orange:#fb923c;
  --text:#e2e8f8;--muted:#4a5680;--subtle:#7a89b0;
  --font:'Space Grotesk',sans-serif;--mono:'IBM Plex Mono',monospace;
}}
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{background:var(--bg);color:var(--text);font-family:var(--font);min-height:100vh;overflow-x:hidden;}}
body::before{{
  content:'';position:fixed;inset:0;pointer-events:none;z-index:0;
  background:
    radial-gradient(ellipse 60% 40% at 20% 20%,rgba(99,102,241,0.07),transparent),
    radial-gradient(ellipse 50% 40% at 80% 80%,rgba(6,182,212,0.06),transparent);
}}
.page{{position:relative;z-index:1;max-width:1300px;margin:0 auto;padding:0 32px 100px;}}

/* HEADER */
header{{padding:56px 0 44px;border-bottom:1px solid var(--border2);margin-bottom:48px;}}
.eyebrow{{font-family:var(--mono);font-size:11px;color:var(--accent);letter-spacing:4px;text-transform:uppercase;margin-bottom:12px;display:flex;align-items:center;gap:10px;}}
.eyebrow::before{{content:'▶';font-size:8px;}}
h1{{font-size:clamp(30px,4.5vw,52px);font-weight:700;line-height:1.08;letter-spacing:-1px;}}
h1 em{{font-style:normal;
  background:linear-gradient(135deg,var(--accent),var(--a2));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.hdr-row{{margin-top:20px;display:flex;gap:8px;flex-wrap:wrap;align-items:center;}}
.chip{{font-family:var(--mono);font-size:10px;padding:4px 12px;background:var(--bg3);border:1px solid var(--border2);color:var(--muted);letter-spacing:1px;}}
.chip.hi{{border-color:var(--accent);color:var(--accent);background:rgba(99,102,241,0.08);}}

/* KPI */
.kpi-strip{{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:16px;margin-bottom:48px;}}
.kpi{{background:var(--bg2);border:1px solid var(--border2);padding:22px 20px;position:relative;}}
.kpi-bar{{position:absolute;top:0;left:0;right:0;height:2px;background:linear-gradient(90deg,var(--accent),var(--a2));}}
.kpi-bar.g{{background:linear-gradient(90deg,var(--green),#10b981);}}
.kpi-bar.r{{background:linear-gradient(90deg,var(--red),#f97316);}}
.kpi-bar.y{{background:linear-gradient(90deg,var(--yellow),var(--orange));}}
.kpi-label{{font-family:var(--mono);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:8px;}}
.kpi-val{{font-size:30px;font-weight:700;line-height:1;letter-spacing:-1px;}}
.kpi-sub{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:5px;}}

/* SECTION */
.section{{margin-bottom:56px;}}
.section-head{{display:flex;align-items:center;gap:14px;margin-bottom:24px;padding-bottom:14px;border-bottom:1px solid var(--border2);}}
.section-num{{font-family:var(--mono);font-size:10px;color:var(--accent);background:rgba(99,102,241,0.1);border:1px solid rgba(99,102,241,0.3);padding:3px 10px;letter-spacing:2px;}}
.section-title{{font-size:17px;font-weight:600;letter-spacing:-0.3px;}}
.section-desc{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-left:auto;}}

/* SCENARIO SELECTOR */
.sc-tabs{{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:20px;}}
.sc-tab{{font-family:var(--mono);font-size:11px;padding:7px 14px;background:var(--bg3);border:1px solid var(--border2);color:var(--muted);cursor:pointer;transition:all .2s;letter-spacing:0.5px;}}
.sc-tab:hover{{border-color:var(--accent);color:var(--accent);}}
.sc-tab.active{{background:rgba(99,102,241,0.15);border-color:var(--accent);color:var(--accent);}}

/* CHARTS */
.chart-grid{{display:grid;gap:16px;}}
.chart-grid.c2{{grid-template-columns:1fr 1fr;}}
.chart-grid.c3{{grid-template-columns:1fr 1fr 1fr;}}
@media(max-width:800px){{.chart-grid.c2,.chart-grid.c3{{grid-template-columns:1fr;}}}}
.chart-box{{background:var(--bg2);border:1px solid var(--border2);padding:22px;}}
.chart-label{{font-family:var(--mono);font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:14px;}}
.chart-wrap{{position:relative;height:230px;}}

/* METRIC CARDS */
.metric-grid{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin-bottom:20px;}}
@media(max-width:800px){{.metric-grid{{grid-template-columns:repeat(2,1fr);}}}}
.metric-card{{background:var(--bg3);border:1px solid var(--border2);padding:16px 18px;}}
.metric-label{{font-family:var(--mono);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);margin-bottom:6px;}}
.metric-val{{font-size:22px;font-weight:700;letter-spacing:-0.5px;}}
.metric-sub{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:3px;}}

/* TABLE */
.tbl-wrap{{overflow-x:auto;border:1px solid var(--border2);}}
table{{width:100%;border-collapse:collapse;font-size:12px;min-width:1000px;}}
thead{{background:var(--bg3);}}
th{{font-family:var(--mono);font-size:9px;letter-spacing:2px;text-transform:uppercase;color:var(--muted);padding:11px 14px;text-align:left;border-bottom:1px solid var(--border2);white-space:nowrap;}}
td{{padding:10px 14px;border-bottom:1px solid var(--border);}}
tr:last-child td{{border-bottom:none;}}
tr:hover td{{background:rgba(99,102,241,0.04);}}
td.mono{{font-family:var(--mono);font-size:11px;}}
td.accent{{color:var(--accent);font-weight:600;}}

/* FORMULA BOX */
.formula-grid{{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin-bottom:20px;}}
@media(max-width:700px){{.formula-grid{{grid-template-columns:1fr;}}}}
.formula-box{{background:var(--bg3);border:1px solid var(--border2);border-left:3px solid var(--accent);padding:18px 20px;}}
.formula-title{{font-family:var(--mono);font-size:10px;letter-spacing:2px;text-transform:uppercase;color:var(--accent);margin-bottom:10px;}}
.formula-eq{{font-family:var(--mono);font-size:13px;color:var(--text);line-height:1.8;}}
.formula-desc{{font-family:var(--mono);font-size:10px;color:var(--muted);margin-top:8px;line-height:1.7;}}

/* FOOTER */
footer{{margin-top:64px;padding-top:28px;border-top:1px solid var(--border2);display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:12px;}}
.fn{{font-size:14px;font-weight:700;letter-spacing:0.5px;}}
.fn span{{background:linear-gradient(135deg,var(--accent),var(--a2));-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;}}
.flinks{{display:flex;gap:16px;}}
.flinks a{{font-family:var(--mono);font-size:11px;color:var(--muted);text-decoration:none;transition:color .2s;}}
.flinks a:hover{{color:var(--accent);}}
</style>
</head>
<body>
<div class="page">

<header>
  <div class="eyebrow">Simulation & Modeling · IPE · BUET</div>
  <h1>Queuing System <em>Simulation</em><br/>M/M/c Model — Hospital Outpatient</h1>
  <div class="hdr-row">
    <span class="chip hi">6 Scenarios</span>
    <span class="chip hi">Discrete-Event Simulation</span>
    <span class="chip">Erlang C Formula</span>
    <span class="chip">8-Hour Shift · 480 min</span>
    <span class="chip">Generated {datetime.now().strftime("%d %b %Y · %H:%M")}</span>
  </div>
</header>

<!-- KPIs from best scenario (Optimal Config) -->
<div class="kpi-strip">
  <div class="kpi">
    <div class="kpi-bar"></div>
    <div class="kpi-label">Scenarios Simulated</div>
    <div class="kpi-val">6</div>
    <div class="kpi-sub">M/M/c configurations</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar g"></div>
    <div class="kpi-label">Simulation Duration</div>
    <div class="kpi-val">480</div>
    <div class="kpi-sub">minutes per scenario</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar y"></div>
    <div class="kpi-label">Arrival Rates</div>
    <div class="kpi-val">3–18</div>
    <div class="kpi-sub">patients/hour tested</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar r"></div>
    <div class="kpi-label">Unstable Scenarios</div>
    <div class="kpi-val">{sum(1 for r in results if not r["stable"])}</div>
    <div class="kpi-sub">ρ ≥ 1 (overloaded)</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar g"></div>
    <div class="kpi-label">Best Avg Wait</div>
    <div class="kpi-val">{min((r["sim"].get("avg_wait_min",999) for r in results if r["sim"]), default=0):.1f}m</div>
    <div class="kpi-sub">optimal configuration</div>
  </div>
  <div class="kpi">
    <div class="kpi-bar"></div>
    <div class="kpi-label">Service Rate (μ)</div>
    <div class="kpi-val">5/hr</div>
    <div class="kpi-sub">12 min avg service</div>
  </div>
</div>

<!-- SECTION 1: FORMULAS -->
<div class="section">
  <div class="section-head">
    <span class="section-num">01</span>
    <span class="section-title">M/M/c Analytical Framework</span>
    <span class="section-desc">Kendall notation · Poisson arrivals · Exponential service</span>
  </div>
  <div class="formula-grid">
    <div class="formula-box">
      <div class="formula-title">Traffic Intensity (ρ)</div>
      <div class="formula-eq">ρ = λ / (c · μ)</div>
      <div class="formula-desc">
        λ = arrival rate (pts/hr)<br/>
        μ = service rate (pts/hr)<br/>
        c = number of servers<br/>
        Stable only if ρ &lt; 1
      </div>
    </div>
    <div class="formula-box">
      <div class="formula-title">Erlang C — P(wait)</div>
      <div class="formula-eq">C(c,ρ) = P(arriving patient waits)<br/>= [(cρ)^c / c!(1-ρ)] · P₀</div>
      <div class="formula-desc">
        P₀ = probability system is empty<br/>
        Higher C → more patients wait
      </div>
    </div>
    <div class="formula-box">
      <div class="formula-title">Mean Queue Length (Lq)</div>
      <div class="formula-eq">Lq = C(c,ρ) · ρ / (1 - ρ)</div>
      <div class="formula-desc">
        Average number of patients waiting<br/>
        (not including those in service)
      </div>
    </div>
    <div class="formula-box">
      <div class="formula-title">Mean Wait & Sojourn (Wq, W)</div>
      <div class="formula-eq">Wq = Lq / λ<br/>W  = Wq + 1/μ</div>
      <div class="formula-desc">
        Wq = avg time waiting in queue<br/>
        W  = total time in system (wait + service)<br/>
        Little's Law: L = λ · W
      </div>
    </div>
  </div>
</div>

<!-- SECTION 2: SCENARIO DRILL-DOWN -->
<div class="section">
  <div class="section-head">
    <span class="section-num">02</span>
    <span class="section-title">Scenario Drill-Down</span>
    <span class="section-desc">Hourly arrivals · Queue length · Wait time per scenario</span>
  </div>
  <div class="sc-tabs" id="scTabs">
    {"".join(f'<div class="sc-tab{" active" if i==0 else ""}" onclick="selectScenario({i})">{r["scenario"]}</div>' for i,r in enumerate(results))}
  </div>
  <div class="metric-grid" id="metricCards"></div>
  <div class="chart-grid c2">
    <div class="chart-box">
      <div class="chart-label">Hourly Arrivals & Departures</div>
      <div class="chart-wrap"><canvas id="hourlyChart"></canvas></div>
    </div>
    <div class="chart-box">
      <div class="chart-label">Avg Queue Length & Wait Time by Hour</div>
      <div class="chart-wrap"><canvas id="queueChart"></canvas></div>
    </div>
  </div>
</div>

<!-- SECTION 3: CROSS-SCENARIO COMPARISON -->
<div class="section">
  <div class="section-head">
    <span class="section-num">03</span>
    <span class="section-title">Cross-Scenario Comparison</span>
    <span class="section-desc">Utilization · Wait time · Queue length across all configurations</span>
  </div>
  <div class="chart-grid c3" style="margin-bottom:16px;">
    <div class="chart-box">
      <div class="chart-label">Server Utilization (%)</div>
      <div class="chart-wrap"><canvas id="utilChart"></canvas></div>
    </div>
    <div class="chart-box">
      <div class="chart-label">Avg Queue Length (Lq) — Analytical</div>
      <div class="chart-wrap"><canvas id="lqChart"></canvas></div>
    </div>
    <div class="chart-box">
      <div class="chart-label">Avg Wait Time — Analytical vs Simulated</div>
      <div class="chart-wrap"><canvas id="waitCompChart"></canvas></div>
    </div>
  </div>
</div>

<!-- SECTION 4: FULL RESULTS TABLE -->
<div class="section">
  <div class="section-head">
    <span class="section-num">04</span>
    <span class="section-title">Complete Results Table</span>
    <span class="section-desc">Analytical (M/M/c) vs Discrete-Event Simulation</span>
  </div>
  <div class="tbl-wrap">
    <table>
      <thead><tr>
        <th>Scenario</th><th>λ/hr</th><th>μ/hr</th><th>c</th>
        <th>Util%</th><th>Erlang C</th><th>Lq</th>
        <th>Wq (anal.)</th><th>W (anal.)</th>
        <th>Wq (sim.)</th><th>% Waited</th><th>Throughput</th><th>Status</th>
      </tr></thead>
      <tbody>{analytic_rows}</tbody>
    </table>
  </div>
</div>

<footer>
  <div class="fn">Almas <span>Shahriar</span> · IPE BUET '26</div>
  <div style="font-family:var(--mono);font-size:10px;color:var(--muted);">Generated {datetime.now().strftime("%Y-%m-%d %H:%M")} · M/M/c Queuing Simulation</div>
  <div class="flinks">
    <a href="https://www.linkedin.com/in/almasshahriar/" target="_blank">LinkedIn</a>
    <a href="mailto:almasalif123@gmail.com">Email</a>
    <a href="https://github.com/almasshahriar" target="_blank">GitHub</a>
  </div>
</footer>
</div>

<script>
const RESULTS = {results_json};
const SC_NAMES = {sc_names_json};
const HOURS = {json.dumps(HOURS)};

const C = {{
  accent:'#6366f1', a2:'#06b6d4', green:'#22d3ee',
  red:'#f43f5e', yellow:'#fbbf24', orange:'#fb923c',
  muted:'#4a5680', grid:'rgba(26,34,54,0.9)'
}};

Chart.defaults.color = C.muted;
Chart.defaults.borderColor = C.grid;
Chart.defaults.font.family = "'IBM Plex Mono', monospace";
Chart.defaults.font.size = 10;

const baseOpts = () => ({{
  responsive:true, maintainAspectRatio:false,
  plugins:{{
    legend:{{display:true,labels:{{boxWidth:8,padding:12,color:C.muted}}}},
    tooltip:{{backgroundColor:'#0b0f1a',borderColor:'#222d45',borderWidth:1,
      titleColor:C.accent,bodyColor:'#e2e8f8',padding:10}}
  }},
  scales:{{
    x:{{grid:{{color:C.grid}},ticks:{{color:C.muted}}}},
    y:{{grid:{{color:C.grid}},ticks:{{color:C.muted}}}}
  }}
}});

// ── CROSS-SCENARIO CHARTS ──
const stableResults = RESULTS.filter(r => r.stable);
const allNames = RESULTS.map(r => r.scenario);

// Utilization
new Chart(document.getElementById('utilChart'), {{
  type:'bar',
  data:{{
    labels: allNames,
    datasets:[{{
      label:'Utilization %',
      data: RESULTS.map(r => r.analytic ? r.analytic.util_pct : null),
      backgroundColor: RESULTS.map(r => {{
        const u = r.analytic ? r.analytic.util_pct : 0;
        return u >= 90 ? 'rgba(244,63,94,0.35)' : u >= 75 ? 'rgba(251,191,36,0.35)' : 'rgba(34,211,238,0.3)';
      }}),
      borderColor: RESULTS.map(r => {{
        const u = r.analytic ? r.analytic.util_pct : 0;
        return u >= 90 ? C.red : u >= 75 ? C.yellow : C.green;
      }}),
      borderWidth:1
    }}]
  }},
  options:{{...baseOpts(), scales:{{
    x:{{grid:{{color:C.grid}},ticks:{{color:C.muted,maxRotation:30}}}},
    y:{{grid:{{color:C.grid}},ticks:{{color:C.muted,callback:v=>v+'%'}},max:120}}
  }}}}
}});

// Lq
new Chart(document.getElementById('lqChart'), {{
  type:'bar',
  data:{{
    labels: allNames,
    datasets:[{{
      label:'Avg Queue (Lq)',
      data: RESULTS.map(r => r.analytic ? r.analytic.Lq : null),
      backgroundColor:'rgba(99,102,241,0.3)', borderColor:C.accent, borderWidth:1
    }}]
  }},
  options:{{...baseOpts(), scales:{{
    x:{{grid:{{color:C.grid}},ticks:{{color:C.muted,maxRotation:30}}}},
    y:{{grid:{{color:C.grid}},ticks:{{color:C.muted}}}}
  }}}}
}});

// Wait comparison
new Chart(document.getElementById('waitCompChart'), {{
  type:'bar',
  data:{{
    labels: allNames,
    datasets:[
      {{label:'Analytical Wq (min)', data:RESULTS.map(r=>r.analytic?r.analytic.Wq_min:null),
        backgroundColor:'rgba(99,102,241,0.3)',borderColor:C.accent,borderWidth:1}},
      {{label:'Simulated Wq (min)', data:RESULTS.map(r=>r.sim?r.sim.avg_wait_min:null),
        backgroundColor:'rgba(6,182,212,0.3)',borderColor:C.a2,borderWidth:1}}
    ]
  }},
  options:{{...baseOpts(), scales:{{
    x:{{grid:{{color:C.grid}},ticks:{{color:C.muted,maxRotation:30}}}},
    y:{{grid:{{color:C.grid}},ticks:{{color:C.muted}}}}
  }}}}
}});

// ── SCENARIO DRILL-DOWN ──
let hourlyChart = null, queueChart = null;

function selectScenario(idx) {{
  document.querySelectorAll('.sc-tab').forEach((t,i) => t.classList.toggle('active', i===idx));
  const r = RESULTS[idx];
  const a = r.analytic || {{}};
  const s = r.sim || {{}};
  const hourly = r.hourly || [];

  // Metric cards
  const mc = document.getElementById('metricCards');
  const util = a.util_pct || 0;
  const utilColor = util >= 90 ? C.red : util >= 75 ? C.yellow : C.green;
  mc.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">Server Utilization</div>
      <div class="metric-val" style="color:${{utilColor}}">${{util}}%</div>
      <div class="metric-sub">ρ = ${{a.rho || '—'}}</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Analytical Wq</div>
      <div class="metric-val">${{a.Wq_min || '—'}} min</div>
      <div class="metric-sub">avg queue wait</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Simulated Wq</div>
      <div class="metric-val">${{s.avg_wait_min || '—'}} min</div>
      <div class="metric-sub">${{s.pct_waited || '—'}}% of patients waited</div>
    </div>
    <div class="metric-card">
      <div class="metric-label">Throughput</div>
      <div class="metric-val">${{s.throughput || '—'}}</div>
      <div class="metric-sub">patients/hour served</div>
    </div>`;

  // Hourly arrivals chart
  if (hourlyChart) hourlyChart.destroy();
  hourlyChart = new Chart(document.getElementById('hourlyChart'), {{
    type:'bar',
    data:{{
      labels: hourly.map(h=>h.hour),
      datasets:[
        {{label:'Arrivals', data:hourly.map(h=>h.arrivals),
          backgroundColor:'rgba(99,102,241,0.3)',borderColor:C.accent,borderWidth:1}},
        {{label:'Departures', data:hourly.map(h=>h.departures),
          backgroundColor:'rgba(6,182,212,0.3)',borderColor:C.a2,borderWidth:1}}
      ]
    }},
    options: baseOpts()
  }});

  // Queue + wait chart
  if (queueChart) queueChart.destroy();
  queueChart = new Chart(document.getElementById('queueChart'), {{
    type:'line',
    data:{{
      labels: hourly.map(h=>h.hour),
      datasets:[
        {{label:'Avg Queue Length', data:hourly.map(h=>h.avg_queue),
          borderColor:C.accent,backgroundColor:'rgba(99,102,241,0.1)',
          borderWidth:2,fill:true,tension:0.4,pointRadius:3,yAxisID:'y'}},
        {{label:'Avg Wait (min)', data:hourly.map(h=>h.avg_wait),
          borderColor:C.orange,backgroundColor:'rgba(251,146,60,0.1)',
          borderWidth:2,fill:false,tension:0.4,pointRadius:3,yAxisID:'y1'}}
      ]
    }},
    options:{{...baseOpts(), scales:{{
      x:{{grid:{{color:C.grid}},ticks:{{color:C.muted}}}},
      y:{{grid:{{color:C.grid}},ticks:{{color:C.muted}},title:{{display:true,text:'Queue Length',color:C.muted}}}},
      y1:{{position:'right',grid:{{drawOnChartArea:false}},
        ticks:{{color:C.muted}},title:{{display:true,text:'Wait (min)',color:C.muted}}}}
    }}}}
  }});
}}

selectScenario(0);
</script>
</body>
</html>"""

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write(html)

print(f"  Dashboard : {OUTPUT}")
print(f"  Log CSV   : {LOG}")
print("  Done.")
