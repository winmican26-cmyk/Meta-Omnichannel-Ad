# OmniConvert Platform Walkthrough

## Node Map

1. **Next.js Frontend**
   - Runs at `http://localhost:3003`
   - Pages: dashboard, auth, campaign wizard, optimizer, creative studio, analytics, migration.

2. **FastAPI Backend**
   - Runs at `http://127.0.0.1:8765`
   - Provides OpenAPI docs and all product APIs.

3. **Meta Auth Node**
   - `/auth/login`
   - `/auth/callback`
   - Exchanges Meta OAuth code for long-lived token.

4. **Session Node**
   - Stores `session_id`, access token, active ad account, and subscription tier.
   - Backed by SQLite.

5. **Billing Node**
   - `/billing/checkout`
   - `/billing/portal`
   - `/billing/webhook`
   - Stripe webhook updates `subscription_tier`.

6. **Paid Guard Node**
   - Enforces Pro/Enterprise on campaign creation, creative generation, sync, templates, duplication, and migration.

7. **Campaign Automation Node**
   - `/campaigns/ccco`
   - Creates Meta Ad Set, Creative, and Ad using the official SDK.

8. **Optimizer Node**
   - `/optimize/suggestions`
   - Produces channel priority, CPA prediction, bid cap, and routing guidance.

9. **Creative Studio Node**
   - `/creative/generate`
   - Generates `omnichannel_link_spec`, deep-link routing, and catalog creative variants.

10. **Analytics Node**
    - `/analytics/ingest`
    - `/analytics/sync/{adset_id}`
    - Stores web/app conversions, spend, CPA, and channel split.

11. **Dashboard Node**
    - `/dashboard/summary`
    - `/dashboard/ccco/{adset_id}`
    - Returns product home summary and ad set performance.

12. **Templates Node**
    - `/campaigns/templates`
    - `/campaigns/duplicate/{template_id}`
    - Saves reusable configs and duplicates campaigns.

13. **Migration Node**
    - `/migration/scan`
    - `/migration/plan/{old_campaign_id}`
    - Finds legacy web-only/app-only campaigns and recommends CCCO upgrade configs.

## Primary Journey

1. User opens frontend dashboard.
2. User connects Meta or saves `session_id`.
3. User upgrades through Stripe.
4. User creates a CCCO campaign.
5. User generates optimizer suggestions.
6. User generates creative variants.
7. User syncs Meta insights.
8. User views dashboard lift and web/app split.
9. User saves templates or scans legacy campaigns for migration.

## One-Minute Video Prompt

Create a 60-second cinematic product walkthrough in a deep ocean-blue style.

- **0-10s:** Show OmniConvert dashboard with glowing ocean-blue cards.
- **10-20s:** Show Meta OAuth and Stripe subscription nodes activating.
- **20-30s:** Show campaign wizard creating a CCCO campaign from web + app inputs.
- **30-40s:** Show AI optimizer and Creative Studio generating channel recommendations and deep-link creative variants.
- **40-50s:** Show Meta insights sync filling analytics dashboard with web/app conversion split and CPA lift.
- **50-60s:** Show migration scanner and templates. End with: “OmniConvert: agency-grade CCCO automation.”
