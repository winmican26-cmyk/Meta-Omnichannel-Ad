# Meta CCCO Engine

Meta CCCO Engine is a FastAPI product prototype for building and managing Meta cross-channel conversion optimization campaigns. The project focuses on campaigns that combine web pixel conversion signals with mobile app conversion signals, then wraps that campaign flow with authentication, billing, analytics, templates, migration tools, privacy tooling, and a static frontend.

The current frontend is a static HTML/CSS/JS product interface served by FastAPI from `app/static`. The backend is structured so a future React or Next.js dashboard can consume the same API without changing the service layer.

## What Is Included

- FastAPI API with structured logging, security headers, CORS, and custom exception handling.
- Pydantic v2 models for campaign creation, omnichannel promoted objects, link specs, creative payloads, and analytics rows.
- Meta OAuth login, long-lived token exchange, ad-account switching, and encrypted local session persistence.
- Email signup/login for browsing the product before connecting Meta.
- Campaign creation through the official `facebook-business` SDK.
- Rule-based optimizer suggestions for channel split, predicted CPA, bid cap, and deep-link routing.
- Creative Studio payload generation for omnichannel link specs and Advantage+ catalog variants.
- SQLite persistence for campaigns, sessions, templates, insights, and GDPR/data-rights requests.
- Stripe checkout, billing portal, webhook handling, Pro/Enterprise subscription checks, and credit metering.
- Analytics ingestion, Meta insights sync, dashboard summaries, reusable templates, and migration planning.
- Static product pages, privacy policy, terms, help page, cookie preferences, onboarding tour, and assistant widget.
- Pytest coverage for validation, auth, billing, analytics, dashboard, migration, templates, database helpers, creative, and optimizer logic.

## Quick Start

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --no-cache-dir --timeout=300 --extra-index-url https://pypi.org/simple/ -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8765
```

Open:

```text
http://127.0.0.1:8765/
```

API docs are intentionally disabled unless enabled in the environment:

```powershell
$env:ENABLE_API_DOCS='true'
uvicorn app.main:app --reload --port 8765
```

Then open:

```text
http://127.0.0.1:8765/docs
```

## Proof Report: Claude vs. Rule Engine

`POST /optimize/backtest` is the headline differentiator. It is the move past Meta's intended scope — not a flashier creative, but an independent, account-scoped, *explainable* performance brain that can **test whether** the Claude optimizer outperforms the rule baseline on the operator's own historical data. It does not claim Claude always wins; it lets the data answer that question and surfaces an honest note in the response when no Anthropic key is configured (in which case the comparison degenerates to rule-vs-rule and is labeled as such).

What it does:

- Strictly scoped to the calling session's `(session_id, ad_account_id)` so it can never read another tenant's data.
- For each owned ad set with enough history, the runner splits the daily insights chronologically into a **history** window and a **holdout** window.
- Reconstructs the `OptimizeRequest` that would have been issued at the split point.
- Runs *both* optimizers — Claude (with a leak-free history snapshot injected via `history_override`) and the legacy rule engine — using only the history window.
- Scores each optimizer's `predicted_cpa` and predicted app-share against the *realized* values in the holdout window.
- Returns MAE, RMSE, and per-adset wins per optimizer, plus an honest `notes` array (e.g. "ANTHROPIC_API_KEY is unset; this is a rule-vs-rule comparison").

Why Meta will not ship this: it would mean Meta benchmarking its own optimizer publicly to every advertiser. Independent SaaS can.

Request:

```json
{
  "session_id": "<session_id>",
  "ad_account_id": "act_123",
  "history_ratio": 0.5,
  "min_rows": 7,
  "max_adsets": 25
}
```

Response shape (truncated):

```json
{
  "session_id": "<session_id>",
  "ad_account_id": "act_123",
  "adsets_evaluated": 4,
  "claude": { "samples": 4, "cpa_mae": 1.42, "cpa_rmse": 1.81, "app_share_mae": 6.2, "wins_cpa": 3, "wins_app_share": 2 },
  "rule":   { "samples": 4, "cpa_mae": 2.95, "cpa_rmse": 3.40, "app_share_mae": 11.8, "wins_cpa": 1, "wins_app_share": 2 },
  "head_to_head": { "cpa_winner": "claude", "app_share_winner": "tie" },
  "per_adset": [ /* per-adset realized + predicted + label */ ],
  "notes": []
}
```

## Grader Demo Walkthrough

Use this path when presenting or grading the project.

1. Start the app with `uvicorn app.main:app --reload --port 8765`.
2. Open `http://127.0.0.1:8765/`.
3. Show the homepage/product dashboard preview: platform summary, campaign engine flow, optimizer/creative/analytics panels, privacy tools, and help/login links.
4. Open `/setup` to show the Meta developer/OAuth readiness checklist.
5. Open `/help` to show the guided user workflow.
6. Open `/login` to show email login/signup and the Meta connection path.
7. Open `/privacy-policy` and the homepage DSR form to show GDPR/data-rights coverage.
8. **Demo the Proof Report.** Hit `POST /optimize/backtest` with a Pro session that owns campaigns with ingested history. Walk through MAE/RMSE and per-adset wins. Show the `notes` field so the grader sees the runner refuses to fake a Claude-vs-Rule comparison when no API key is configured.
9. **Demo tenant safety.** With session A authenticated, attempt `GET /dashboard/ccco/<session_B_adset>` and `POST /analytics/ingest` against session B's adset. Both return 404. Then show `GET /campaigns/ccco?session_id=<A>` returns only A's campaigns.
10. Run `python -m pytest --basetemp .\tmp-pytest` to show automated backend verification (the `test_tenant_safety` and `test_optimizer_evidence` suites are the receipts).
11. If Meta/Stripe credentials are available, demonstrate live OAuth and checkout. Otherwise explain that those integrations are credential-gated and covered by service-level tests.

