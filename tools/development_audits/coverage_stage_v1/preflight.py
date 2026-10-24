"""Pure context-limit diagnostics; tokenizer loading belongs to the notebook."""

def context_report(prompt_token_counts, expected_rows, max_model_len=8192, completion_cap=1024):
    if not prompt_token_counts or len(prompt_token_counts) != expected_rows:
        raise ValueError('Prompt-token coverage differs')
    if type(max_model_len) is not int or type(completion_cap) is not int or max_model_len <= 0 or completion_cap <= 0:
        raise ValueError('Invalid context settings')
    if any(type(n) is not int or n < 1 for n in prompt_token_counts):
        raise ValueError('Invalid rendered token count')
    over = [i for i,n in enumerate(prompt_token_counts) if n + completion_cap > max_model_len]
    return {'rows': expected_rows, 'prompt_tokens_total': sum(prompt_token_counts),
            'prompt_tokens_max': max(prompt_token_counts), 'completion_cap': completion_cap,
            'max_model_len': max_model_len, 'over_limit_request_indices': over,
            'all_fit': not over, 'prompts_truncated': False, 'requests_dropped': 0,
            'limit': 'Pinned-tokenizer rendering preflight; server validation remains authoritative.'}
