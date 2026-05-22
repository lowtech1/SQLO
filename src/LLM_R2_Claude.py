# @TIME : 16/5/26
# @AUTHOR : Claude Opus 4.6
# ============================================================
# LLM_R2_Claude.py
# Chuyen doi tu GPT-3.5-turbo sang Claude Opus 4.6
# Thay doi chinh:
#   - openai.OpenAI -> anthropic.Anthropic
#   - query_turbo_model() -> query_claude_model()
#   - Prompt format tu OpenAI chat sang Anthropic messages
# ============================================================

import os
import json
import random
import pandas as pd
import re
import zss
import ast
import time
from rewriter import *
from get_query_meta import *
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
import sys

# ====== SETUP .env (CACH 2) ======
# Doc API key tu file .env thay vi hardcode
from dotenv import load_dotenv
load_dotenv()  # Tu dong doc file .env trong cung thu muc

# Set PATHs
PATH_TO_SENTEVAL = './SentEval'
PATH_TO_DATA = './SentEval/data'
sys.path.insert(0, PATH_TO_SENTEVAL)
import senteval
from senteval.utils import cosine
from encoder import *
from models import QueryformerForCL

# ====== THAY DOI 1: Anthropic thay vi OpenAI ======
from anthropic import Anthropic

# Cau hinh API key tu .env
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "your_anthropic_api_key")

client = Anthropic(
    api_key=ANTHROPIC_API_KEY
)

os.environ["TOKENIZERS_PARALLELISM"] = "false"
pre_lang_model = SentenceTransformer('all-MiniLM-L6-v2')

model = QueryformerForCL()
model_name = 'tpch'
checkpoint = torch.load('simcse_models/' + model_name + '/pytorch_model.bin', map_location=torch.device('cpu'))
model.load_state_dict(checkpoint, strict=False)
model.eval()
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = model.to(device)


def batcher(sentences, db_ids):
    sent_features = prepare_enc_data(sentences, pre_lang_model, db_ids)
    batch = eval_collator(sent_features)
    with torch.no_grad():
        outputs = model(**batch, eval=True)
        pooler_output = outputs
    return pooler_output.cpu()


compute_similarity = lambda s1, s2: np.nan_to_num(cosine(np.nan_to_num(s1), np.nan_to_num(s2)))


def query_claude_attempts(prompt, trys):
    """
    Goi Claude Opus 4.6 voi retry logic (tuong tu nhu query_gpt_attempts cu).
    prompt: Danh sach messages theo dinh dang Anthropic messages API.
    """
    try:
        output = query_claude_model(prompt)
    except Exception as e:
        print(f"[Claude API Error] Attempt {trys}: {e}")
        trys += 1
        if trys <= 3:
            output = query_claude_attempts(prompt, trys)
        else:
            output = 'NA'
    return output


def query_claude_model(messages, model="claude-opus-4-6", temperature=0, max_tokens=1024):
    """
    Goi Anthropic Claude Opus 4.6 API.
    TUONG TUONG: query_turbo_model() trong LLM_R2.py goc.

    Su khac biet voi GPT-3.5:
    - Anthropic su dung messages API ( khac voi OpenAI chat completions)
    - System message duoc truyen rieng trong truong 'system'
    - Response la AnthropicMessage(content=[TextBlock(text=...)])

    Parameters:
        messages: Danh sach messages [{'role': '...', 'content': '...'}]
                 Giong cau truc GPT nhung phu hop voi Anthropic API
        model: Model cua Anthropic (mac dinh: claude-opus-4-6)
        temperature: Nhiet do sinh (0 = deterministic)
        max_tokens: So token toi da dau ra

    Returns:
        Noi dung text tu response cua Claude.
    """
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=messages[0]['content'] if messages and messages[0]['role'] == 'system' else None,
        messages=[
            {
                'role': msg['role'],
                'content': msg['content']
            }
            for msg in messages[1:]  # Bo qua system message vi da truyen o tren
        ]
    )

    # Anthropic tra ve response.content la danh sach TextBlock
    # Lay text tu TextBlock dau tien
    if response.content and len(response.content) > 0:
        return response.content[0].text
    return 'NA'


# ============================================================
# CAC LUAT REWRITE (Giu nguyen tu ban goc)
# ============================================================
agge_rewrite_rules = '["AGGREGATE_EXPAND_DISTINCT_AGGREGATES": "Rule that expands distinct aggregates (such as COUNT(DISTINCT x)) from a Aggregate"], ' \
                     '["AGGREGATE_EXPAND_DISTINCT_AGGREGATES_TO_JOIN": "As AGGREGATE_EXPAND_DISTINCT_AGGREGATES but generates a Join"], ' \
                     '["AGGREGATE_JOIN_TRANSPOSE_EXTENDED": "As AGGREGATE_JOIN_TRANSPOSE, but extended to push down aggregate functions"], ' \
                     '["AGGREGATE_PROJECT_MERGE": "Rule that recognizes an Aggregate on top of a Project and if possible aggregates through the Project or removes the Project"], ' \
                     '["AGGREGATE_ANY_PULL_UP_CONSTANTS": "More general form of AGGREGATE_PROJECT_PULL_UP_CONSTANTS that matches any relational expression"], ' \
                     '["AGGREGATE_UNION_AGGREGATE": "Rule that matches an Aggregate whose input is a Union one of whose inputs is an Aggregate"], ' \
                     '["AGGREGATE_UNION_TRANSPOSE": "Rule that pushes an Aggregate past a non-distinct Union"], ' \
                     '["AGGREGATE_VALUES": "Rule that applies an Aggregate to a Values (currently just an empty Values)"], ' \
                     '["AGGREGATE_REMOVE": "Rule that removes an Aggregate if it computes no aggregate functions (that is, it is implementing SELECT DISTINCT), or all the aggregate functions are splittable, and the underlying relational expression is already distinct"], '

