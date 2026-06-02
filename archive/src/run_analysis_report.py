# ============================================================
# run_analysis_report.py
# Phan tich ket qua va tao bang so sanh cho luan van
# ============================================================
import os
from dotenv import load_dotenv
load_dotenv()

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

# Co dinh font de hien thi tieng Viet
plt.rcParams['font.family'] = 'DejaVu Sans'

def analyze_results(result_file, dataset_name, llm_name):
    """Phan tich ket qua tu mot file CSV"""
    if not os.path.exists(result_file):
        print(f"[WARN] Khong tim thay: {result_file}")
        return None

    df = pd.read_csv(result_file)

    print(f"\n{'='*70}")
    print(f"  PHAN TICH: {dataset_name} ({llm_name})")
    print(f"{'='*70}")

    # So luong query
    total = len(df)
    print(f"\n1. TONG QUAN")
    print(f"   Tong so query: {total}")

    # Kiem tra cot latency (neu co trong file)
    latency_cols = [c for c in df.columns if 'latency' in c.lower()]
    if latency_cols:
        for col in latency_cols:
            valid = df[df[col] != 'NA'][col].astype(float)
            improved = (valid < 1.0).sum() if 'ratio' in col.lower() else (valid > 0).sum()
            print(f"   {col}: {improved}/{len(valid)} queries duoc cai thien")

    # Thong ke rules
    rule_cols = [c for c in df.columns if 'rules' in c.lower() or 'activated' in c.lower()]
    if rule_cols:
        rule_col = rule_cols[0]
        all_rules = []
        for rules_str in df[rule_col]:
            if pd.notna(rules_str) and rules_str != '[]':
                import ast
                try:
                    rules = ast.literal_eval(rules_str)
                    all_rules.extend(rules)
                except:
                    pass

        if all_rules:
            rule_counts = pd.Series(all_rules).value_counts()
            print(f"\n2. RULES DUOC SU DUNG NHIEU NHAT")
            print(f"   (Top 10)")
            for rule, count in rule_counts.head(10).items():
                pct = count / total * 100
                print(f"   {rule:45s} {count:4d} lan ({pct:5.1f}%)")

            # The loai rule
            print(f"\n3. THONG KE THEO THE LOAI RULE")
            agg_rules = [r for r in all_rules if 'AGGREGATE' in r.upper()]
            filt_rules = [r for r in all_rules if 'FILTER' in r.upper()]
            join_rules = [r for r in all_rules if 'JOIN' in r.upper()]
            proj_rules = [r for r in all_rules if 'PROJECT' in r.upper()]
            sort_rules = [r for r in all_rules if 'SORT' in r.upper()]
            union_rules = [r for r in all_rules if 'UNION' in r.upper()]

            categories = {
                'Aggregate Rules': agg_rules,
                'Filter Rules': filt_rules,
                'Join Rules': join_rules,
                'Project Rules': proj_rules,
                'Sort Rules': sort_rules,
                'Union Rules': union_rules,
            }
            for cat, rules_list in categories.items():
                if rules_list:
                    print(f"   {cat:20s}: {len(rules_list):4d} lan su dung")

    # Ve bieu do
    if all_rules:
        create_charts(all_rules, dataset_name, llm_name)

    return df


def create_charts(all_rules, dataset_name, llm_name):
    """Ve bieu do phan tich"""
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))

    # Bieu do 1: Top 10 rules
    rule_counts = pd.Series(all_rules).value_counts().head(10)
    colors = plt.cm.Blues(np.linspace(0.4, 0.9, len(rule_counts)))

    axes[0].barh(range(len(rule_counts)), rule_counts.values, color=colors[::-1])
    axes[0].set_yticks(range(len(rule_counts)))
    axes[0].set_yticklabels(rule_counts.index, fontsize=8)
    axes[0].set_xlabel('So lan su dung')
    axes[0].set_title(f'Top 10 Rewrite Rules\n{dataset_name} - {llm_name}')
    axes[0].invert_yaxis()

    # Bieu do 2: Phan bo theo the loai
    categories = {
        'Aggregate': [r for r in all_rules if 'AGGREGATE' in r.upper()],
        'Filter': [r for r in all_rules if 'FILTER' in r.upper()],
        'Join': [r for r in all_rules if 'JOIN' in r.upper()],
        'Project': [r for r in all_rules if 'PROJECT' in r.upper()],
        'Sort': [r for r in all_rules if 'SORT' in r.upper()],
        'Union': [r for r in all_rules if 'UNION' in r.upper()],
        'Calc': [r for r in all_rules if 'CALC' in r.upper()],
    }

    cat_counts = {k: len(v) for k, v in categories.items() if len(v) > 0}
    if cat_counts:
        colors2 = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2']
        axes[1].bar(cat_counts.keys(), cat_counts.values(), color=colors2[:len(cat_counts)])
        axes[1].set_xlabel('The loai Rule')
        axes[1].set_ylabel('So lan su dung')
        axes[1].set_title(f'Phan bo Rules theo The Loai\n{dataset_name} - {llm_name}')
        for i, (k, v) in enumerate(cat_counts.items()):
            axes[1].text(i, v + 0.5, str(v), ha='center', fontsize=9)

    plt.tight_layout()
    os.makedirs('../results/figures', exist_ok=True)
    filename = f'../results/figures/analysis_{dataset_name}_{llm_name.replace(" ", "_")}.png'
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    print(f"\n   [INFO] Bieu do luu tai: {filename}")
    plt.close()


