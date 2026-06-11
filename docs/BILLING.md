# Billing & Credits

Controlled by env vars (see `.env.example`). Source of truth: `app/billing.py`.

## Concepts

- **Credits**: `users.credits`. One `/generate` call costs `CREDITS_PER_GENERATION`
  (default 1), deducted by `billing.charge_generation`.
- **Plans**: defined in `BILLING_PLANS_JSON` — list of
  `{ id, name, price_usd, credits, polar_product_id, recurring }`.
  `available` (in API responses) is true only when `polar_product_id` is set.
- **Free tier modes** (`FREE_TIER_MODE`):
  - `trial` (default): grant `FREE_TRIAL_CREDITS` once at signup (`reason=signup_trial`).
  - `forever_free`: grant `FREE_MONTHLY_CREDITS` at signup (`reason=signup_free_monthly`),
    then top back up to that amount every ~30 days via `maybe_refill_monthly`
    (`reason=monthly_refill`), called on `/billing/summary` and `/generate`.
- Every credit change writes a `credit_ledger` row with the resulting balance
  (`balance_after`) — this is the audit trail for support/disputes.

## Payments (Polar — Merchant of Record)

1. `POST /billing/checkout?plan_id=<id>` -> `payments/polar.create_checkout`
   creates a Polar checkout session with `metadata.user_id` and `metadata.plan_id`,
   returns `checkout_url` for the frontend to redirect to.
2. Buyer pays on Polar's hosted page, redirected back to `POLAR_SUCCESS_URL`.
3. Polar sends a `POST /billing/webhook` (Standard Webhooks signed with
   `POLAR_WEBHOOK_SECRET`) — **this is the only trusted source of truth for
   crediting**, the success-page redirect is not.
   - `order.paid` -> `_handle_order_paid`: resolves the plan (by
     `metadata.plan_id` or `product_id`), resolves the user (by
     `metadata.user_id` or customer email), stores `polar_customer_id`, and
     calls `billing.add_purchase` which is **idempotent on `provider_ref`**
     (the Polar order id) — duplicate webhook deliveries don't double-credit.
   - `subscription.canceled` / `subscription.revoked` -> `_handle_subscription_end`:
     sets `users.plan = "free"` but leaves remaining credits untouched.
4. `POST /billing/portal` opens a Polar-hosted portal (requires
   `polar_customer_id`, i.e. at least one prior purchase) for managing
   cards/subscriptions/invoices.

## Margin math (display only)

`PlanOut.price_per_credit` and `margin_pct` are computed from
`price_usd`, `credits`, and `COST_PER_GENERATION_USD` for display in the
billing UI — purely informational, not enforced server-side.

## Admin overrides

`POST /admin/users/{id}/credits` lets an admin (`is_admin=true` or email in
`ADMIN_EMAILS`) directly adjust a user's balance, recorded as
`reason="admin:<reason>"` / `ref="admin:<admin email>"` in the ledger and as
an `admin_credit_adjust` audit event.