filt_rewrite_rules = '["FILTER_AGGREGATE_TRANSPOSE": "Rule that pushes a Filter past an Aggregate"], ' \
                     '["FILTER_CORRELATE": "Rule that pushes a Filter above a Correlate into the inputs of the Correlate"], ' \
                     '["FILTER_INTO_JOIN": "Rule that tries to push filter expressions into a join condition and into the inputs of the join"], ' \
                     '["JOIN_CONDITION_PUSH": "Rule that pushes predicates in a Join into the inputs to the join"], ' \
                     '["FILTER_MERGE": "Rule that combines two LogicalFilters"], ' \
                     '["FILTER_MULTI_JOIN_MERGE": "Rule that merges a Filter into a MultiJoin, creating a richer MultiJoin"], ' \
                     '["FILTER_PROJECT_TRANSPOSE": "The default instance of FilterProjectTransposeRule"], ' \
                     '["FILTER_SET_OP_TRANSPOSE": "Rule that pushes a Filter past a SetOp"], ' \
                     '["FILTER_TABLE_FUNCTION_TRANSPOSE": "Rule that pushes a LogicalFilter past a LogicalTableFunctionScan"], ' \
                     '["FILTER_SCAN": "Rule that matches a Filter on a TableScan"], ' \
                     '["FILTER_REDUCE_EXPRESSIONS": "Rule that reduces constants inside a LogicalFilter"], ' \
                     '["PROJECT_REDUCE_EXPRESSIONS": "Rule that reduces constants inside a LogicalProject"], '

join_rewrite_rules = '["JOIN_EXTRACT_FILTER": "Rule to convert an inner join to a filter on top of a cartesian inner join"], ' \
                     '["JOIN_PROJECT_BOTH_TRANSPOSE": "Rule that matches a LogicalJoin whose inputs are LogicalProjects, and pulls the project expressions up"], ' \
                     '["JOIN_PROJECT_LEFT_TRANSPOSE": "As JOIN_PROJECT_BOTH_TRANSPOSE but only the left input is a LogicalProject"], ' \
                     '["JOIN_PROJECT_RIGHT_TRANSPOSE": "As JOIN_PROJECT_BOTH_TRANSPOSE but only the right input is a LogicalProject"], ' \
                     '["JOIN_LEFT_UNION_TRANSPOSE": "Rule that pushes a Join past a non-distinct Union as its left input"], ' \
                     '["JOIN_RIGHT_UNION_TRANSPOSE": "Rule that pushes a Join past a non-distinct Union as its right input"], ' \
                     '["SEMI_JOIN_REMOVE": "Rule that removes a semi-join from a join tree"], ' \
                     '["JOIN_REDUCE_EXPRESSIONS": "Rule that reduces constants inside a Join"], '

sort_rewrite_rules = '["SORT_JOIN_TRANSPOSE": "Rule that pushes a Sort past a Join"], ' \
                     '["SORT_PROJECT_TRANSPOSE": "Rule that pushes a Sort past a Project"], ' \
                     '["SORT_UNION_TRANSPOSE": "Rule that pushes a Sort past a Union"], ' \
                     '["SORT_REMOVE_CONSTANT_KEYS": "Rule that removes keys from a Sort if those keys are known to be constant, or removes the entire Sort if all keys are constant"], ' \
                     '["SORT_REMOVE": "Rule that removes a Sort if its input is already sorted"], '

union_rewrite_rules = '["UNION_MERGE": "Rule that flattens a Union on a Union into a single Union"], ' \
                      '["UNION_REMOVE": "Rule that removes a Union if it has only one input"], ' \
                      '["UNION_TO_DISTINCT": "Rule that translates a distinct Union (all = false) into an Aggregate on top of a non-distinct Union (all = true)"], ' \
                      '["UNION_PULL_UP_CONSTANTS": "Rule that pulls up constants through a Union operator"], '


# ============================================================
# PROMPT GENERATION
# ============================================================
def generate_claude_prompt_light(schema, query, logical_plan, promotions):
    """
    Tao prompt cho Claude Opus 4.6.
    Dinh dang: Danh sach messages theo Anthropic API.

    Su khac biet voi generate_turbo_prompt_light():
    - Khong su dung 'system' role trong danh sach messages
      vi Anthropic xu ly system message rieng biet
    - Noi dung prompt giong GPT nhung format cho Anthropic
    """
    system_prompt = (
        'You are an online SQL rewrite agent. You will be given a SQL query.'
        ' You are required to propose rewriting rules to'
        ' rewrite the query to improve the efficiency of running this query, using the '
        'given rewriting rules below. The rules are provided in form of ["rule name": '
        '"rule description"] and you should answer with a list of rewriting rule names, '
        'which if applied in sequence, will best rewrite the input SQL query into a new '
        'query, which is the most efficient. '
        'Return "Empty List" if from the previous chat and input query, no rule should be used. '
        'The rewriting rules you can adopt are defined as follows: ' +
        agge_rewrite_rules + filt_rewrite_rules + join_rewrite_rules +
        union_rewrite_rules + sort_rewrite_rules +
        'You should return only a list of rewriting rule names provided above, in the '
        'form of "Rules selected: [rule names]".'
    )

    messages = []

    # Demonstration examples (few-shot learning)
    for promo in promotions:
        schema_p, query_p, logical_plan_p, rules_list_p = promo
        print('demo sql: ', str(query_p))
        print('demo rules: Rules selected: ', str(rules_list_p))

        # User message (query tu demo)
        messages.append({
            'role': 'user',
            'content': "Query: " + str(query_p),
        })
        # Assistant message (tra loi dung tu demo)
        messages.append({
            'role': 'assistant',
            'content': 'Rules selected: ' + str(rules_list_p),
        })

    # User message cuoi cung (query can rewrite)
    messages.append({
        'role': 'user',
        'content': "Query: " + str(query),
    })

    # Tra ve danh sach messages + system prompt
    # Dinh dang nay phu hop voi query_claude_model()
    return [{'role': 'system', 'content': system_prompt}] + messages


