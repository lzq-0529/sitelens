# Tracker

Drop this on any independent site:

```html
<script defer src="https://your-sitelens.example/tracker.js" data-region="cn"></script>
```

Use `data-region="intl"` on the overseas storefront.

```js
sitelens.viewItem("sku-1", "Wool throw");
sitelens.addToCart("sku-1", "Wool throw");
sitelens.checkout();
sitelens.purchase({ amount: 199, sku: "sku-1", title: "Wool throw", order_id: "A1001" });
sitelens.signup("buyer@example.com");
```

`purchase.amount` is in major units (yuan / dollars). The console records it as an order.

Optional header if you set `SITELENS_COLLECT_TOKEN`: `X-Sitelens-Token`.
