# Your models. Your rules.

**Another model. Another decision. Keeping up should not be your job.**

This small starter chooses a model for a task and moves eligible worker jobs between Claude and Codex when your supplied usage reading reaches a threshold.

[Try the visual walkthrough](https://soyakaai-studio.github.io/model-router-starter/) · [Download the ZIP](https://github.com/soyakaai-studio/model-router-starter/archive/refs/heads/main.zip)

## Try it in a minute

Download and extract the ZIP. Open a terminal in that folder. You need Python 3.10 or newer, available on Mac, Linux and Windows. There are no packages to install and no API keys needed for the sample.

```sh
python3 router.py build
python3 router.py claude
python3 router.py stuck --reason "The normal worker could not resolve the issue"
```

On Windows, use `py` instead of `python3` if needed. The output shows the chosen lane, model and reason. The supplied readings are **illustrative**; these commands do not send anything or run an agent.

## What happens

| Job | Default |
| --- | --- |
| Plan / judge | Opus, medium, one dispatcher |
| Build / data / review | Sol, medium |
| Claude work | Sonnet, high |
| Stuck / long | Astra, high, only with your manual reason |
| Bulk public work | DeepSeek |

Claude session at 70% → eligible Claude worker jobs move to Codex. Codex weekly at 80% → eligible Codex worker jobs move to Claude. If both are busy, the engine holds work. Judgement stays with the Opus dispatcher; Astra escalation is never automatic.

The model names are editable starter labels in `router.py`, not guaranteed provider model IDs. Your adapter must translate them into IDs and effort settings supported by your account.

## Make it yours

1. Copy `config.example.json` to `config.json`. Choose your thresholds.
2. Copy `usage.example.json` to `usage.json`. Enter your own current percentages, set `illustrative` to `false`, and supply an ISO timestamp with a timezone in `observed_at`.
3. Preview: `python3 router.py build --config config.json --usage usage.json`.
4. Optionally connect your workers: put an explicit command argument list in each `adapters` lane. For example, `["python3", "my_worker_adapter.py"]`. The adapter receives a JSON object on standard input containing the lane, model label, effort, reason and prompt. It must call your chosen agent tool and enforce its own permissions.
5. Execute only after you have reviewed that adapter: `python3 router.py build --config config.json --usage usage.json --prompt "Build a report from public sample data" --run`.

`--run` refuses sample readings, stale readings, a held job or an unconfigured adapter. Keep credentials in your local secret store or environment, never in these files.

## What this starter does—and what still needs connecting

The rule engine works locally. Live usage collection, your provider/agent adapters, queues, retries, concurrency reservations and monitoring are not bundled. You supply the usage readings today. A new-model checker and a usage-pace alert are future ideas.

It cannot guarantee that limits will never be hit or always fully used. Provider limits can change and simultaneous jobs can consume capacity after a reading was taken. Start with one job at a time and retain headroom. A running job is not migrated mid-execution; routing chooses where a new job starts.

This is a public teaching starter, not a copy of Sonat's private deployment. Jev is part of his illustrated workflow; no private Jev connection or memory is included here.

## Check it

```sh
python3 -m unittest -v
```

MIT licensed. Created for Sonat / SoyakaAI. The repository contains generic sample data only.