def generate_llama2_prompt_light(query, promotions):
    """
    Prompt cho Llama2 (chua su dung, giu nguyen tu ban goc).
    """
    p = 'You are an online SQL rewrite agent. You will be given a SQL query. You are required to propose rewriting ' \
        'rules to rewrite the query to improve the efficiency of running this query, using the given rewriting rules ' \
        'below. The rules are provided in form of ["rule name": "rule description"] and you should answer with a ' \
        'list of rewriting rule names, which if applied in sequence, will best rewrite the input SQL query into a ' \
        'new query, which is the most efficient. Return "Empty List" if from the previous chat and input query, no ' \
        'rule should be used. The rewriting rules you can adopt are defined as follows: ' \
        + agge_rewrite_rules + filt_rewrite_rules + join_rewrite_rules + union_rewrite_rules + sort_rewrite_rules + \
        'You should return only a list of rewriting rule names provided above, in the form of ' \
        '"Rules selected: [rule names]".'

    for promo in promotions:
        schema_p, query_p, logical_plan_p, rules_list_p = promo
        print('demo rules: Rules selected: ', str(rules_list_p))
        promo_p = " Query: " + str(query_p) + '. Rules selected: ' + str(rules_list_p) + "."
        p = p + promo_p
    p += " Query: " + str(query) + "."
    return p


# ============================================================
# OUTPUT FILTERING (Giu nguyen tu ban goc)
# ============================================================
def filter_gpt_output(gpt_output):
    """
    Loc ra cac rule hop le tu output cua LLM.
    Giu nguyen logic tu ban goc LLM_R2.py.
    """
    rule_list = ['AGGREGATE_EXPAND_DISTINCT_AGGREGATES', 'AGGREGATE_EXPAND_DISTINCT_AGGREGATES_TO_JOIN',
                 'AGGREGATE_JOIN_TRANSPOSE_EXTENDED', 'AGGREGATE_PROJECT_MERGE', 'AGGREGATE_ANY_PULL_UP_CONSTANTS',
                 'AGGREGATE_UNION_AGGREGATE', 'AGGREGATE_UNION_TRANSPOSE', 'AGGREGATE_VALUES', 'AGGREGATE_INSTANCE',
                 'AGGREGATE_REMOVE', 'FILTER_AGGREGATE_TRANSPOSE', 'FILTER_CORRELATE', 'FILTER_INTO_JOIN',
                 'JOIN_CONDITION_PUSH', 'FILTER_MERGE', 'FILTER_MULTI_JOIN_MERGE', 'FILTER_PROJECT_TRANSPOSE',
                 'FILTER_SET_OP_TRANSPOSE', 'FILTER_TABLE_FUNCTION_TRANSPOSE', 'FILTER_SCAN',
                 'FILTER_REDUCE_EXPRESSIONS', 'PROJECT_REDUCE_EXPRESSIONS', 'FILTER_INSTANCE', 'JOIN_EXTRACT_FILTER',
                 'JOIN_PROJECT_BOTH_TRANSPOSE', 'JOIN_PROJECT_LEFT_TRANSPOSE', 'JOIN_PROJECT_RIGHT_TRANSPOSE',
                 'JOIN_LEFT_UNION_TRANSPOSE', 'JOIN_RIGHT_UNION_TRANSPOSE', 'SEMI_JOIN_REMOVE',
                 'JOIN_REDUCE_EXPRESSIONS', 'JOIN_LEFT_INSTANCE', 'JOIN_RIGHT_INSTANCE', 'PROJECT_CALC_MERGE',
                 'PROJECT_CORRELATE_TRANSPOSE', 'PROJECT_MERGE', 'PROJECT_MULTI_JOIN_MERGE', 'PROJECT_REMOVE',
                 'PROJECT_TO_CALC', 'PROJECT_SUB_QUERY_TO_CORRELATE', 'PROJECT_REDUCE_EXPRESSIONS',
                 'PROJECT_INSTANCE', 'CALC_MERGE', 'CALC_REMOVE', 'SORT_JOIN_TRANSPOSE', 'SORT_PROJECT_TRANSPOSE',
                 'SORT_UNION_TRANSPOSE', 'SORT_REMOVE_CONSTANT_KEYS', 'SORT_REMOVE', 'SORT_INSTANCE',
                 'SORT_FETCH_ZERO_INSTANCE', 'UNION_MERGE', 'UNION_REMOVE', 'UNION_TO_DISTINCT',
                 'UNION_PULL_UP_CONSTANT', 'UNION_INSTANCE', 'INTERSECT_INSTANCE', 'MINUS_INSTANCE']
    if gpt_output == 'NA':
        return []
    out_rules = gpt_output.split('[')[-1].split(']')[0]
    out_rules = out_rules.replace('/', '').replace('"', '').replace("'", "")
    out_rules = [x.replace(' ', '').replace('\n', '').strip() for x in out_rules.split(',')]
    print('out_rules: ', out_rules)
    execute_rules = []
    for r in out_rules:
        if r in rule_list:
            execute_rules.append(r)
    return execute_rules