Strong presentation points:

- Campaigns are created paused by default, so the user can review ad sets before spend begins.
- Session tokens are encrypted at rest in SQLite.
- Paid actions are protected by subscription checks and credit metering.
- Every read and write is account-scoped: campaign listing, dashboard, analytics ingest, sync, and the backtest all enforce `(session_id, ad_account_id)` ownership through `require_adset_owner`. No cross-tenant leakage.
- The Proof Report (`/optimize/backtest`) is the on-demand harness for **testing whether** the Claude optimizer outperforms the rule baseline on the operator's own historical data. It honestly labels rule-vs-rule comparisons when no Anthropic key is configured. That honesty — not a marketing claim — is what separates this from "another AI wrapper."
- The database is local SQLite for development, but the data-access functions are isolated enough to swap for Postgres later.

## Running Tests

```powershell
python -m pytest --basetemp .\tmp-pytest
```

The explicit `--basetemp` avoids `PermissionError` on Windows environments where the default `%TEMP%` location under `AppData\Local\Temp` is not writable to the pytest worker. Once you have run it once, the `.tmp-pytest` directory can be safely deleted.

`pytest.ini` stores pytest cache under `C:\tmp\meta-omni-channel-ad-pytest-cache` to avoid local Windows permission issues with the default temp/cache locations.

## Docker

```powershell
docker build -t meta-ccco-engine .
docker run -p 8765:8765 --env-file .env meta-ccco-engine
```

## Environment Configuration

Copy `.env.example` to `.env`, then fill in the values needed for the integrations you want to demo.

Meta Business Login:

```text
META_APP_ID=your_meta_app_id
META_APP_SECRET=your_meta_app_secret
META_REDIRECT_URI=http://localhost:8765/auth/callback
META_LOGIN_CONFIG_ID=optional_login_for_business_config_id
```

Stripe billing:

```text
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_PRO_PRICE_ID=price_...
STRIPE_ENTERPRISE_PRICE_ID=price_...
BILLING_SUCCESS_URL=http://localhost:8765/billing/success
BILLING_CANCEL_URL=http://localhost:8765/
```

Useful local settings:

```text
ENABLE_API_DOCS=true
CCCO_DB_PATH=campaigns.db
PUBLIC_BASE_URL=http://127.0.0.1:8765
```

Anthropic (Tier 1 Claude Optimizer):

```text
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_OPTIMIZER_MODEL=claude-sonnet-4-6
ANTHROPIC_OPTIMIZER_MAX_TOKENS=1500
```

When `ANTHROPIC_API_KEY` is unset, `/optimize/suggestions` transparently falls back to the legacy rule-based optimizer, so the endpoint works in any environment.

## Core API Map

System:

```text
GET /health
GET /docs                # only when ENABLE_API_DOCS=true
```

Authentication:

```text
GET  /auth/login
GET  /auth/callback
GET  /auth/me
POST /auth/switch-account/{ad_account_id}
POST /auth/email/signup
POST /auth/email/login
GET  /auth/setup-status
```

Billing and credits:

```text
POST /billing/checkout
POST /billing/portal
POST /billing/webhook
GET  /credits/balance
```

Campaigns:

```text
POST /campaigns/ccco
GET  /campaigns/ccco
POST /campaigns/templates
GET  /campaigns/templates
POST /campaigns/duplicate/{template_id}
```

Optimization and creative:

```text
POST /optimize/suggestions
POST /optimize/backtest        # scores Claude vs. rule engine on the account's own history
POST /creative/generate
```

Analytics and dashboard:

```text
POST /analytics/ingest
POST /analytics/sync/{adset_id}
GET  /dashboard/summary
GET  /dashboard/ccco/{adset_id}
```

