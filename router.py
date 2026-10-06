"""Small, dependency-free rule engine. No provider API or private deployment required."""
import argparse
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

RULES = {
    'plan': ('claude', 'Opus', 'medium'),
    'judge': ('claude', 'Opus', 'medium'),
    'build': ('codex', 'Sol', 'medium'),
    'data': ('codex', 'Sol', 'medium'),
    'review': ('codex', 'Sol', 'medium'),
    'claude': ('claude', 'Sonnet', 'high'),
    'bulk-public': ('deepseek', 'DeepSeek', 'default'),
    'stuck': ('codex', 'Astra', 'high'),
    'long': ('codex', 'Astra', 'high'),
}

def decide(job, usage, config, reason=None):
    if job not in RULES:
        raise ValueError('Unknown job type')
    levels = [usage['claude_session_percent'], usage['codex_weekly_percent']]
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 100 for v in levels):
        raise ValueError('Usage percentages must be numbers from 0 to 100')
    limits = config['thresholds']
    if any(not 0 < limits[k] <= 100 for k in ('claude_session_percent', 'codex_weekly_percent')):
        raise ValueError('Thresholds must be from 1 to 100')
    lane, model, effort = RULES[job]
    result = {'action': 'route', 'job': job, 'lane': lane, 'model': model, 'effort': effort,
              'reason': 'fixed default', 'mode': 'illustrative' if usage.get('illustrative') else 'live-reading'}
    if job in ('stuck', 'long'):
        if not reason or not reason.strip():
            raise ValueError('Astra needs a manual reason: --reason "why escalation is needed"')
        result['reason'] = 'manual escalation: ' + reason.strip()
    claude_busy = levels[0] >= limits['claude_session_percent']
    codex_busy = levels[1] >= limits['codex_weekly_percent']
    if lane == 'deepseek':
        return result
    if claude_busy and codex_busy:
        result.update(action='hold', reason='both configured usage thresholds reached')
    elif job in ('plan', 'judge') and claude_busy:
        result.update(action='hold', reason='keep judgement on the Opus dispatcher; wait for capacity')
    elif job in ('stuck', 'long') and codex_busy:
        result.update(action='hold', reason='manual Astra route has no capacity; do not silently substitute')
    elif lane == 'claude' and claude_busy:
        result.update(lane='codex', model='Sol', effort='medium', reason='Claude threshold reached; use Codex worker')
    elif lane == 'codex' and codex_busy:
        result.update(lane='claude', model='Sonnet', effort='high', reason='Codex threshold reached; use Claude worker')
    return result

def run_adapter(result, prompt, usage, config):
    if result['action'] != 'route':
        raise ValueError('Work is held; no adapter will run')
    if usage.get('illustrative'):
        raise ValueError('Sample readings cannot execute work. Supply your own current readings.')
    observed = datetime.fromisoformat(usage['observed_at'].replace('Z', '+00:00'))
    if observed.tzinfo is None:
        raise ValueError('observed_at must include a timezone')
    age = (datetime.now(timezone.utc) - observed).total_seconds()
    if not 0 <= age <= config.get('max_reading_age_seconds', 300):
        raise ValueError('Usage reading is stale or in the future; refresh it before executing')
    command = config.get('adapters', {}).get(result['lane'])
    if not isinstance(command, list) or not command or any(not isinstance(x, str) for x in command):
        raise ValueError('Configure an adapter argument list for the selected lane first')
    payload = dict(result, prompt=prompt)
    # No shell expansion. Adapter is explicitly configured by the person installing this kit.
    completed = subprocess.run(command, input=json.dumps(payload), text=True, timeout=3600, check=False)
    return completed.returncode

def main():
    p = argparse.ArgumentParser(description='Choose a model and lane using your own rules and usage readings.')
    p.add_argument('job', choices=RULES)
    p.add_argument('--usage', default='usage.example.json')
    p.add_argument('--config', default='config.example.json')
    p.add_argument('--reason')
    p.add_argument('--prompt', default='')
    p.add_argument('--run', action='store_true', help='Run your configured adapter, only with fresh non-sample readings')
    a = p.parse_args()
    try:
        usage = json.loads(Path(a.usage).read_text())
        config = json.loads(Path(a.config).read_text())
        result = decide(a.job, usage, config, a.reason)
        print(json.dumps(result, indent=2))
        if a.run:
            if not a.prompt.strip():
                raise ValueError('--run needs a nonempty --prompt')
            return run_adapter(result, a.prompt, usage, config)
        return 0
    except (ValueError, KeyError, OSError, subprocess.TimeoutExpired) as e:
        p.exit(2, f'Cannot route: {e}\n')

if __name__ == '__main__':
    raise SystemExit(main())