# ============================================================
# CAC HAM HO TRO (Giu nguyen tu ban goc)
# ============================================================
def fill_quotes_list(original_sql):
    fill_list = []
    count = 0
    for i in range(len(original_sql)):
        if i != 0 and i != len(original_sql) - 1:
            char = original_sql[i]
            if char == '"':
                count += 1
                if count % 2 == 1:
                    start_ind = i
                else:
                    end_ind = i
                    seg = original_sql[start_ind: end_ind].replace('"', '')
                    fill_list.append(seg)
    return fill_list


def get_promo_meta(db_id, query, rule_path):
    with open('../data/data_llmr2/schemas/' + db_id + '.json') as f_sch:
        data = f_sch.read()
        schema = json.loads(data)
    filtered_schema = []
    q_names = query.split()
    for tab in schema:
        if tab['table'] in q_names or (',' + tab['table']) in q_names or (tab['table'] + ',') in q_names:
            new_tab = {'table': tab['table'], 'rows': tab['rows'], 'columns': []}
            for col in tab['columns']:
                if col['name'] in q_names or (',' + col['name']) in q_names or (col['name'] + ',') in q_names:
                    new_tab['columns'].append(col)
            filtered_schema.append(new_tab)
    schema = filtered_schema
    query_1 = query.replace('`', '"')
    query_1 = query_1.replace('TEXT', 'CHAR')
    pattern_iif = r'IIF\((.*?),\s+(.*?),\s+(.*?)\)'
    matches_iif = re.findall(pattern_iif, query_1)
    for i in matches_iif:
        query_1 = query_1.replace('IIF(' + i[0] + ', ' + i[1] + ', ' + i[2] + ')',
                                  'CASE WHEN ' + i[0] + ' THEN ' + i[1] + ' ELSE ' + i[2] + ' END')
    pattern_lim = r'LIMIT\s+(.*?),\s+(.*?)\s+.*'
    matches_lim = re.findall(pattern_lim, query_1)
    for i in matches_lim:
        query_1 = query_1.replace('LIMIT ' + i[0] + ', ' + i[1],
                                  'OFFSET ' + i[0] + ' ROWS FETCH NEXT ' + i[1] + ' ROWS ONLY')
    pattern_len = r'LENGTH\((.*?)\)'
    matches_len = re.findall(pattern_len, query_1)
    for i in matches_len:
        query_1 = query_1.replace('LENGTH(' + i + ')', 'CHAR_LENGTH(CAST(' + i + ' AS VARCHAR))')
    logical_plan = get_logical_plan(db_id, query_1)
    return schema, query, logical_plan, rule_path


def edit_queries(textsql):
    rep = {" year ": " calcite_year ", " date ": " calcite_date ", " rank ": "calcite_rank ", " position ": " calcite_position ",
           " YEAR ": " calcite_YEAR ", " DATE ": " calcite_DATE ", " RANK ": "calcite_RANK ", " POSITION ": " calcite_POSITION ",
           " Year ": " calcite_Year ", " Date ": " calcite_Date ", " Rank ": "calcite_Rank ", " Position ": " calcite_Position ",
           " TIME ": " calcite_TIME ", " Time ": " calcite_Time ", " time ": "calcite_time ",
           " KEY ": " calcite_KEY ", " Key ": " calcite_Key ", " key ": " calcite_key ",
           " DAY ": " calcite_DAY ", " Day ": " calcite_Day ", " day ": " calcite_day ",
           " PER ": " calcite_PER ", " Per ": " calcite_Per ", " per ": " calcite_per ",
           " RESULT ": " calcite_RESULT ", " Result ": " calcite_Result ", " result ": " calcite_result ",
           " MONTH ": " calcite_MONTH ", " Month ": " calcite_Month ", " month ": " calcite_month ",
           " METHOD ": " calcite_METHOD ", " Method ": " calcite_Method ", " method ": " calcite_method ",
           " RATING ": " calcite_RATING ", " Rating ": " calcite_Rating ", " rating ": " calcite_rating ",
           " RANGE ": " calcite_RANGE ", " Range ": " calcite_Range ", " range ": " calcite_range ",
           " CHARACTER ": " calcite_CHARACTER ", " Character ": " calcite_Character ",
           " count ": " calcite_count "}
    rep = dict((re.escape(k), v) for k, v in rep.items())
    pattern = re.compile("|".join(rep.keys()))
    textsql = pattern.sub(lambda m: rep[re.escape(m.group(0))], textsql)
    return textsql


def get_promo_pools(promo_df):
    pools = {}
    db_id_pool_pos = []
    query_pool_pos = []
    rule_path_pool_pos = []
    db_id_pool_neg = []
    query_pool_neg = []
    rule_path_pool_neg = []
    for index, row in promo_df.iterrows():
        db_id = row['db_id']
        query = str(row['original_sql'])
        query = edit_queries(str(row['original_sql']))
        rule_path = row['activated_rules_gpt']
        if row['latency_org'] != 'NA' and row['latency_gpt'] != 'NA':
            prop = float(row['latency_gpt']) / float(row['latency_org'])
            if prop < 1 and rule_path != '[]':
                db_id_pool_pos.append(db_id)
                query_pool_pos.append(query)
                rule_path_pool_pos.append(rule_path)
            elif prop > 1 and rule_path != '[]':
                db_id_pool_neg.append(db_id)
                query_pool_neg.append(query)
                rule_path_pool_neg.append(rule_path)
    pools['pos'] = (db_id_pool_pos, query_pool_pos, rule_path_pool_pos)
    pools['neg'] = (db_id_pool_neg, query_pool_neg, rule_path_pool_neg)
    return pools


