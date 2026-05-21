# BugSwarm Sample Report: BuggyShop

## Summary

- Target: `http://buggyshop:8090`
- Run type: demo swarm exploration
- Expected result: BugSwarm should discover deterministic defects in the bundled demo app.
- Status: sample evidence for final project demonstrations.

## Findings

### HTTP 500 response detected

- Severity: high
- Category: `http_error`
- URL: `/checkout?empty=1`
- Expected: Checkout should handle an empty cart with a validation message.
- Actual: The route returns HTTP 500.
- Replay: open cart, click checkout anyway.

### Broken link detected

- Severity: medium
- Category: `broken_link`
- URL: `/products/ghost`
- Expected: Product links should resolve to product detail pages.
- Actual: The product detail route returns HTTP 404.
- Replay: open products, click Ghost Product.

### Console error detected

- Severity: medium
- Category: `console_error`
- URL: `/products`
- Expected: Product pages should not emit console errors.
- Actual: The product list emits `Inventory widget failed to hydrate`.

### Invalid email accepted

- Severity: medium
- Category: `form_validation_failure`
- URL: `/register`
- Expected: Registration should reject malformed email values.
- Actual: The demo form accepts `bad-email-value`.

### Page did not become idle

- Severity: medium
- Category: `infinite_loading`
- URL: `/orders`
- Expected: Order history should finish loading or show an empty state.
- Actual: The spinner never resolves.