def compare_llms(llm1_file, llm2_file, dataset):
    """So sanh 2 LLM (GPT-3.5 vs Claude Opus 4.6)"""

    print(f"\n{'='*70}")
    print(f"  SO SANH: GPT-3.5 vs CLAUDE OPUS 4.6 ({dataset})")
    print(f"{'='*70}")

    df1 = pd.read_csv(llm1_file) if os.path.exists(llm1_file) else None
    df2 = pd.read_csv(llm2_file) if os.path.exists(llm2_file) else None

    # Bang so sanh
    print(f"\n{'STT':<4} {'Chi tieu':<35} {'GPT-3.5':>15} {'Claude Opus 4.6':>18}")
    print("-" * 75)

    metrics = []

    if df1 is not None:
        rules1 = []
        for r in df1.get('activated_rules_gpt', []):
            if pd.notna(r) and r != '[]':
                try:
                    import ast
                    rules1.extend(ast.literal_eval(r))
                except:
                    pass
        metrics.append(('So query', len(df1), len(df2) if df2 is not None else 'N/A'))

        # Unique rules
        unique1 = len(set(rules1))
        unique2 = 0
        if df2 is not None:
            rules2 = []
            for r in df2.get('activated_rules_gpt', []):
                if pd.notna(r) and r != '[]':
                    try:
                        rules2.extend(ast.literal_eval(r))
                    except:
                        pass
            unique2 = len(set(rules2))

        metrics.append(('So luong rules duoc su dung', unique1, unique2))

    if df2 is not None:
        rules2 = []
        for r in df2.get('activated_rules_gpt', []):
            if pd.notna(r) and r != '[]':
                try:
                    import ast
                    rules2.extend(ast.literal_eval(r))
                except:
                    pass

        # Top 5 rules moi LLM
        top2 = pd.Series(rules2).value_counts().head(5)

    for i, (name, v1, v2) in enumerate(metrics):
        print(f"  {i+1:<3} {name:<35} {str(v1):>15} {str(v2):>18}")

    # Tao bieu do so sanh
    if df1 is not None and df2 is not None:
        fig, ax = plt.subplots(figsize=(8, 4))
        x = np.arange(3)
        width = 0.35

        vals1 = [len(df1), unique1, len(rules1)]
        vals2 = [len(df2), unique2, len(rules2)]

        bars1 = ax.bar(x - width/2, vals1, width, label='GPT-3.5', color='#74add1')
        bars2 = ax.bar(x + width/2, vals2, width, label='Claude Opus 4.6', color='#f46d43')

        ax.set_ylabel('So luong')
        ax.set_title(f'So sanh GPT-3.5 vs Claude Opus 4.6\nDataset: {dataset}')
        ax.set_xticks(x)
        ax.set_xticklabels(['Tong Query', 'Unique Rules', 'Tong Rules su dung'])
        ax.legend()

        for bar in bars1:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   str(int(bar.get_height())), ha='center', fontsize=9)
        for bar in bars2:
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                   str(int(bar.get_height())), ha='center', fontsize=9)

        os.makedirs('../results/figures', exist_ok=True)
        plt.tight_layout()
        plt.savefig(f'../results/figures/comparison_{dataset}.png', dpi=150)
        print(f"\n   [INFO] Bieu do so sanh luu tai: ../results/figures/comparison_{dataset}.png")
        plt.close()


# ========================
# CHAY PHAN TICH
# ========================
if __name__ == '__main__':
    print("=" * 70)
    print("  LLM-R2 — BAO CAO PHAN TICH THUC NGHIEM")
    print("=" * 70)

    results_dir = '../results'

    # 1. Phan tich Claude Opus 4.6 tren cac dataset
    datasets = ['dsb', 'tpch', 'job_syn']
    llm_name = 'Claude Opus 4.6'

    for dataset in datasets:
        result_file = f'{results_dir}/gpt_{dataset}_claude_opus_queryCL_updated.csv'
        analyze_results(result_file, dataset, llm_name)

    # 2. So sanh voi GPT-3.5 (neu co ket qua)
    for dataset in datasets:
        gpt_file = f'{results_dir}/gpt_{dataset}_one_promo_queryCL_updated.csv'
        claude_file = f'{results_dir}/gpt_{dataset}_claude_opus_queryCL_updated.csv'
        if os.path.exists(gpt_file) or os.path.exists(claude_file):
            compare_llms(gpt_file, claude_file, dataset)

    print(f"\n{'='*70}")
    print("  HOAN TAT PHAN TICH")
    print("  Ket qua: ../results/")
    print("  Bieu do: ../results/figures/")
    print(f"{'='*70}")
