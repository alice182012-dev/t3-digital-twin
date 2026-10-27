cd /Users/maianhtran/Documents/3Di/Case-study-sim-center/airflow_clone/t3-digital-twin
env_vars=$(grep -oE '^[A-Z_][A-Z0-9_]*=' .env.example | tr -d '=' | sort -u)
all_vars=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*' compose.yml | tr -d '${' | sort -u)
req_vars=$(grep -oE '\$\{[A-Z_][A-Z0-9_]*:\?' compose.yml | tr -d '${:?' | sort -u)
echo "1. .env.example against compose.yml"
echo "   listed in .env.example but not read by compose.yml: [$(comm -23 <(echo "$env_vars") <(echo "$all_vars") | tr '\n' ' ')]"
echo "   required by compose.yml (:?) but not listed:        [$(comm -13 <(echo "$env_vars") <(echo "$req_vars") | tr '\n' ' ')]"
echo "   required variables: $(echo $req_vars)"
echo "   THREEDI_API_PERSONAL_API_TOKEN listed: $(grep -c '^THREEDI_API_PERSONAL_API_TOKEN=' .env.example)   VALHALLA_PORT or FLOODMAP_FRONTEND_PORT listed: $(grep -cE '^(VALHALLA_PORT|FLOODMAP_FRONTEND_PORT)=' .env.example)"
echo "2. links to [[SW Architecture]] outside artifacts/raw, in the main tree (excluding logs, stories, blockers, plans that quote the name)"
n=$(grep -rln "SW Architecture" . --include='*.md' --include='*.py' --include='*.yml' --include='*.ts' --include='*.tsx' --exclude-dir=node_modules --exclude-dir=.git --exclude-dir=.claude --exclude-dir=raw 2>/dev/null | grep -v "artifacts/logs/\|artifacts/docs/user-stories/\|artifacts/docs/blockers/\|artifacts/docs/claude-plan/\|artifacts/TODOS.md" | wc -l | tr -d ' ')
echo "   files with a match: $n"
echo "3. 3Di orchestration page"
echo "   lines with */15: $(grep -c '\*/15' artifacts/docs/concepts/3di-simulation-orchestration.md)   lines with max_active_runs=2: $(grep -c 'max_active_runs=2' artifacts/docs/concepts/3di-simulation-orchestration.md)"
echo "4. files named in PINNED_COMMIT.md that do not exist under floodmap/graphhopper-maps"
cd floodmap/graphhopper-maps
missing=0
for f in $(grep -oE '`[A-Za-z0-9_./-]+\.(ts|tsx|js|example|conf|json|md)`|`(src|test)/[A-Za-z0-9_./-]+/?`|`Dockerfile`' PINNED_COMMIT.md | tr -d '`' | sort -u); do
  [ -e "$f" ] || [ -e "src/floodmap/$f" ] || [ -e "src/stores/$f" ] || [ -e "src/map/$f" ] || { echo "   missing: $f"; missing=1; }
done
[ $missing = 0 ] && echo "   none missing"
