(function () {
  var script = document.currentScript || {};
  var endpoint = script.getAttribute("data-endpoint") || (script.src || "").replace(/tracker\.js.*$/, "api/collect");
  if (!endpoint) return;
  var key = script.getAttribute("data-token") || "";
  var region = script.getAttribute("data-region") || "";
  var storageKey = "sl_vid";
  function vid() {
    try {
      var existing = localStorage.getItem(storageKey);
      if (existing) return existing;
      var created = "sl_" + Math.random().toString(36).slice(2) + Date.now().toString(36);
      localStorage.setItem(storageKey, created);
      return created;
    } catch (err) {
      return "";
    }
  }
  function send(name, props) {
    var body = {
      name: name,
      visitor_id: vid(),
      path: location.pathname + location.search,
      title: document.title,
      referrer: document.referrer,
      host: location.host,
      region: region,
      utm: location.search,
      props: props || {},
    };
    var headers = { "content-type": "application/json" };
    if (key) headers["x-sitelens-token"] = key;
    try {
      if (navigator.sendBeacon && !key) {
        navigator.sendBeacon(endpoint, new Blob([JSON.stringify(body)], { type: "application/json" }));
        return;
      }
    } catch (err) {}
    fetch(endpoint, { method: "POST", headers: headers, body: JSON.stringify(body), keepalive: true, mode: "cors" }).catch(function () {});
  }
  window.sitelens = {
    track: send,
    viewItem: function (sku, title) { send("view_item", { sku: sku, title: title }); },
    addToCart: function (sku, title) { send("add_to_cart", { sku: sku, title: title }); },
    checkout: function (props) { send("begin_checkout", props || {}); },
    purchase: function (props) { send("purchase", props || {}); },
    signup: function (account) { send("signup", { account: account }); },
    identify: function (account) { send("identify", { account: account }); },
  };
  send("pageview", {});
})();
