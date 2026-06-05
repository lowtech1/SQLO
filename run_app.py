"""
LLM-R2: Research & Benchmark Runner
===================================
Launcher for benchmark, tests, and research reports.
No UI — pure command-line.

Usage:
    python run_app.py benchmark   # Run research benchmark
    python run_app.py tests      # Run all tests
    python run_app.py dss        # Run DSS tests only
    python run_app.py all        # Run tests + benchmark
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.makedirs("results/benchmarks", exist_ok=True)
os.makedirs("results/research", exist_ok=True)


def run_benchmark():
    from my_exp.research_report import run_benchmark, generate_research_report
    from datetime import datetime
    results = run_benchmark(use_llm=False)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    import json
    with open(f"results/benchmarks/benchmark_{ts}.json", "w") as f:
        json.dump(results, f, indent=2)
    report_path = f"results/research/report_{ts}.md"
    generate_research_report(results, report_path)
    print(f"\nBenchmark complete.")
    print(f"  Results : results/benchmarks/benchmark_{ts}.json")
    print(f"  Report  : {report_path}")
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_app.py [benchmark|tests|dss|all]")
        sys.exit(1)

    cmd = sys.argv[1]

    if cmd == "benchmark":
        run_benchmark()

    elif cmd == "tests":
        import subprocess
        subprocess.run([sys.executable, "my_exp/core/run_tests.py"], check=False)

    elif cmd == "dss":
        import subprocess
        subprocess.run([sys.executable, "my_exp/dss/test_dss.py"], check=False)

    elif cmd == "all":
        import subprocess
        subprocess.run([sys.executable, "my_exp/core/run_tests.py"], check=False)
        print("\n" + "=" * 70)
        subprocess.run([sys.executable, "my_exp/dss/test_dss.py"], check=False)
        print("\n" + "=" * 70)
        run_benchmark()

    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python run_app.py [benchmark|tests|dss|all]")
