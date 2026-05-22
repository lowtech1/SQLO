# ============================================================
# GHI CHÚ SO SANH: LLM_R2.py (GPT-3.5) vs LLM_R2_Claude.py (Claude Opus 4.6)
# ============================================================

## 1. CÀI ĐẶT THƯ VIỆN

### Trước (GPT-3.5):
```bash
pip install openai
```

### Sau (Claude Opus 4.6):
```bash
pip install anthropic
```

---

## 2. IMPORT VÀ KHỞI TẠO CLIENT

### Trước:
```python
from openai import OpenAI

client = OpenAI(
    api_key="your_openai_api_key"
)
```

### Sau:
```python
from anthropic import Anthropic

client = Anthropic(
    api_key=os.environ.get("ANTHROPIC_API_KEY", "your_anthropic_api_key")
)
```

### Biến môi trường cần đặt:
```bash
# Linux/Mac:
export ANTHROPIC_API_KEY="sk-ant-..."

# Windows:
set ANTHROPIC_API_KEY=sk-ant-...
```

---

## 3. HÀM GỌI API

### Trước - query_turbo_model():
```python
def query_turbo_model(prompt):
    chat_completion = client.chat.completions.create(
        messages=prompt,       # List[dict] - OpenAI format
        model="gpt-3.5-turbo",
        temperature=0,
    )
    return chat_completion.choices[0].message.content
```

### Sau - query_claude_model():
```python
def query_claude_model(messages, model="claude-opus-4-6", temperature=0, max_tokens=1024):
    response = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        system=messages[0]['content'] if messages and messages[0]['role'] == 'system' else None,
        messages=[
            {'role': msg['role'], 'content': msg['content']}
            for msg in messages[1:]  # Bo qua system
        ]
    )
    return response.content[0].text
```

### Sự khác biệt cốt lõi:

| Khía cạnh | GPT-3.5 (OpenAI) | Claude Opus 4.6 (Anthropic) |
|---|---|---|
| **API endpoint** | `chat.completions.create()` | `messages.create()` |
| **System message** | Trong danh sách `messages` | Trường `system` riêng |
| **Model identifier** | `"gpt-3.5-turbo"` | `"claude-opus-4-6"` |
| **Temperature=0** | Hỗ trợ đầy đủ | Hỗ trợ đầy đủ |
| **Response format** | `choices[0].message.content` | `content[0].text` (TextBlock) |
| **max_tokens** | Mặc định không giới hạn | **BẮT BUỘC** truyền |
| **Context window** | ~16K tokens | 200K tokens |

---

## 4. PROMPT GENERATION

### Trước - generate_turbo_prompt_light():
```python
def generate_turbo_prompt_light(schema, query, logical_plan, promotions):
    p = [{'role': "system", 'content': 'You are an online SQL rewrite agent...'}]
    for promo in promotions:
        p = p + [{
            'role': "user", 'content': "Query: " + str(query_p),
        }, {
            'role': "assistant", 'content': 'Rules selected: ' + str(rules_list_p),
        }]
    p.append({'role': "user", 'content': "Query: " + str(query)})
    return p
```

### Sau - generate_claude_prompt_light():
```python
def generate_claude_prompt_light(schema, query, logical_plan, promotions):
    system_prompt = 'You are an online SQL rewrite agent...'
    messages = []

    # Demonstration examples (few-shot)
    for promo in promotions:
        messages.append({'role': 'user', 'content': "Query: " + str(query_p)})
        messages.append({'role': 'assistant', 'content': 'Rules selected: ' + str(rules_list_p)})

    # Final user query
    messages.append({'role': 'user', 'content': "Query: " + str(query)})

    # Tra ve voi system prompt rieng
    return [{'role': 'system', 'content': system_prompt}] + messages
```

**Điểm khác biệt:**
- System prompt được tách riêng thành trường `system` (Anthropic convention)
- Các message giữ nguyên cấu trúc `{role, content}`
- Logic xử lý trong `query_claude_model()` sẽ tách system ra khỏi messages list

