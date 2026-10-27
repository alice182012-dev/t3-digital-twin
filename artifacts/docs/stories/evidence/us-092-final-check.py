"""Evidence for US-092. Reads the final result file and prints the limit sweep. Run from the repository root:
python3 -I artifacts/docs/stories/evidence/us-092-final-check.py"""
import collections, json, statistics as st

d = json.load(open("marie-curie/real_run_replay2_final_seed1.json"))
ls, ch = d["us092_limit_sweep"], d["us092_conclusion_changes"]
print(f"result file: real_run_replay2_final_seed1.json  ({len(ls)} settings, {d['n_pairs']} pairs, limits {d['limits']})")
agg, reg = collections.defaultdict(lambda: collections.defaultdict(list)), collections.defaultdict(list)
for v in ls.values():
    for r in v["rows"]:
        for m in ("closed_km", "route_share", "mean_detour_s", "violation_rate"):
            agg[r["plan_limit"]][m].append(r[m])
    for k, x in v["regret"].items():
        reg[k].append(x)
print("plan limit   closed km   route share   detour s   violation")
for pl in sorted(agg):
    a = agg[pl]
    print(f"  {pl:3} cm     {st.mean(a['closed_km']):6.1f}      {st.mean(a['route_share']):.3f}        {st.mean(a['mean_detour_s']):5.0f}      {st.mean(a['violation_rate']):.3f}")
print("regret, plan limit judged at a lower limit:  40 at 20 cm", f"{st.mean(reg['40|20']):.3f}", "  40 at 30", f"{st.mean(reg['40|30']):.3f}", "  30 at 20", f"{st.mean(reg['30|20']):.3f}")
print(f"settings where the best limit changes: {len(ch)} of {len(ls)}  (violations {sum(c['violations_changed'] for c in ch)}, ranking {sum(c['rank_changed'] for c in ch)})")
fs = collections.defaultdict(list)
for k, v in d["us092_fraction_sweep"].items():
    fs[k.split("|")[-1]].append(v["share_recommended_under_precaution"])
print("precaution fraction -> share of routes under the precaution depth:", {f: round(st.mean(x), 3) for f, x in sorted(fs.items())})