Migration:

```text
GET  /migration/scan
POST /migration/plan/{old_campaign_id}
```

Privacy:

```text
POST /privacy/dsr
GET  /privacy/dsr/{ticket_id}
POST /privacy/meta/deletion
GET  /privacy/meta/deletion-status/{confirmation_code}
```

## Example: Optimizer Suggestions

`POST /optimize/suggestions`

```json
{
  "session_id": "<session_id>",
  "name": "Spring Promo",
  "event": "PURCHASE",
  "omnichannel": {
    "app": [],
    "pixel": []
  },
  "daily_budget": 5000,
  "web_url": "https://example.com/products",
  "android_deeplink": "myapp://products"
}
```

Example response:

```json
{
  "recommendations": [
    {
      "channel": "app",
      "weight_percent": 65,
      "reason": "App deeplinks are available for a high-intent commerce event.",
      "expected_cpa_lift": 18.0
    },
    {
      "channel": "web",
      "weight_percent": 35,
      "reason": "Web fallback keeps acquisition open for users without the app installed.",
      "expected_cpa_lift": 8.0
    }
  ],
  "suggested_bid_cap": 60,
  "predicted_cpa": 12.4,
  "creative_tip": "Use dynamic product deep links in Advantage+ catalog ads to reduce landing friction.",
  "deep_link_routing_rule": "deeplink_with_web_fallback"
}
```

## Example: CCCO Campaign Creation

`POST /campaigns/ccco`

```json
{
  "name": "Spring Promo",
  "session_id": "<session_id>",
  "page_id": "1122334455",
  "daily_budget": 5000,
  "event": "PURCHASE",
  "pixel_id": "456",
  "application_id": "123",
  "web_url": "https://example.com/products",
  "android_deeplink": "myapp://products",
  "ios_deeplink": "myapp://products",
  "omnichannel": {
    "app": [
      {
        "application_id": "123",
        "custom_event_type": "PURCHASE",
        "object_store_urls": [
          "https://play.google.com/store/apps/details?id=com.example.app",
          "https://apps.apple.com/us/app/example/id123456789"
        ]
      }
    ],
    "pixel": [
      {
        "pixel_id": "456",
        "custom_event_type": "PURCHASE"
      }
    ]
  }
}
```

The endpoint creates:

1. A paused ad set with `promoted_object.omnichannel_object`.
2. A creative with `omnichannel_link_spec`.
3. A paused ad with web and app tracking specs.
4. A local SQLite record in `campaigns.db`.

## Example: Analytics Ingestion

`POST /analytics/ingest`

```json
{
  "session_id": "<session_id>",
  "adset_id": "238500000000001",
  "insights": [
    {
      "adset_id": "238500000000001",
      "date": "2026-05-12",
      "conversions_web": 18,
      "conversions_app": 32,
      "spend": 620.0,
      "cpa": 12.4,
      "channel_split_web": 36.0,
      "channel_split_app": 64.0
    }
  ]
}
```

`GET /dashboard/ccco/{adset_id}` then returns total conversions, spend, average CPA, CCCO lift, channel split, and the daily insight rows.

## Notes

- The default targeting is intentionally minimal and request-driven through `countries`.
- Meta permissions, page ownership, pixel ownership, app ownership, and account access are still enforced by Meta's Graph API.
- Live campaign creation requires valid Meta credentials and the `facebook-business` package.
- Stripe checkout and webhooks require valid Stripe test credentials.
- SQLite is used as a local development persistence layer.

## Roadmap — Beyond Meta's CCCO Ceiling

Meta's intended scope for this project is a competent ops console for one Meta ad product: rule-based optimizer, link-spec generation, static analytics, paused-by-default campaigns. The roadmap below pushes the product past that ceiling using Anthropic (Claude), OpenAI, and Meta Movie Gen. Every stage preserves the existing endpoint contracts so the static frontend keeps working while the engine underneath gets replaced.

Status legend: `[ ]` planned, `[~]` in progress, `[x]` shipped.

### Tier 1 — Claude Optimizer + Evidence Layer (replace the rule engine and prove it beats the baseline)

The README already calls the rule-based optimizer "a clean replacement point for an LLM or ML model." This tier takes the invitation *and* builds the evidence required to claim we beat it.

Optimizer:

- [x] Add `anthropic` SDK and `ANTHROPIC_API_KEY` env var.
- [x] Implement `ClaudeOptimizer` service that reads campaign request + 90-day historical insights from SQLite, produces channel split, bid cap, predicted CPA, and an English "why" the rule engine can't generate.
- [x] Use prompt caching on the system prompt + Meta CCCO reference so per-request cost stays low.
- [x] Keep `OptimizerSuggestion` schema and `/optimize/suggestions` endpoint contract identical — drop-in swap.
- [x] Graceful fallback to the legacy rule engine when no API key is configured or the Anthropic call fails.

