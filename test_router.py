import unittest
from datetime import datetime, timezone
from unittest.mock import patch
from router import decide, run_adapter

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.config = {'thresholds': {'claude_session_percent': 70, 'codex_weekly_percent': 80}, 'adapters': {}}
        self.usage = {'claude_session_percent': 30, 'codex_weekly_percent': 20, 'illustrative': True}

    def test_default_worker(self):
        r = decide('build', self.usage, self.config)
        self.assertEqual((r['lane'], r['model'], r['effort']), ('codex', 'Sol', 'medium'))

    def test_claude_boundary_routes_worker(self):
        self.usage['claude_session_percent'] = 70
        self.assertEqual(decide('claude', self.usage, self.config)['lane'], 'codex')

    def test_codex_boundary_routes_worker(self):
        self.usage['codex_weekly_percent'] = 80
        r = decide('build', self.usage, self.config)
        self.assertEqual((r['lane'], r['model']), ('claude', 'Sonnet'))

    def test_both_lanes_full_holds(self):
        self.usage.update(claude_session_percent=90, codex_weekly_percent=90)
        self.assertEqual(decide('build', self.usage, self.config)['action'], 'hold')

    def test_dispatcher_is_not_silently_switched(self):
        self.usage['claude_session_percent'] = 70
        r = decide('plan', self.usage, self.config)
        self.assertEqual((r['action'], r['model']), ('hold', 'Opus'))

    def test_astra_requires_a_reason_and_capacity(self):
        with self.assertRaises(ValueError):
            decide('stuck', self.usage, self.config)
        self.usage['codex_weekly_percent'] = 80
        self.assertEqual(decide('stuck', self.usage, self.config, 'hard issue')['action'], 'hold')

    def test_invalid_usage_is_rejected(self):
        for value in (True, -1, 101, float('nan'), '70'):
            self.usage['claude_session_percent'] = value
            with self.assertRaises(ValueError):
                decide('build', self.usage, self.config)

    @patch('router.subprocess.run')
    def test_sample_never_executes(self, run):
        r = decide('build', self.usage, self.config)
        with self.assertRaises(ValueError):
            run_adapter(r, 'sample task', self.usage, self.config)
        run.assert_not_called()

    @patch('router.subprocess.run')
    def test_stale_reading_never_executes(self, run):
        self.usage.update(illustrative=False, observed_at='2000-01-01T00:00:00Z')
        r = decide('build', self.usage, self.config)
        with self.assertRaises(ValueError):
            run_adapter(r, 'sample task', self.usage, self.config)
        run.assert_not_called()

    @patch('router.subprocess.run')
    def test_adapter_receives_json_without_shell(self, run):
        self.usage.update(illustrative=False, observed_at=datetime.now(timezone.utc).isoformat())
        self.config['adapters']['codex'] = ['python3', 'my_worker.py']
        run.return_value.returncode = 0
        r = decide('build', self.usage, self.config)
        self.assertEqual(run_adapter(r, 'public task', self.usage, self.config), 0)
        self.assertEqual(run.call_args.args[0], ['python3', 'my_worker.py'])
        self.assertNotIn('shell', run.call_args.kwargs)

if __name__ == '__main__':
    unittest.main()