def simple_distance(A, B):
    if A.label != B.label:
        return 1
    return 0


def list_to_zss_tree(lst):
    if not lst:
        return None
    if isinstance(lst, list):
        root = zss.Node(lst[0])
        if len(lst) > 1 and lst[1]:
            root.addkid(list_to_zss_tree(lst[1]))
        if len(lst) > 2 and lst[2]:
            root.addkid(list_to_zss_tree(lst[2]))
    else:
        root = zss.Node(lst)
    return root


def get_top_k_smallest_indices(in_list, k):
    sorted_list = sorted(in_list)
    out_inds = []
    for i in range(len(sorted_list)):
        small_val = sorted_list[i]
        if i <= k - 1:
            inds = [ind for ind in range(len(sorted_list)) if in_list[ind] == small_val and ind not in out_inds]
            selected_ind = random.choices(inds, k=1)[0]
            out_inds.append(selected_ind)
        else:
            break
    return out_inds


def get_k_promos(k, pos_pool, neg_pool, db_id, query, logical_plan, method='plan', same=False):
    db_id_pool_pos, query_pool_pos, rule_path_pool_pos, logical_plan_pos, embeddings_pos = pos_pool
    db_id_pool_neg, query_pool_neg, rule_path_pool_neg, logical_plan_neg, embeddings_neg = neg_pool
    db_id_pool_all = db_id_pool_pos + db_id_pool_neg
    query_pool_all = query_pool_pos + query_pool_neg
    rule_path_pool_all = rule_path_pool_pos + rule_path_pool_neg
    logical_plan_all = logical_plan_pos + logical_plan_neg
    if method == 'sentbert':
        embeddings_all = np.concatenate((embeddings_pos, embeddings_neg), axis=0)
    elif method == 'queryCL':
        enc2 = torch.cat((embeddings_pos, embeddings_neg))
    if query in query_pool_all and same:
        assert k == 1
        same_ind = query_pool_all.index(query)
        same_promos = [get_promo_meta(db_id_pool_all[same_ind], query_pool_all[same_ind], rule_path_pool_all[same_ind])]
        return same_promos
    if method == 'random':
        all_indices = np.arange(len(db_id_pool_all))
        rdm_inds = random.choices(all_indices, k=k)
        random_promos = []
        for i in rdm_inds:
            random_promos.append(get_promo_meta(db_id_pool_all[i], query_pool_all[i], rule_path_pool_all[i]))
        return random_promos
    elif method == 'plan':
        if not logical_plan:
            print('invalid plan, use random')
            all_indices = np.arange(len(db_id_pool_all))
            rdm_inds = random.choices(all_indices, k=k)
            random_promos = []
            for i in rdm_inds:
                random_promos.append(get_promo_meta(db_id_pool_all[i], query_pool_all[i], rule_path_pool_all[i]))
            return random_promos
        else:
            tree_plan_test = list_to_zss_tree(logical_plan)
            tree_plans_pool = [list_to_zss_tree(ast.literal_eval(logical_plan_all[i])) if query != query_pool_all[i]
                               else None for i in range(len(logical_plan_all))]
            tree_edit_dists = [zss.simple_distance(tree_plan_test, tree) if tree else float('inf') for tree in
                               tree_plans_pool]
            sim_indices = get_top_k_smallest_indices(tree_edit_dists, k)
            print(sim_indices)
            plan_promos = []
            for i in sim_indices:
                plan_promos.append(get_promo_meta(db_id_pool_all[i], query_pool_all[i], rule_path_pool_all[i]))
            return plan_promos
    elif method == 'sentbert':
        sent_promos = []
        in_sent = [query]
        in_ind = -1
        if query in query_pool_all:
            in_ind = query_pool_all.index(query)
        in_embedding = pre_lang_model.encode(in_sent)
        sim_scores = []
        for i in range(len(embeddings_all)):
            if i != in_ind:
                sim_score = cosine_similarity(in_embedding, [embeddings_all[i]])[0][0]
                sim_scores.append(sim_score)
        sorted_scores = sorted(sim_scores, reverse=True)
        promo_inds = []
        for i in range(k):
            score = sorted_scores[i]
            promo_inds.append(sim_scores.index(score))
        for ind in promo_inds:
            sent_promos.append(get_promo_meta(db_id_pool_all[ind], query_pool_all[ind], rule_path_pool_all[ind]))
        return sent_promos
    elif method == 'queryCL':
        query_pool_all = [x for x in query_pool_all if x != query]
        batch1 = [[query]]
        enc1 = batcher(batch1, [db_id])
        enc1 = enc1.repeat((enc2.shape[0], 1))
        sim_scores = []
        for kk in range(enc2.shape[0]):
            sys_score = compute_similarity(enc1[kk], enc2[kk])
            sim_scores.append(sys_score)
        cl_promos = []
        sorted_scores = sorted(sim_scores, reverse=True)
        promo_inds = []
        for i in range(k):
            score = sorted_scores[i]
            promo_inds.append(sim_scores.index(score))
        for ind in promo_inds:
            cl_promos.append(get_promo_meta(db_id_pool_all[ind], query_pool_all[ind], rule_path_pool_all[ind]))
        return cl_promos


