# Tracker

Drop this on any independent site:

```html
<script defer src="https://your-sitelens.example/tracker.js" data-region="cn" data-token="slcol_..."></script>
```

Use `data-region="intl"` on the overseas storefront. Production needs `data-token`.

```js
sitelens.viewItem("sku-1", "Wool throw");
sitelens.addToCart("sku-1", "Wool throw");
sitelens.checkout();
sitelens.identify("buyer@example.com");
sitelens.signup("buyer@example.com");
sitelens.purchase({ amount: 199, sku: "sku-1", title: "Wool throw", order_id: "A1001" });
```

`identify` / `signup` put the account on the event **and** in `props`. Without this, the visitors page stays empty.

`purchase.amount` is in major units (yuan / dollars). Prefer Shopify / Woo / generic webhooks for paid orders — see [getting-started.md](getting-started.md).

Production (`SITELENS_ENV=production`) rejects collect without `data-token` / `X-Sitelens-Token`.
