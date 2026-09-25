# OpenRouter trial setup

The original shortlist is Qwen3.8 Flash for routine answers, GPT-6 Sol for difficult
cases and GLM 5.3 Flash for comparison. Selection between routes remains future
router work; the current text route uses one explicitly selected profile.
The user authorised a **$5 total trial inference-credit limit**, shared across
serving, evaluation and all selected models. This is not a recurring allowance.

## Local setup

1. In [OpenRouter keys](https://openrouter.ai/settings/keys), create a dedicated
   project key with credit limit **5** and reset **never**.
   No BYOK setting is required. Keep automatic credit top-ups off and use OpenRouter
   credits without connecting separate provider keys for this trial.
2. From the repository root, run `.venv/bin/ask-phil configure-openrouter` in your
   terminal. Paste only into its hidden prompt, never chat, a shell command,
   tracked configuration, GitHub, or an evaluation artifact.
3. The command reads back the provider limit before saving
   `.secrets/openrouter.key` (mode 0600; parent 0700). It refuses to overwrite an
   existing key. `.secrets/` and `.env*` are Git-ignored; Docker excludes them too.
   `.env.example` is the sole Git exception and must never contain credentials.
4. Select `export ASK_PHIL_MODELS=config/openrouter-sol.json` in the shell
   running the API or evaluation script. This is the accepted issue-4 profile.
   `config/openrouter-qwen.json` and `config/openrouter-glm.json` remain comparison
   candidates: Qwen's first smoke failed citation validation; GLM is untested.
   Configuration files contain no credentials. Local smoke commands keep
   `config/local-models.json` as their default; there is no silent provider fallback.

The setup command **checks**, rather than sets, your remote key limit. The user
entered the key locally, and real limit readback and bounded inference have now
passed. The final readback reports $4.89109413 remaining under the non-resetting
$5 cap; private storage remains 0600 inside a 0700 directory. Account top-up settings cannot be
verified through the ordinary inference key API. Purchase fees and taxes are
outside the $5 inference-credit limit.

## Spending and reproducibility controls

Before every paid call, the app verifies a positive, non-resetting provider limit
no larger than $5 and remaining credit. The optional `include_byok_in_limit` flag
does not gate ordinary credit-funded keys, including when false or absent.
BYOK means separately connected provider credentials and is outside this trial.
The account balance can exceed $5 without increasing the key's limit. It verifies the
configured provider/model version still advertises required parameters. Calls
pin a provider, forbid fallback, enforce maximum token prices, send one strict
JSON response schema, and use bounded input/output. There are no automatic retries,
tools, searches or paid plugins in this slice.

All profiles share `artifacts/openrouter-budget.sqlite`. SQLite transactions
reserve conservative prompt/output cost before HTTP; reported cost settles the
reservation once. Missing billing data, timeouts and interruptions retain the
reservation. Preserve this file across restarts and run from the repository root.
Do not delete it, copy it into separate trial runners or rotate the key to reset
the allowance. The local byte-based reservation is conservative accounting, not
a measured token total; the provider's verified key cap is the billing authority.

Answer receipts and MLflow traces retain the selected configuration, returned
model/provider, request ID, reported cost, reservation and reasoning-token count.
Completion tokens include reasoning; the separate reasoning count is a subset.
Unknown cost is null, never a fictitious zero. Provider errors omit upstream
bodies and authorization headers. Only source/context, final answers and safe
usage fields enter tracing; the credential is not a model setting.

The embedding model/digest and retrieval/context limits remain unchanged. Profile
changes need new captured answers and independent reviews. The provider schema
uses `anyOf` for the mutually exclusive qualification kinds; the original Pydantic
validation still enforces the domain contract after generation.

## Evaluation and publication

Use `scripts/evaluate_answer_policy.py capture` with an explicitly chosen cloud
profile and a new output path. Begin with a single case; then capture the 13-case
policy dataset. Its command help describes case and output arguments. The older
issue-3 `evaluate_text_baseline.py` is local-only and rejects cloud profiles.
Cloud captures distinguish paid attempts from local runs and retain the same
shared spending controls. A software pass is not a semantic acceptance pass.

Before every commit/publication run `python3 scripts/check_secrets.py` after
staging intended files. It checks the Git index, including the actual local key
if present, without printing credentials. Do not force-add ignored files. The
scanner recognises common provider-key prefixes; it is not a detector for all
possible secrets. Review the staged file list as well.

Container builds contain the profiles and adapter but no credentials. Live cloud
execution is initially configured through the native CLI/evaluation path. A
container run needs a read-only secret mount readable by its runtime UID and the
same persistent budget ledger; never bake a key into an image or build argument.
Existing local-model containers have not been switched to cloud inference.

The [issue-4 cloud baseline](issue-4/cloud/README.md) passes its independently
reviewed 13-case policy matrix and five actual CLI/API/restart checks. This is a
small exposed development slice, not deployment-quality or broad canon approval.
No automatic router or model fallback has been enabled.

## Software validation (2026-09-25)

Software validation: full native suite **83 passed** against disposable real
PostgreSQL; Ruff and strict mypy passed. No tests called a paid provider.
The subsequent review fix passed all **3 cloud receipt integration cases**, including
a billed, truncated answer whose prompt/completion counts survive failure in the
receipt and trace. Staged files and existing Git history passed the provider-key scan.

### Standards review

One finding: retain known token usage for rejected completions. Fixed by retaining
usage before answer validation and recording it in failed receipts and traces.

### Spec review

One finding: the same failed-completion accounting gap. Fixed with the corresponding
integration regression. No other scope or requirements findings were reported.

The subsequent ordinary-key/BYOK correction passed 85 tests. After the live policy
prompt repair, the full suite again passed **85 tests**, Ruff and strict mypy
(27 files). [Separate live evidence](issue-4/cloud/summary.json) records 32 paid
attempts costing $0.10890587: $0.10190787 offline evaluation and $0.006998 serving.
All reservations settled; the ledger rounds upward to $0.108911. Preserve it.

## Verified reference material (2026-09-25)

- [OpenRouter key limits](https://openrouter.ai/docs/api_reference/limits)
- [Provider pinning, parameter support and maximum prices](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Reasoning and completion budgets](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)
- [BYOK billing and routing](https://openrouter.ai/docs/guides/overview/auth/byok)
- [GPT-6 Sol parameters](https://developers.openai.com/api/docs/models/gpt-6-sol)

The public endpoint catalog confirmed Alibaba/Qwen at $0.15/$0.47, OpenAI/Sol at
$2/$10, and Fireworks/GLM at $0.15/$0.50 per million input/output tokens at setup.
These are ceilings in the checked-in profiles, not guarantees of future prices.
Qwen and GLM start at low reasoning with 4096 completion tokens; Sol uses medium
reasoning with 8192. Sol now has scoped policy acceptance; the recorded observations
do not establish a general provider ranking or production cost/latency estimate.
Broader model comparisons and route selection remain later evaluated work.