def append_logical_plans(in_csv):
    df_pool = pd.read_csv(in_csv)
    ids = df_pool['db_id'].tolist()
    originals = [edit_queries(x) for x in df_pool['original_sql'].tolist()]
    plans = []
    for i in range(len(ids)):
        plan = get_logical_plan(ids[i], originals[i])
        print(plan)
        plans.append(plan)
    df_pool['original_logical_plan'] = plans
    df_pool = pd.DataFrame(df_pool)
    df_pool.to_csv(in_csv)
    print('logical plan appended')


def get_pool(poll_csv, method):
    pool_df = pd.read_csv(poll_csv)
    sentences = [edit_queries(x) for x in pool_df['original_sql'].tolist()]
    if method == 'sentbert':
        embeddings = pre_lang_model.encode(sentences)
    elif method == 'queryCL':
        batch2 = [[x] for x in pool_df['original_sql'].tolist()]
        embeddings = batcher(batch2, pool_df['db_id'].tolist())
    else:
        embeddings = []
    promo_pool = (pool_df['db_id'].tolist(), pool_df['original_sql'].tolist(),
                  pool_df['activated_rules'].tolist(), pool_df['original_logical_plan'].tolist(), embeddings)
    return promo_pool


# ============================================================
# HAM CHINH: LLM_R2 voi Claude Opus 4.6
# ============================================================
def LLM_R2_Claude(dataset, method, num_promos, max_queries=10, parallel_calls=8):
    """
    Pipeline chinh: su dung Claude Opus 4.6 thay GPT-3.5-turbo.

    Them: parallel_calls de goi nhieu API cung luc (ThreadPoolExecutor).
    max_queries=0 nghia la chay tat ca query.
    """
    demo_time_record = []
    llm_time_record = []
    rewriter_time_record = []
    df_gpt = {}
    db_ids = []
    original_queries = []
    rewritten_queries_s = []
    activated_rules_s = []
    prompt_queries_s = []
    prompt_rules_s = []

    process_time_start = time.time()
    df_test = pd.read_csv('../data/data_llmr2/queries/queries_' + dataset + '_test.csv').fillna('NA')

    # Gioi han so query cho mode test nhanh
    if max_queries > 0:
        df_test = df_test.head(max_queries)
        print(f"[QUICK TEST] Chi chay {max_queries} query dau tien")

    promo_pool_pos = get_pool('../data/data_llmr2/pools/pos_pool_' + dataset + '_updated.csv', method)
    promo_pool_neg = get_pool('../data/data_llmr2/pools/neg_pool_' + dataset + '_updated.csv', method)

    process_time_end = time.time()
    process_time = process_time_end - process_time_start
    print('preprocess time: ', process_time)
    print(f'query pool embeddings collected | parallel_calls={parallel_calls}')
    print(f'Tong so query: {len(df_test)}')

    # ============================
    # GIAI DOAN 1: Tien xu ly tat ca query (Sequential - can precompute)
    # ============================
    print("Giai doan 1: Tien xu ly tat ca query...")
    query_items = []  # list of dicts

    for idx, (index, row) in enumerate(df_test.iterrows()):
        db_id = row['db_id']
        raw_query = row['original_sql']
        query = str(raw_query).replace(';', '') + ';' if pd.notna(raw_query) else 'NA;'

        item = {'db_id': db_id, 'raw_query': query, 'index': index}
        if query == 'NA;':
            item['valid'] = False
            query_items.append(item)
            continue

        item['valid'] = True

        # Schema filtering
        with open('../data/data_llmr2/schemas/' + db_id + '.json') as f_sch:
            schema = json.load(f_sch)
        filtered_schema = []
        q_names = query.split()
        for tab in schema:
            if tab['table'] in q_names or (',' + tab['table']) in q_names or (tab['table'] + ',') in q_names:
                new_tab = {'table': tab['table'], 'rows': tab['rows'], 'columns': []}
                for col in tab['columns']:
                    if col['name'] in q_names or (',' + col['name']) in q_names or (col['name'] + ',') in q_names:
                        new_tab['columns'].append(col)
                filtered_schema.append(new_tab)
        item['schema'] = filtered_schema

        # SQL normalization
        q = query.replace('`', '"').replace('TEXT', 'CHAR')
        item['matches_iif'] = re.findall(r'IIF\((.*?),\s+(.*?),\s+(.*?)\)', q)
        for m in item['matches_iif']:
            q = q.replace('IIF(' + m[0] + ', ' + m[1] + ', ' + m[2] + ')',
                          'CASE WHEN ' + m[0] + ' THEN ' + m[1] + ' ELSE ' + m[2] + ' END')
        item['matches_lim'] = re.findall(r'LIMIT\s+(.*?),\s+(.*?)\s+.*', q)
        for m in item['matches_lim']:
            q = q.replace('LIMIT ' + m[0] + ', ' + m[1],
                          'OFFSET ' + m[0] + ' ROWS FETCH NEXT ' + m[1] + ' ROWS ONLY')
        item['matches_len'] = re.findall(r'LENGTH\((.*?)\)', q)
        for m in item['matches_len']:
            q = q.replace('LENGTH(' + m + ')', 'CHAR_LENGTH(CAST(' + m + ' AS VARCHAR))')
        item['normalized_query'] = q

        # Logical plan
        item['logical_plan'] = get_logical_plan(db_id, edit_queries(q))
        query_items.append(item)

        if (idx + 1) % 50 == 0:
            print(f"  Da tien xu ly {idx + 1}/{len(df_test)} query...")

    # ============================
    # GIAI DOAN 2: Demo selection (Sequential - can parallelize neu can)
    # ============================
    print("Giai doan 2: Demo selection...")
    for item in query_items:
        if not item['valid']:
            item['sim_promos'] = []
            item['demo_time'] = 0
            continue
        t0 = time.time()
        item['sim_promos'] = get_k_promos(
            num_promos, promo_pool_pos, promo_pool_neg,
            item['db_id'], item['normalized_query'], item['logical_plan'], method=method
        )
        item['demo_time'] = time.time() - t0
        demo_time_record.append(item['demo_time'])

    # ============================
    # GIAI DOAN 3: Tao prompts (Sequential)
    # ============================
    print("Giai doan 3: Tao prompts...")
    for item in query_items:
        if not item['valid']:
            item['sim_prompt'] = None
            continue
        item['sim_prompt'] = generate_claude_prompt_light(
            item['schema'], item['normalized_query'], item['logical_plan'], item['sim_promos']
        )
        # Store demo queries/rules for record
        promo_q, promo_r = [], []
        for p in item['sim_promos']:
            _, q0, _, r0 = p
            promo_q.append(q0)
            promo_r.append(r0)
        item['prompt_queries'] = promo_q
        item['prompt_rules'] = promo_r

    # ============================
    # GIAI DOAN 4: Goi LLM API (PARALLEL - ThreadPoolExecutor)
    # ============================
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def call_llm_single(item):
        """Goi LLM cho 1 query - chay trong thread"""
        if not item['valid'] or item['sim_prompt'] is None:
            return item['index'], None, None, None
        llm_t0 = time.time()
        try:
            output = query_claude_model(item['sim_prompt'])
            rules = filter_gpt_output(output)
        except Exception as e:
            print(f"  [LLM Error idx {item['index']}] {e}")
            output = 'NA'
            rules = []
        llm_t = time.time() - llm_t0
        return item['index'], output, rules, llm_t

    print(f"Giai doan 4: Goi LLM API (parallel={parallel_calls})...")
    llm_results = {}
    with ThreadPoolExecutor(max_workers=parallel_calls) as executor:
        futures = {executor.submit(call_llm_single, item): item for item in query_items}
        done = 0
        for future in as_completed(futures):
            idx, output, rules, llm_t = future.result()
            llm_results[idx] = (output, rules, llm_t)
            done += 1
            if done % 20 == 0 or done == len(query_items):
                print(f"  LLM API: {done}/{len(query_items)} hoan tat")

    # ============================
    # GIAI DOAN 5: Rewrite (PARALLEL)
    # ============================
    def call_rewriter_single(item):
        """Goi rewriter cho 1 query - chay trong thread"""
        if not item['valid']:
            return item['index'], 'NA', 0
        _, rules, _ = llm_results.get(item['index'], ('NA', [], 0))
        rw_t0 = time.time()
        rewritten = call_rewriter(item['db_id'], item['normalized_query'], rules)
        rw_t = time.time() - rw_t0
        return item['index'], rewritten, rw_t

    print(f"Giai doan 5: Rewrite (parallel={parallel_calls})...")
    rewrite_results = {}
    with ThreadPoolExecutor(max_workers=parallel_calls) as executor:
        futures = {executor.submit(call_rewriter_single, item): item for item in query_items}
        done = 0
        for future in as_completed(futures):
            idx, rewritten, rw_t = future.result()
            rewrite_results[idx] = (rewritten, rw_t)
            done += 1
            if done % 20 == 0 or done == len(query_items):
                print(f"  Rewriter: {done}/{len(query_items)} hoan tat")

    # ============================
    # GIAI DOAN 6: Gop ket qua & post-process
    # ============================
    print("Giai doan 6: Gop ket qua...")
    for item in query_items:
        db_ids.append(item['db_id'])
        if not item['valid']:
            original_queries.append('NA')
            rewritten_queries_s.append('NA')
            activated_rules_s.append('NA')
            prompt_queries_s.append('NA')
            prompt_rules_s.append('NA')
            continue

        # LLM output
        output, rules, llm_t = llm_results.get(item['index'], ('NA', [], 0))
        llm_time_record.append(llm_t)
        print(f"  [{item['index']}] Claude: {str(output)[:60]}...")
        print(f"  [{item['index']}] Rules: {rules}")

        # Rewrite output
        rewritten, rw_t = rewrite_results.get(item['index'], ('NA', 0))
        rewriter_time_record.append(rw_t)

        # Post-process SQL
        q = item['normalized_query']
        rw = rewritten if rewritten else 'NA'

        q = q.replace('calcite_', '')
        rw = rw.replace('calcite_', '') if rw != 'NA' else 'NA'

        fill_list = fill_quotes_list(q)
        for fi in fill_list:
            if '"' + fi + '"' not in rw:
                rw = rw.replace(fi, '"' + fi + '"')

        for m in item['matches_iif']:
            q = q.replace('CASE WHEN ' + m[0] + ' THEN ' + m[1] + ' ELSE ' + m[2] + ' END',
                          'IIF(' + m[0] + ', ' + m[1] + ', ' + m[2] + ')')
            rw = rw.replace('CASE WHEN ' + m[0] + ' THEN ' + m[1] + ' ELSE ' + m[2] + ' END',
                            'IIF(' + m[0] + ', ' + m[1] + ', ' + m[2] + ')') if rw != 'NA' else rw

        for m in item['matches_lim']:
            q = q.replace('OFFSET ' + m[0] + ' ROWS FETCH NEXT ' + m[1] + ' ROWS ONLY',
                          'LIMIT ' + m[0] + ', ' + m[1])
            rw = rw.replace('OFFSET ' + m[0] + ' ROWS FETCH NEXT ' + m[1] + ' ROWS ONLY',
                            'LIMIT ' + m[0] + ', ' + m[1]) if rw != 'NA' else rw

        if rw != 'NA':
            rw = re.sub(r'FETCH NEXT (\d+) ROWS ONLY', r'LIMIT \1', rw)
        for m in item['matches_len']:
            q = q.replace('CHAR_LENGTH(CAST(' + m + ' AS VARCHAR))', 'LENGTH(' + m + ')')
            rw = rw.replace('CHAR_LENGTH(CAST(' + m + ' AS VARCHAR))',
                            'LENGTH(' + m + ')') if rw != 'NA' else rw

        q = q.replace('CHAR', 'TEXT')
        rw = rw.replace('$', '') if rw != 'NA' else rw

        original_queries.append(q)
        rewritten_queries_s.append(rw)
        activated_rules_s.append(rules if rules else [])

        prompt_queries_s.append(item.get('prompt_queries', []))
        prompt_rules_s.append(item.get('prompt_rules', []))

    # Save checkpoint moi 100 query
    CHECKPOINT_INTERVAL = 100
    total = len(db_ids)
    for cp_idx in range(CHECKPOINT_INTERVAL, total, CHECKPOINT_INTERVAL):
        cp_data = {
            'db_id': db_ids[:cp_idx],
            'original_sql': original_queries[:cp_idx],
            'rewritten_sql_gpt': rewritten_queries_s[:cp_idx],
            'activated_rules_gpt': activated_rules_s[:cp_idx],
            'prompt_sql_similar': prompt_queries_s[:cp_idx],
            'prompt_rules_similar': prompt_rules_s[:cp_idx],
        }
        pd.DataFrame(cp_data).to_csv(
            '../results/gpt_' + dataset + '_claude_opus_' + method + '_cp_' + str(cp_idx) + '.csv'
        )
        print(f"  [CHECKPOINT] Da luu {cp_idx}/{total} query")

    df_gpt['db_id'] = db_ids
    df_gpt['original_sql'] = original_queries
    df_gpt['rewritten_sql_gpt'] = rewritten_queries_s
    df_gpt['activated_rules_gpt'] = activated_rules_s
    df_gpt['prompt_sql_similar'] = prompt_queries_s
    df_gpt['prompt_rules_similar'] = prompt_rules_s
    df_gpt = pd.DataFrame(df_gpt)
    df_gpt.to_csv('../results/gpt_' + dataset + '_claude_opus_' + method + '_updated.csv')

    df_t = {'demo_time': demo_time_record, 'llm_time': llm_time_record, 'rewriter_time': rewriter_time_record}
    df_t = pd.DataFrame(df_t)
    df_t.to_csv('../results/time_gpt_' + dataset + '_claude_opus_' + method + '.csv')