---

## 5. HÀM CHÍNH

### Trước:
```python
# goi GPT
gpt_output_s = query_gpt_attempts(sim_prompt, trys)
```

### Sau:
```python
# goi Claude
claude_output_s = query_claude_attempts(sim_prompt, trys)
```

### Tất cả các hàm khác: GIỮ NGUYÊN 100%
- `filter_gpt_output()` — không thay đổi
- `call_rewriter()` — không thay đổi
- `get_promo_meta()` — không thay đổi
- `get_k_promos()` — không thay đổi
- `get_pool()` — không thay đổi
- `LLM_R2()` → `LLM_R2_Claude()` — chỉ đổi tên và dùng Claude API

---

## 6. KẾT QUẢ ĐẦU RA

File kết quả được đổi tên để phân biệt:

| GPT-3.5 | Claude Opus 4.6 |
|---|---|
| `gpt_{dataset}_one_promo_{method}_updated.csv` | `gpt_{dataset}_claude_opus_{method}_updated.csv` |
| `time_gpt_{dataset}_one_promo_{method}_cleaned.csv` | `time_gpt_{dataset}_claude_opus_{method}.csv` |

---

## 7. CHẠY THỰC NGHIỆM

### Linux/Mac:
```bash
cd src
export ANTHROPIC_API_KEY="sk-ant-..."
bash run_Claude_Experiment.sh
```

### Windows:
```batch
cd src
set ANTHROPIC_API_KEY=sk-ant-...
run_Claude_Experiment.bat
```

### Hoặc trực tiếp:
```bash
cd src
python LLM_R2_Claude.py
```

---

## 8. LƯU Ý QUAN TRỌNG

1. **`max_tokens=1024`**: BẮT BUỘC cho Anthropic API. Nếu không truyền, API sẽ lỗi.
2. **System prompt**: Đặt trong trường `system` riêng, không nằm trong messages list.
3. **API Key**: Nên dùng biến môi trường `ANTHROPIC_API_KEY` thay vì hardcode.
4. **Model name**:
   - `claude-opus-4-6` — mạnh nhất, tốt cho suy luận phức tạp về SQL rewrite
   - `claude-sonnet-4-6` — cân bằng giữa chất lượng và tốc độ
   - `claude-haiku-4-5-20251001` — nhanh nhất, thử nghiệm nhanh
5. **Cost**: Claude Opus 4.6 có chi phí API cao hơn GPT-3.5. So sánh:
   - GPT-3.5-turbo: ~$0.5-2/1M tokens
   - Claude Opus 4.6: ~$15/1M tokens input, ~$75/1M tokens output
6. **Context window**: Claude Opus 4.6 có 200K tokens vs GPT-3.5 ~16K — cho phép đưa nhiều demonstration và schema hơn vào prompt.

---

## 9. BẢNG SO SÁNH ĐẦY ĐỦ

| Khía cạnh | GPT-3.5 (gốc) | Claude Opus 4.6 (mới) |
|---|---|---|
| Thư viện | `openai` | `anthropic` |
| Client class | `OpenAI()` | `Anthropic()` |
| API method | `chat.completions.create()` | `messages.create()` |
| System prompt | Trong `messages[0]` | Trường `system` riêng |
| Model | `gpt-3.5-turbo` | `claude-opus-4-6` |
| Max context | ~16K tokens | 200K tokens |
| max_tokens | Optional | **Required** |
| Response field | `choices[0].message.content` | `content[0].text` |
| Hàm gọi chính | `query_turbo_model()` | `query_claude_model()` |
| Hàm retry | `query_gpt_attempts()` | `query_claude_attempts()` |
| Prompt generation | `generate_turbo_prompt_light()` | `generate_claude_prompt_light()` |
| Hàm main | `LLM_R2()` | `LLM_R2_Claude()` |
| Chi phí API | Thấp | Cao (~30x) |
| Chất lượng rewrite | Tốt | **Tốt hơn** (theo benchmark Anthropic) |
