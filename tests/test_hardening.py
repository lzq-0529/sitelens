from __future__ import annotations

import os
import tempfile
import unittest
import warnings
from pathlib import Path

from fastapi.testclient import TestClient

from sitelens.detect import source_of
from sitelens.geo import score_item
from sitelens.siteconfig import DEFAULT_SITE


class HardeningTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SITELENS_DATA_DIR"] = self.tmp.name
        os.environ["SITELENS_DATABASE_URL"] = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        os.environ["SITELENS_GEO_TOKEN"] = "slgeo_hardening"
        os.environ.pop("SITELENS_COLLECT_TOKEN", None)
        os.environ.pop("SITELENS_ENV", None)
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

    def test_geo_reingest_same_query_is_not_500(self):
        headers = {"X-Geo-Token": "slgeo_hardening"}
        first = self.client.post(
            "/api/geo/ingest",
            headers=headers,
            json={"items": [{"platform": "perplexity", "query": "Q1", "answer": "A1", "sources": ["https://lumen.shop/"]}]},
        )
        self.client.post(
            "/api/geo/ingest",
            headers=headers,
            json={"items": [{"platform": "perplexity", "query": "Q2", "answer": "A2", "sources": ["https://lumen.shop/"]}]},
        )
        again = self.client.post(
            "/api/geo/ingest",
            headers=headers,
            json={"items": [{"platform": "perplexity", "query": "Q1", "answer": "A1-updated", "sources": ["https://lumen.shop/"]}]},
        )
        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(again.status_code, 200, again.text)

    def test_malformed_amounts_are_400(self):
        owner = self.login()
        for payload in (
            {"title": "T", "amount_cents": "abc"},
            {"title": "T", "amount_cents": []},
            {"title": "T", "amount": "inf"},
            {"title": "T", "amount_cents": 10**21},
        ):
            res = owner.post("/api/admin/orders", json=payload)
            self.assertEqual(res.status_code, 400, (payload, res.text))

    def test_geo_ingest_non_list_sources_is_not_500(self):
        owner = self.login()
        res = owner.post(
            "/api/admin/site/geo/ingest",
            json={"items": [{"platform": "deepseek", "query": "src-int", "answer": "a", "sources": 123}]},
        )
        self.assertEqual(res.status_code, 200, res.text)
        res = owner.post(
            "/api/admin/site/geo/ingest",
            json={"platform": "deepseek", "query": "src-int-2", "answer": "a", "sources": 123},
        )
        self.assertEqual(res.status_code, 200, res.text)

    def test_score_item_survives_bad_ipv6_and_inf_rank(self):
        scored = score_item("", "", ["http://[invalid-ipv6"], DEFAULT_SITE)
        self.assertFalse(scored["cited"])
        scored = score_item("", "", [{"url": "https://lumen.shop/", "rank": float("inf")}], DEFAULT_SITE)
        self.assertTrue(scored["cited"])
        self.assertEqual(scored["citations"][0]["rank"], 1)

    def test_negative_purchase_does_not_abort_collect_batch(self):
        res = self.client.post(
            "/api/collect",
            json=[
                {"name": "pageview", "visitor_id": "neg1", "user_agent": "Mozilla/5.0", "path": "/"},
                {"name": "purchase", "visitor_id": "neg1", "user_agent": "Mozilla/5.0", "props": {"amount": -10}},
            ],
        )
        self.assertEqual(res.status_code, 200, res.text)
        self.assertEqual(res.json()["accepted"], 2)
        owner = self.login()
        self.assertEqual(owner.get("/api/admin/orders").json()["total"], 0)

    def test_utc_event_stays_on_utc_day(self):
        res = self.client.post(
            "/api/collect",
            json={"name": "pageview", "visitor_id": "tz_vis", "user_agent": "Mozilla/5.0", "at": "2026-11-03T01:30:00Z"},
        )
        self.assertEqual(res.status_code, 200, res.text)
        owner = self.login()
        summary = owner.get("/api/admin/site/summary?days=7&scope=human&region=all").json()
        days = [row["day"] for row in summary["site"]["series"]]
        self.assertIn("2026-11-03", days)
        self.assertNotIn("2026-11-02", days)

    def test_source_of_unicode_utm_and_named_source(self):
        self.assertEqual(source_of("https://unknown-shop-domain.example/0000000000", "?utm_source=α"), "α")
        self.assertEqual(source_of("", "newsletter"), "newsletter")

    def test_source_taxonomy_covers_cn_and_overseas_platforms(self):
        self.assertEqual(source_of("https://www.zhihu.com/question/1", ""), "知乎")
        self.assertEqual(source_of("https://www.xiaohongshu.com/explore/1", ""), "小红书")
        self.assertEqual(source_of("https://www.reddit.com/r/shopify/comments/1", ""), "Reddit")
        self.assertEqual(source_of("https://www.producthunt.com/products/x", ""), "Product Hunt")
        self.assertEqual(source_of("https://news.ycombinator.com/item?id=1", ""), "Hacker News")
        self.assertEqual(source_of("https://www.linkedin.com/company/x", ""), "LinkedIn")
        self.assertEqual(source_of("", "?utm_source=producthunt"), "Product Hunt")
        self.assertEqual(source_of("", "?utm_source=zhihu_answer"), "知乎")
        self.assertEqual(source_of("https://chatgpt.com/share/1", ""), "ChatGPT")

    def test_live_previous_and_geo_share_of_voice(self):
        owner = self.login()
        for visitor, name in (("live-a", "pageview"), ("live-a", "add_to_cart"), ("live-b", "pageview")):
            res = owner.post("/api/collect", json={"name": name, "visitor_id": visitor, "path": "/", "user_agent": "Mozilla/5.0"})
            self.assertLess(res.status_code, 500)
        overview = owner.get("/api/admin/overview?days=28").json()
        self.assertIn("live", overview)
        self.assertGreaterEqual(overview["live"]["visitors"], 1)
        summary = owner.get("/api/admin/site/summary?days=28").json()
        self.assertIn("previous", summary)

    def test_mask_ip_hides_last_octet(self):
        from sitelens.analytics import mask_ip

        self.assertEqual(mask_ip("203.0.113.42"), "203.0.113.*")
        self.assertEqual(mask_ip(""), "")

    def test_order_region_aliases(self):
        owner = self.login()
        overseas = owner.post("/api/admin/orders", json={"title": "Overseas", "amount": 50, "region": "overseas"}).json()
        upper = owner.post("/api/admin/orders", json={"title": "INTL", "amount": 50, "region": "INTL"}).json()
        self.assertEqual(overseas["region"], "intl")
        self.assertEqual(upper["region"], "intl")

    def test_parse_http_status_rejects_infinity(self):
        from sitelens.analytics import parse_http_status

        self.assertEqual(parse_http_status(float("inf")), 200)
        self.assertEqual(parse_http_status("inf"), 200)
        self.assertEqual(parse_http_status(-1), 200)
        self.assertEqual(parse_http_status(404), 404)

    def test_webhook_parsers_tolerate_malformed_line_items(self):
        from sitelens.hooks import parse_shopify, parse_woocommerce

        self.assertIsNotNone(parse_shopify({"status": "paid", "line_items": 1, "total_price": "10"}))
        self.assertIsNotNone(parse_shopify({"status": "paid", "line_items": [None], "total_price": "10"}))
        self.assertIsNotNone(parse_shopify({"status": "paid", "line_items": {"": 0}, "total_price": "10"}))
        self.assertIsNotNone(parse_woocommerce({"status": "completed", "line_items": 1, "total": "10"}))
        self.assertIsNotNone(parse_woocommerce({"status": "completed", "line_items": [None], "total": "10"}))

    def test_webhook_hmac_non_ascii_is_401(self):
        from sitelens.hooks import _compare

        self.assertFalse(_compare("shp_sec", b"{}", "0" * 43 + "\x80"))
        owner = self.login()
        owner.put("/api/admin/settings", json={"shopify_secret": "shp_sec", "woo_secret": "woo_sec"})
        shopify = self.client.post(
            "/api/hooks/shopify",
            content=b'{"id":1}',
            headers=[(b"x-shopify-hmac-sha256", ("0" * 43 + "\x80").encode("latin-1"))],
        )
        woo = self.client.post(
            "/api/hooks/woocommerce",
            content=b'{"id":1}',
            headers=[(b"x-wc-webhook-signature", ("0" * 43 + "\x80").encode("latin-1"))],
        )
        self.assertEqual(shopify.status_code, 401, shopify.text)
        self.assertEqual(woo.status_code, 401, woo.text)

    def test_settings_reject_bad_lists_and_keep_midnight_hour(self):
        owner = self.login()
        inf = owner.put("/api/admin/settings", content=b'{"alert_hour":1e309}', headers={"content-type": "application/json"})
        self.assertEqual(inf.status_code, 200, inf.text)
        self.assertEqual(inf.json()["alert_hour"], 1)
        lists = owner.put("/api/admin/settings", json={"domains": 123, "cn_hosts": True})
        self.assertEqual(lists.status_code, 200, lists.text)
        self.assertEqual(lists.json()["domains"], [])
        midnight = owner.put("/api/admin/settings", json={"alert_hour": 0})
        self.assertEqual(midnight.status_code, 200, midnight.text)
        self.assertEqual(midnight.json()["alert_hour"], 0)

    def test_init_db_disposes_previous_engine(self):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always", ResourceWarning)
            self.db_module.init_db()
            import gc

            gc.collect()
            leaked = [item for item in caught if issubclass(item.category, ResourceWarning) and "unclosed database" in str(item.message)]
        self.assertEqual(leaked, [])