# ============================================================
# DIEM CHAY THUC NGHIEM
# ============================================================
# Thay doi tuong minh: chi thay doi model_name = 'claude' thay vi 'tpch'
# va goi ham LLM_R2_Claude thay vi LLM_R2
model_name = 'tpch'
checkpoint = torch.load('simcse_models/' + model_name + '/pytorch_model.bin', map_location=torch.device('cpu'))
model.load_state_dict(checkpoint, strict=False)
model.eval()
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
model = model.to(device)

# === TOI UU TOC DO CHAY ===
# HF_TOKEN: Lay tu .env de tang toc do tai model (tranh warning)
HF_TOKEN = os.environ.get("HF_TOKEN", None)
if HF_TOKEN:
    os.environ["HF_TOKEN"] = HF_TOKEN
    print(f"[INFO] HF_TOKEN da duoc dat - tai model se nhanh hon")

# === CAC LUA CHON TOC DO ===
# MODEL toc nhat: 'claude-haiku-4-5-20251001' (~10x nhanh hon Opus, chat luong thap hon)
# MODEL can bang:  'claude-sonnet-4-6'            (~3x nhanh hon Opus, chat luong tot)
# MODEL tot nhat:  'claude-opus-4-6'              (mac dinh, chat luong cao nhat)
LLM_MODEL = 'claude-opus-4-6'   # doi thanh 'claude-sonnet-4-6' hoac 'claude-haiku-4-5-20251001' de nhanh hon

# Cau hinh thuc nghiem
method = 'sentbert'           # queryCL | sentbert | plan | random
dataset = 'dsb'              # dsb | tpch | job_syn
num_promos = 1               # So luong demonstration
max_queries = 10             # = 0: chay tat ca | = 5: chi test nhanh 5 query dau
parallel_calls = 3            # So API calls cung luc (8 la tot, 16+ neu can)

# Doi model trong API call
query_claude_model.__defaults__ = (LLM_MODEL, 0, 1024)

print("=" * 60)
print("LLM-R2 voi Claude Opus 4.6")
print(f"Dataset: {dataset}")
print(f"Demonstration method: {method}")
print(f"Number of prompts: {num_promos}")
print(f"Max queries: {'tat ca' if max_queries == 0 else max_queries}")
print(f"Parallel calls: {parallel_calls}")
print(f"LLM Model: {LLM_MODEL}")
print("=" * 60)

LLM_R2_Claude(dataset, method, num_promos, max_queries=max_queries, parallel_calls=parallel_calls)
