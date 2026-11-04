from __future__ import annotations

import hashlib
import hmac
import json
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class StoreReadyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SITELENS_DATA_DIR"] = self.tmp.name
        os.environ["SITELENS_DATABASE_URL"] = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        os.environ.pop("SITELENS_GEO_TOKEN", None)
        os.environ.pop("SITELENS_COLLECT_TOKEN", None)
        os.environ.pop("SITELENS_ENV", None)
        os.environ.pop("SITELENS_CORS_ORIGINS", None)
        from sitelens import db as db_module
        from sitelens.app import create_app
        from sitelens.auth import OWNER, create_user

        db_module.init_db()
        with db_module.SessionLocal() as session:
            create_user(session, "boss", "owner-password-1", role=OWNER, display_name="站长")
            session.commit()
        self.client = TestClient(create_app())
        self.db_module = db_module

    def tearDown(self) -> None:
        if getattr(self, "client", None):
            self.client.close()
        if getattr(self, "db_module", None) and self.db_module.engine is not None:
            self.db_module.engine.dispose()
        self.tmp.cleanup()

    def login(self) -> TestClient:
        client = TestClient(self.client.app)
        res = client.post("/api/admin/login", json={"username": "boss", "password": "owner-password-1"})
        self.assertEqual(res.status_code, 200, res.text)
        return client

    def test_signup_from_tracker_props_identifies_visitor(self):
        self.client.post(
            "/api/collect",
            json={"name": "signup", "visitor_id": "vid-alice", "user_agent": "Mozilla/5.0", "props": {"account": "alice@example.com"}},
        )
        owner = self.login()
        found = owner.get("/api/admin/site/visitors?identified=true&q=alice@example.com").json()
        self.assertEqual(found["total"], 1)
        self.assertEqual(found["data"][0]["account"], "alice@example.com")

    def test_identify_reads_email_inside_props(self):
        self.client.post(
            "/api/collect",
            json={"name": "identify", "visitor_id": "vid-bob", "user_agent": "Mozilla/5.0", "props": {"email": "bob@shop.test"}},
        )
        owner = self.login()
        found = owner.get("/api/admin/site/visitors?identified=true").json()
        self.assertEqual(found["total"], 1)
        self.assertEqual(found["data"][0]["account"], "bob@shop.test")

    def test_intl_host_from_settings_is_not_forced_cn(self):
        owner = self.login()
        owner.put("/api/admin/settings", json={"cn_hosts": "lumen.shop", "intl_hosts": "intl.lumen.shop"})
        self.client.post(
            "/api/collect",
            json={"name": "pageview", "visitor_id": "vid-intl", "host": "intl.lumen.shop", "user_agent": "Mozilla/5.0"},
        )
        visitors = owner.get("/api/admin/site/visitors").json()
        row = next(item for item in visitors["data"] if item["id"] == "vid-intl")
        self.assertEqual(row["region"], "intl")

    def test_generic_order_webhook_creates_paid_order(self):
        owner = self.login()
        settings = owner.put(
            "/api/admin/settings",
            json={"hook_token": "slhook_test_token_1"},
        ).json()
        self.assertTrue(settings.get("hook_token"))
        raw = {
            "id": "woo-88",
            "amount": 128,
            "title": "北欧羊毛毯",
            "sku": "wool-1",
            "customer": "ada@shop.test",
            "region": "intl",
            "currency": "USD",
        }
        denied = self.client.post("/api/hooks/order", json=raw)
        self.assertEqual(denied.status_code, 401)
        ok = self.client.post("/api/hooks/order", json=raw, headers={"x-sitelens-token": "slhook_test_token_1"})
        self.assertEqual(ok.status_code, 200, ok.text)
        orders = owner.get("/api/admin/orders").json()
        self.assertEqual(orders["total"], 1)
        self.assertEqual(orders["data"][0]["title"], "北欧羊毛毯")
        self.assertEqual(orders["data"][0]["source"], "webhook")
        summary = owner.get("/api/admin/orders/summary").json()
        self.assertIn("by_product", summary)
        self.assertEqual(summary["by_product"][0]["label"], "北欧羊毛毯")

    def test_shopify_webhook_accepts_valid_hmac(self):
        owner = self.login()
        owner.put("/api/admin/settings", json={"shopify_secret": "shpsec"})
        payload = {
            "id": 9001,
            "email": "buyer@shopify.test",
            "total_price": "19.90",
            "currency": "USD",
            "financial_status": "paid",
            "line_items": [{"sku": "mug", "title": "Hand mug"}],
            "created_at": "2026-11-03T12:00:00Z",
        }
        raw = json.dumps(payload, separators=(",", ":")).encode()
        digest = hmac.new(b"shpsec", raw, hashlib.sha256).digest()
        import base64

        header = base64.b64encode(digest).decode()
        bad = self.client.post(
            "/api/hooks/shopify",
            content=raw,
            headers={"content-type": "application/json", "x-shopify-hmac-sha256": "nope", "x-shopify-topic": "orders/paid"},
        )
        self.assertEqual(bad.status_code, 401)
        ok = self.client.post(
            "/api/hooks/shopify",
            content=raw,
            headers={"content-type": "application/json", "x-shopify-hmac-sha256": header, "x-shopify-topic": "orders/paid"},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(owner.get("/api/admin/orders").json()["total"], 1)

    def test_woocommerce_webhook_accepts_valid_signature(self):
        owner = self.login()
        owner.put("/api/admin/settings", json={"woo_secret": "woosec"})
        payload = {
            "id": 77,
            "status": "completed",
            "total": "88.00",
            "currency": "CNY",
            "billing": {"email": "woo@shop.test"},
            "line_items": [{"sku": "cup", "name": "手冲杯"}],
            "date_created": "2026-11-03T12:00:00",
        }
        raw = json.dumps(payload).encode()
        import base64

        header = base64.b64encode(hmac.new(b"woosec", raw, hashlib.sha256).digest()).decode()
        ok = self.client.post(
            "/api/hooks/woocommerce",
            content=raw,
            headers={"content-type": "application/json", "x-wc-webhook-signature": header},
        )
        self.assertEqual(ok.status_code, 200, ok.text)
        self.assertEqual(owner.get("/api/admin/orders").json()["data"][0]["title"], "手冲杯")

    def test_cors_does_not_reflect_unknown_origins(self):
        res = self.client.options(
            "/api/collect",
            headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "POST"},
        )
        self.assertNotEqual(res.headers.get("access-control-allow-origin"), "*")
        self.assertIsNone(res.headers.get("access-control-allow-origin"))

    def test_cors_allows_configured_store_host(self):
        owner = self.login()
        owner.put("/api/admin/settings", json={"domains": "lumen.shop", "cn_hosts": "lumen.shop"})
        res = self.client.options(
            "/api/collect",
            headers={"Origin": "https://lumen.shop", "Access-Control-Request-Method": "POST"},
        )
        self.assertEqual(res.headers.get("access-control-allow-origin"), "https://lumen.shop")

    def test_production_rejects_open_collect(self):
        os.environ["SITELENS_ENV"] = "production"
        from sitelens.app import create_app

        client = TestClient(create_app())
        res = client.post("/api/collect", json={"name": "pageview", "path": "/"})
        self.assertEqual(res.status_code, 401)

    def test_daily_alert_posts_snapshot_once(self):
        owner = self.login()
        owner.put("/api/admin/settings", json={"alert_webhook": "https://hooks.example/sitelens"})
        posted: list[dict] = []

        from sitelens.alerts import tick
        from sitelens.models import utcnow

        with self.db_module.SessionLocal() as session:
            first = tick(session, now=utcnow(), poster=lambda url, payload: posted.append({"url": url, "payload": payload}))
            session.commit()
            second = tick(session, now=utcnow(), poster=lambda url, payload: posted.append({"url": url, "payload": payload}))
            session.commit()
        self.assertTrue(first["sent"])
        self.assertFalse(second["sent"])
        self.assertEqual(len(posted), 1)
        self.assertEqual(posted[0]["payload"]["type"], "sitelens.daily")
        self.assertIn("visitors", posted[0]["payload"])
        self.assertIn("orders", posted[0]["payload"])
        self.assertIn("geo_due", posted[0]["payload"])

    def test_visitors_summary_alias_and_orders_region_filter(self):
        owner = self.login()
        workbench = owner.get("/api/admin/workbench/summary").json()
        visitors = owner.get("/api/admin/visitors/summary").json()
        self.assertEqual(set(workbench), set(visitors))
        owner.post("/api/admin/orders", json={"title": "国内单", "amount": 10, "region": "cn"})
        listed = owner.get("/api/admin/orders?region=cn").json()
        self.assertEqual(listed["total"], 1)

    def test_tracker_puts_account_on_event_body(self):
        js = self.client.get("/tracker.js").text
        self.assertIn("body.account", js)
        self.assertIn("identify", js)


if __name__ == "__main__":
    unittest.main()
