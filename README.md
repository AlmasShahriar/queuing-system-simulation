# Queuing System Simulation — M/M/c Model

> Discrete-event simulation of a hospital outpatient queuing system using the **M/M/c** model — implemented from scratch in pure Python.
> Built on core Industrial & Production Engineering principles taught at BUET.

![Python](https://img.shields.io/badge/Python-3.8+-blue?style=flat-square&logo=python)
![Model](https://img.shields.io/badge/Model-M%2FM%2Fc_Queue-indigo?style=flat-square)
![Zero Dependencies](https://img.shields.io/badge/pip_deps-none-brightgreen?style=flat-square)
![Output](https://img.shields.io/badge/output-standalone_HTML-purple?style=flat-square)

---

## What It Does

Simulates a multi-server queuing system across **6 real-world scenarios** (morning rush, emergency peak, overnight shift, etc.) and compares:

- **Analytical results** — closed-form M/M/c / Erlang C formulas
- **Simulated results** — discrete-event simulation (DES) over an 8-hour shift

### Dashboard Sections

| # | Section | What's Inside |
|---|---------|---------------|
| 01 | **M/M/c Framework** | Key formulas with notation: ρ, Erlang C, Lq, Wq, W |
| 02 | **Scenario Drill-Down** | Hourly arrivals, queue length, wait time per scenario |
| 03 | **Cross-Scenario Comparison** | Utilization, Lq, Wq — analytical vs simulated |
| 04 | **Full Results Table** | All 6 scenarios with every metric side by side |

---

## Techniques Used

| Technique | Description |
|-----------|-------------|
| **M/M/c Queue Model** | Markovian arrivals (Poisson), exponential service, c parallel servers |
| **Erlang C Formula** | Probability that an arriving patient must wait |
| **Discrete-Event Simulation** | Event-driven clock, exponential inter-arrival & service times |
| **Little's Law** | `L = λ · W` — connects queue length, arrival rate, and time |
| **Stability Analysis** | Flags scenarios where ρ ≥ 1 (system collapses) |

---

## Project Structure

```
queuing-system-simulation/
├── src/
│   └── simulation.py          ← Main script: DES engine + M/M/c analytics + dashboard
├── data/
│   └── simulation_log.csv     ← Auto-generated results log
├── output/
│   └── dashboard.html         ← Interactive HTML dashboard
└── README.md
```

---

## Getting Started

**Requirements:** Python 3.8+ · No pip installs needed

```bash
# Clone the repo
git clone https://github.com/almasshahriar/queuing-system-simulation
cd queuing-system-simulation

# Run the simulation
python src/simulation.py

# Open the dashboard
open output/dashboard.html    # macOS
start output/dashboard.html   # Windows
```

---

## Sample Console Output

```
[Morning Rush]    λ=12/hr  μ=5/hr  c=3  ✓ Stable
  Utilization : 80.0%   Erlang C : 0.6472
  Avg Queue   : 2.589 patients
  Avg Wait    : 0.216 min (analytical)  |  7.5 min (simulated)

[Evening Surge]   λ=10/hr  μ=5/hr  c=2  ✗ UNSTABLE
  → Queue grows unboundedly — add a 3rd server

[Optimal Config]  λ=12/hr  μ=5/hr  c=4  ✓ Stable
  Utilization : 60.0%   Erlang C : 0.287
  Avg Wait    : 0.036 min (analytical)  |  1.41 min (simulated)
```

---

## Key Formulas

**Traffic Intensity:**
```
ρ = λ / (c · μ)        [stable only if ρ < 1]
```

**Erlang C (probability of waiting):**
```
C(c,ρ) = [(cρ)^c / c!(1−ρ)] · P₀
```

**Mean queue length & wait time:**
```
Lq = C(c,ρ) · ρ / (1 − ρ)
Wq = Lq / λ
W  = Wq + 1/μ          [Little's Law: L = λ·W]
```

---

## Scenarios Simulated

| Scenario | λ (pts/hr) | μ (pts/hr) | Servers (c) | Status |
|----------|-----------|-----------|-------------|--------|
| Morning Rush | 12 | 5 | 3 | ✅ Stable |
| Afternoon Calm | 6 | 5 | 2 | ✅ Stable |
| Evening Surge | 10 | 5 | 2 | ❌ Unstable |
| Night Shift | 3 | 5 | 1 | ✅ Stable |
| Emergency Peak | 18 | 5 | 4 | ✅ Stable |
| Optimal Config | 12 | 5 | 4 | ✅ Stable |

---

## Author

**Almas Shahriar**
B.Sc. Industrial & Production Engineering · BUET ('26)

[![LinkedIn](https://img.shields.io/badge/LinkedIn-almasshahriar-blue?style=flat-square&logo=linkedin)](https://www.linkedin.com/in/almasshahriar/)
[![GitHub](https://img.shields.io/badge/GitHub-almasshahriar-black?style=flat-square&logo=github)](https://github.com/almasshahriar)
[![Email](https://img.shields.io/badge/Email-almasalif123@gmail.com-red?style=flat-square&logo=gmail)](mailto:almasalif123@gmail.com)

---

## License

MIT License — free to use, adapt, and build upon.****