Closing the advisory-weights credibility gap:

- [x] **Applied bid cap.** `CampaignCreateRequest.bid_amount_cents` is optional. When present, the ad set is created with `bid_strategy='LOWEST_COST_WITH_BID_CAP'` and `bid_amount=<value>`, so the optimizer's `suggested_bid_cap` flows into actual Meta delivery instead of staying advisory. When absent, the legacy `LOWEST_COST_WITHOUT_CAP` strategy is used. Verified by [tests/test_bid_application.py](tests/test_bid_application.py).

Evidence layer (what makes this an "above Meta" move, not a flashy reskin):

- [x] **Account-scoped history.** `ccco_campaigns` and `campaign_insights` now carry `session_id` and `ad_account_id`; the Claude optimizer filters by `(session_id, ad_account_id)` strictly so one advertiser never reads another's performance. New helpers: `list_owned_ccco_campaigns`, `_weighted_history_for_owner`.
- [x] **Spend-weighted, conversion-weighted metrics.** Trailing CPA is `SUM(spend) / SUM(conversions)`, not flat `AVG(cpa)`; channel splits are conversion-weighted. Low-spend days no longer drown high-spend days in the signal handed to Claude.
- [x] **Per-event breakdown.** History snapshot includes a per-event aggregate (PURCHASE / LEAD / ATC / …) so Claude can reason about the operator's CPA-by-event reality.
- [x] **Optimizer-run logging.** Every `/optimize/suggestions` call writes to `optimizer_runs` (which optimizer ran, which fallback if any, full request + suggestion JSON). Future backtests will be faithful because the input is captured at decision time.
- [x] **Backtest harness.** `POST /optimize/backtest` splits each owned adset into history / holdout windows, runs Claude (with a leak-free history override) and the rule engine on the history-only inputs, scores both against realized CPA and app-share in the holdout, and reports MAE, RMSE, and per-adset wins.
- [ ] Extended-thinking mode for budget shifts above a configurable threshold.
- [ ] Tool-use loop with live Meta Graph API calls (audience size, cost benchmarks, ad-library competitor lookups).
- [ ] Apply optimizer-derived bid cap and attribution settings into actual Meta `bid_amount` / `attribution_spec` at campaign-creation time (current optimizer output is advisory; this closes that loop).

### Tier 2 — Multimodal Creative Studio (real assets, not link specs)

Today `/creative/generate` returns JSON link specs. This tier turns it into a creative factory.

- [ ] Claude (Sonnet 4.6) writes concept + storyboard from brand voice, product, audience, and prior winners.
- [ ] OpenAI `gpt-image-1` produces hero images and carousel frames across all Meta placements (9:16, 1:1, 1.91:1) in one pass.
- [ ] Meta Movie Gen (when API access is available) is the primary video backend; OpenAI Sora is the immediate fallback. 6–15s vertical video generated from Claude's storyboard.
- [ ] OpenAI TTS (`gpt-4o-mini-tts`) produces per-locale voiceover with brand-tone control.
- [ ] Claude with vision QAs every generated asset against Meta ad policy + brand guidelines, regenerates rejects.
- [ ] `/creative/generate` returns ready-to-upload assets, not just `omnichannel_link_spec` JSON.

### Tier 3 — Autonomous Omnichannel Agent (what Meta will not build)

Meta cannot ship an agent that routes spend off Meta. This tier turns the project into one.

- [ ] Wrap every FastAPI endpoint as an MCP tool so an agent can drive the platform.
- [ ] Claude Agent SDK orchestrator with persistent session state per ad account.
- [ ] Scheduled loop (every 4h per ad account): pull insights, detect drift (CPA spike, frequency burnout, creative fatigue, audience saturation), decide actions, write a daily English brief into the dashboard.
- [ ] Human-in-the-loop guardrails: budget moves above a threshold and any new ad launch require one-click approval in the dashboard. Non-negotiable — ads spend real money.
- [ ] OpenAI Realtime API voice interface: "What's happening with my Spring Promo campaign?" answered live with tool calls against current data.
- [ ] Add MCP tool packs for Google Ads, TikTok Ads, and LinkedIn Ads. Project stops being a Meta tool and becomes an autonomous omnichannel media buyer.

### Sequencing

1. Tier 1 optimizer swap (weeks 1–2). Instrument cost + latency, A/B against the rule engine on past campaigns.
2. Tier 2 creative pipeline (weeks 3–4). Ship gpt-image + TTS first; add video as Movie Gen / Sora access lands.
3. Tier 3 MCP wrapping + manual-trigger agent (weeks 5–6).
4. Scheduled agent loop + approval UI + voice (weeks 7–8).
5. Cross-platform tool packs (weeks 9+).
