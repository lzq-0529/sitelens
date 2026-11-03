from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient


class SiteLensTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        os.environ["SITELENS_DATA_DIR"] = self.tmp.name
        os.environ["SITELENS_DATABASE_URL"] = f"sqlite:///{Path(self.tmp.name) / 'test.db'}"
        os.environ.pop("SITELENS_GEO_TOKEN", None)
        from sitelens import db as db_module
        from sitelens.app import create_app
        from sitelens.auth import OWNER, create_user
        from sitelens.demo import seed_demo

        db_module.init_db()
        with db_module.SessionLocal() as session:
            create_user(session, "boss", "owner-password-1", role=OWNER, display_name="站长")
            session.commit()
        self.client = TestClient(create_app())
        self.db_module = db_module
        self.seed_demo = seed_demo

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def login(self, username: str = "boss", password: str = "owner-password-1") -> TestClient:
        client = TestClient(self.client.app)
        res = client.post("/api/admin/login", json={"username": username, "password": password})
        self.assertEqual(res.status_code, 200, res.text)
        return client

    def test_health_and_robots(self):
        self.assertEqual(self.client.get("/api/health").json()["ok"], "sitelens")
        self.assertIn("Disallow", self.client.get("/robots.txt").text)
        self.assertIn("window.sitelens", self.client.get("/tracker.js").text)

    def test_collect_funnel_and_overview(self):
        owner = self.login()
        for name in ("pageview", "view_item", "add_to_cart", "begin_checkout"):
            res = self.client.post(
                "/api/collect",
                json={"name": name, "visitor_id": "v1", "path": "/", "region": "cn", "user_agent": "Mozilla/5.0"},
            )
            self.assertEqual(res.status_code, 200, res.text)
        buy = self.client.post(
            "/api/collect",
            json={
                "name": "purchase",
                "visitor_id": "v1",
                "region": "cn",
                "user_agent": "Mozilla/5.0",
                "account": "buyer@example.com",
                "props": {"sku": "wool-throw", "title": "羊毛毯", "amount_cents": 29900, "order_id": "ord_1"},
            },
        )
        self.assertEqual(buy.status_code, 200, buy.text)
        summary = owner.get("/api/admin/site/summary?days=28&scope=human&region=all").json()
        self.assertEqual(summary["site"]["visitors"], 1)
        self.assertEqual(summary["site"]["order"], 1)
        labels = [step["label"] for step in summary["funnel"]]
        self.assertEqual(labels, ["浏览网站", "看商品", "加入购物车", "开始结账", "完成下单"])
        self.assertEqual(summary["funnel"][-1]["count"], 1)
        visitors = owner.get("/api/admin/site/visitors?identified=true").json()
        self.assertEqual(visitors["total"], 1)
        orders = owner.get("/api/admin/orders").json()
        self.assertEqual(orders["total"], 1)
        self.assertEqual(orders["data"][0]["title"], "羊毛毯")

    def test_bot_becomes_crawl(self):
        self.client.post("/api/collect", json={"name": "pageview", "path": "/", "user_agent": "Googlebot/2.1"})
        owner = self.login()
        search = owner.get("/api/admin/site/search").json()
        self.assertGreaterEqual(search["totals"]["hits"], 1)
        self.assertTrue(any(item["id"] == "google" or "google" in item["id"] for item in search["engines"]))

    def test_geo_weekly_tasks_and_grok_ingest(self):
        owner = self.login()
        geo = owner.get("/api/admin/site/geo").json()
        self.assertEqual(geo["summary"]["total_platforms"], 15)
        self.assertEqual(geo["schedule"], "weekly")
        token = geo["ingest_token"]
        self.assertTrue(token.startswith("slgeo_"))
        self.assertEqual(self.client.get("/api/geo/tasks").status_code, 401)
        tasks = self.client.get("/api/geo/tasks", headers={"X-Geo-Token": token}).json()
        self.assertEqual(len(tasks["all_platforms"]), 15)
        self.assertIn("grok", tasks["agents"])
        self.assertIn("muse", tasks["agents"])
        self.assertGreaterEqual(tasks["due_count"], 14)
        add = owner.post("/api/admin/site/geo/prompts", json={"action": "add", "region": "cn", "query": "自定义独立站问题？"}).json()
        self.assertIn("自定义独立站问题？", add["prompts"]["cn"])
        ingest = self.client.post(
            "/api/geo/ingest",
            headers={"X-Geo-Token": token},
            json={
                "agent": "muse",
                "items": [
                    {
                        "platform": "DeepSeek 网页",
                        "query": "流明好物 这个独立站靠谱吗？官网是哪一个？",
                        "answer": "官网是 lumen.shop，流明好物可以在独立站直接下单。",
                        "sources": [{"title": "官网", "url": "https://lumen.shop/", "cited": True}],
                    }
                ],
            },
        )
        self.assertEqual(ingest.status_code, 200, ingest.text)
        self.assertIn("deepseek", ingest.json()["updated_platforms"])
        self.assertGreaterEqual(ingest.json()["summary"]["owned_cited_count"], 1)
        after = owner.get("/api/admin/site/geo").json()
        by_plat = {item["id"]: item for item in after["platforms"]}
        self.assertTrue(by_plat["deepseek"]["tested"])
        self.assertEqual(by_plat["deepseek"]["best_rank"], 1)

    def test_orders_refund_and_audit(self):
        owner = self.login()
        created = owner.post("/api/admin/orders", json={"title": "手冲壶", "amount": "189", "channel": "Stripe", "customer": "Ada"}).json()
        self.assertEqual(created["status"], "paid")
        self.assertEqual(owner.get("/api/admin/orders/summary").json()["orders_d30"], 1)
        owner.post(f"/api/admin/orders/{created['id']}/refund")
        self.assertEqual(owner.get("/api/admin/orders").json()["data"][0]["status"], "refunded")
        self.assertGreaterEqual(owner.get("/api/admin/audit").json()["total"], 2)

    def test_viewer_cannot_write(self):
        owner = self.login()
        owner.post("/api/admin/users", json={"username": "look", "password": "viewer-pass-1", "role": "viewer"})
        viewer = self.login("look", "viewer-pass-1")
        self.assertEqual(viewer.post("/api/admin/orders", json={"title": "x", "amount": 1}).status_code, 403)
        self.assertEqual(viewer.get("/api/admin/site/summary").status_code, 200)

    def test_seed_demo_creates_independent_store_data(self):
        with self.db_module.SessionLocal() as session:
            self.seed_demo(session)
            session.commit()
        owner = self.login()
        summary = owner.get("/api/admin/site/summary?days=28").json()
        self.assertGreater(summary["site"]["visitors"], 20)
        self.assertGreater(summary["site"]["order"], 0)
        self.assertNotIn("立即体验", str(summary))
        settings = owner.get("/api/admin/settings").json()
        self.assertEqual(settings["brand"], "流明好物")


if __name__ == "__main__":
    unittest.main()
