"""
LLM-R2-Enhanced: Interactive SQL Optimization Advisor
==================================================
Launcher script for Streamlit app and benchmark runner.

Usage:
    python run_app.py              # Run Streamlit app
    python run_app.py benchmark    # Run research benchmark
    python run_app.py tests        # Run all tests
    python run_app.py dss          # Run DSS tests only
"""

import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default: run Streamlit app
        os.system("cd d:/DoAnTotNghiep/LLM-R2-1 && streamlit run my_exp/ui/app.py")
    else:
        cmd = sys.argv[1]
        if cmd == "benchmark":
            from my_exp.research_report import run_benchmark, generate_research_report
            from datetime import datetime
            os.makedirs("results/benchmarks", exist_ok=True)
            os.makedirs("results/research", exist_ok=True)
            results = run_benchmark(use_llm=False)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            import json
            with open(f"results/benchmarks/benchmark_{ts}.json", "w") as f:
                json.dump(results, f, indent=2)
            report = generate_research_report(results, f"results/research/report_{ts}.md")
            print(f"\nBenchmark complete. Results: results/benchmarks/benchmark_{ts}.json")
            print(f"Report: results/research/report_{ts}.md")
        elif cmd == "tests":
            os.system("python my_exp/core/run_tests.py")
        elif cmd == "dss":
            os.system("python my_exp/dss/test_dss.py")
        elif cmd == "all":
            os.system("python my_exp/core/run_tests.py")
            print("\n" + "=" * 70)
            os.system("python my_exp/dss/test_dss.py")
            print("\n" + "=" * 70)
            from my_exp.research_report import run_benchmark, generate_research_report
            from datetime import datetime
            os.makedirs("results/benchmarks", exist_ok=True)
            os.makedirs("results/research", exist_ok=True)
            results = run_benchmark(use_llm=False)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            import json
            with open(f"results/benchmarks/benchmark_{ts}.json", "w") as f:
                json.dump(results, f, indent=2)
            generate_research_report(results, f"results/research/report_{ts}.md")
            print(f"\nAll complete!")
        else:
            print(f"Unknown command: {cmd}")
            print("Usage: python run_app.py [benchmark|tests|dss|all]")
