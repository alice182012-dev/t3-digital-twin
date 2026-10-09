#!/usr/bin/env bash
# Evidence for US-096. Read-only. Run from the repository root on the Mac. Needs the gh CLI signed in.
echo "--- Python suites"
(cd scripts/routing_reference && python3 -m pytest -q 2>&1 | tail -1)
(cd scripts/routing_proof && python3 -m unittest 2>&1 | tail -3 | tr '\n' ' '; echo)
(cd scripts/routing_experiments && python3 -m unittest 2>&1 | tail -3 | tr '\n' ' '; echo)
echo "--- Java suite, run by the java-module workflow on GitHub for commit 66c9883"
/opt/homebrew/bin/gh run view 37880057761 --repo alice182012-dev/t3-digital-twin --log 2>&1 | LC_ALL=C grep -a "Tests run: 1[0-9][0-9],\|StickyClosureTest\|BUILD" | sed 's/^test\tTest the module\t[0-9TZ:.-]* //'
