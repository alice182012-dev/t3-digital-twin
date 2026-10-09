"""Evidence for US-093. Reads the final result file and prints the shares. Run from the repository root:
python3 -I artifacts/docs/stories/evidence/us-093-final-check.py"""
import collections, json, statistics

d = json.load(open("marie-curie/option_a_real_replay2_final_seed1.json"))
R, pc = d["records"], d["pair_classes"]
cls = lambda r: pc[f"{r['pair'][0]}-{r['pair'][1]}"]
n = len(R)
oc = collections.Counter(r["outcome"] for r in R)
route = oc["same"] + oc["sticky_longer"] + oc["sticky_no_route"]
print(f"result file: option_a_real_replay2_final_seed1.json  ({len(d['tables'])} tables, {d['n_pairs']} pairs, budget {d['budget']:,}, {d['wall_s']/60:.1f} min)")
print(f"searches {n:,}   exact {sum(r['exact'] for r in R):,} ({sum(r['exact'] for r in R)/n:.4f})   bar 97 percent per vehicle")
for v in ("motorbike", "car", "truck", "foot"):
    x = [r for r in R if r["vehicle"] == v]
    print(f"  {v:10} exact {sum(r['exact'] for r in x)/len(x):.4f}")
print(f"outcomes   same {oc['same']:,}   sticky longer {oc['sticky_longer']}   sticky no route {oc['sticky_no_route']}   neither {oc['neither']}   inexact {oc['inexact']}")
print(f"where arrival-only has a route ({route:,}):  same {oc['same']/route:.1%}   longer {oc['sticky_longer']/route:.2%}   no route {oc['sticky_no_route']/route:.2%}")
for k in ("under_2km", "2_to_5km", "over_5km"):
    x = [r for r in R if cls(r) == k and r["outcome"] in ("same", "sticky_longer", "sticky_no_route")]
    print(f"  {k:10} longer {sum(r['outcome']=='sticky_longer' for r in x)/len(x):.1%}")
ex = [r["extra_s"] for r in R if r["outcome"] == "sticky_longer"]
print(f"extra time of the {len(ex)} longer routes: median {statistics.median(ex):.0f} s   mean {statistics.mean(ex):.0f} s   max {max(ex):.0f} s")
