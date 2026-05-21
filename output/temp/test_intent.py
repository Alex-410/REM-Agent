import requests, json, sys

url = 'http://127.0.0.1:8002/api/intent'
data = {'message': '给rem发送打包好的html代码', 'conversation_id': 'test-session-3'}

resp = requests.post(url, json=data, stream=True, timeout=120)
print(f'Status: {resp.status_code}')

for line in resp.iter_lines():
    if not line:
        continue
    decoded = line.decode('utf-8').replace('data: ', '')
    try:
        event = json.loads(decoded)
    except json.JSONDecodeError:
        print(f'[RAW] {decoded[:200]}')
        continue

    etype = event.get('type', '')
    if etype == 'memory_hit':
        print(f'[记忆命中] input="{event.get("user_input","")}" confidence={event.get("confidence","")}')
    elif etype == 'learning':
        print(f'[学习模式] 没做过，开始学习...')
    elif etype == 'context':
        print(f'[桌面环境] (已收集)')
    elif etype == 'plan_generated':
        plan = event.get('plan', [])
        print(f'[方案生成] {len(plan)} 步')
        for p in plan:
            print(f'    {p["step"]}. {p["action"]}: {p.get("description","")}')
    elif etype == 'step':
        print(f'[执行] {event["step"]}/{event["total"]}: {event["action"]} - {event.get("description","")}')
    elif etype == 'step_result':
        r = event.get('result', {})
        if 'error' in r:
            print(f'[结果] step{event["step"]} ERR: {str(r["error"])[:200]}')
        else:
            print(f'[结果] step{event["step"]} OK: {str(r)[:200]}')
    elif etype == 'step_failed':
        print(f'[失败] step{event["step"]}: {event.get("error","")[:200]}')
    elif etype == 'step_retry':
        print(f'[重试] step{event["step"]} attempt{event["attempt"]}...')
    elif etype == 'auto_fix':
        print(f'[自动修复] {event.get("fix","")} -> {"OK" if event.get("success") else "FAIL"}')
    elif etype == 'memory_saved':
        print(f'[记忆保存] {event.get("result","")}')
    elif etype == 'steps_done':
        print(f'[完成] 共{event["total"]}步')
    elif etype == 'error':
        print(f'[错误] {event.get("content","")[:300]}')
    else:
        print(f'[{etype}] {str(event)[:200]}')
