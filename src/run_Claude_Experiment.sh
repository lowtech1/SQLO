#!/bin/bash
# ============================================================
# run_Claude_Experiment.sh
# Chay thuc nghiem LLM-R2 voi Claude Opus 4.6
#
# Cach su dung:
#   bash run_Claude_Experiment.sh
#
# Bien moi truong can thiet:
#   export ANTHROPIC_API_KEY="sk-ant-..."
#
# Cau hinh (thay doi tai day):
#   - MODEL: model Anthropic (claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5-20251001)
#   - DATASET: dsb | tpch | job_syn
#   - METHOD: queryCL | sentbert | plan | random
#   - NUM_PROMPTS: so luong demonstration (1-5)
# ============================================================

# ==== CAU HINH ====
MODEL="claude-opus-4-6"        # Model Anthropic (opus | sonnet | haiku)
DATASET="dsb"                   # Dataset: dsb | tpch | job_syn
METHOD="queryCL"                # Demonstration method: queryCL | sentbert | plan | random
NUM_PROMPTS=1                   # So luong demo (recommend: 1-3)

# ==== KIEN NGHI ====
# Model tot nhat cho rewrite rules: claude-opus-4-6
# Model nhanh hon: claude-sonnet-4-6
# Model nhanh nhat (haiku): claude-haiku-4-5-20251001

# ==== LAY API KEY ====
if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "[ERROR] ANTHROPIC_API_KEY chua duoc dat."
    echo "Vui long chay: export ANTHROPIC_API_KEY='sk-ant-...'"
    exit 1
fi

echo "=============================================="
echo "  LLM-R2 + Claude Opus 4.6 Experiment"
echo "=============================================="
echo "  Model:        $MODEL"
echo "  Dataset:      $DATASET"
echo "  Method:       $METHOD"
echo "  Num Prompts:  $NUM_PROMPTS"
echo "=============================================="

cd src

# Chay thuc nghiem
python LLM_R2_Claude.py << EOF
# Cau hinh duoc doc tu trong code, khong can truyen them
EOF

# Neu muon chay truc tiep (thay doi trong code truoc):
# python LLM_R2_Claude.py

echo ""
echo "=== Thuc nghiem hoan tat ==="
echo "Ket qua luu tai: ../results/"
