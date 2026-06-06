from fastapi.testclient import TestClient

from backend.server import app
import backend.server as server_module


client = TestClient(app)


def test_store_products_endpoint_returns_subscription_products_only(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "list_membership_plans",
        lambda: [
            {
                "plan_code": "free",
                "plan_name": "Free",
                "price_fen": 0,
                "duration_days": 0,
                "tier": "free",
                "status": "active",
                "benefits": {"model_access_level": "free"},
            },
            {
                "plan_code": "vip_monthly",
                "plan_name": "VIP Monthly",
                "price_fen": 1990,
                "duration_days": 30,
                "tier": "vip",
                "status": "active",
                "benefits": {"model_access_level": "vip"},
            },
            {
                "plan_code": "svip_monthly",
                "plan_name": "SVIP Monthly",
                "price_fen": 3990,
                "duration_days": 30,
                "tier": "svip",
                "status": "active",
                "benefits": {"model_access_level": "svip"},
            },
        ],
    )

    response = client.get("/store/products")

    assert response.status_code == 200
    data = response.json()
    assert [item["plan_code"] for item in data] == [
        "vip_monthly",
        "svip_monthly",
    ]
    assert data[0]["price_fen"] == 1990
    assert data[0]["duration_days"] == 30
    assert data[0]["tier"] == "vip"
    assert data[1]["tier"] == "svip"
    assert data[1]["benefits"]["model_access_level"] == "svip"


def test_me_endpoint_returns_membership_points_and_entitlements(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {
            "id": 101,
            "phone": "13800138000",
            "nickname": "owner",
            "avatar_url": None,
            "status": "active",
        },
    )
    monkeypatch.setattr(
        server_module,
        "get_user_membership",
        lambda user_id: {
            "plan_code": "vip_monthly",
            "tier": "vip",
            "status": "active",
            "started_at": None,
            "expires_at": None,
            "benefits": {"model_access_level": "vip", "voice_access_level": "vip"},
        },
    )
    monkeypatch.setattr(server_module, "get_user_points_balance", lambda user_id: 1200)
    monkeypatch.setattr(
        server_module,
        "list_user_entitlements",
        lambda user_id: [
            {
                "entitlement_code": "music.world_is_mine",
                "entitlement_type": "permanent",
                "source_product_code": "music_item_world_is_mine_remote",
                "status": "active",
                "expires_at": None,
                "payload": {"asset_key": "music/world-is-mine"},
            },
        ],
    )

    response = client.get("/me", headers={"Authorization": "Bearer access-token"})

    assert response.status_code == 200
    data = response.json()
    assert data["membership"]["tier"] == "vip"
    assert data["points_balance"] == 1200
    assert [item["entitlement_code"] for item in data["entitlements"]] == [
        "music.world_is_mine",
    ]


def test_create_membership_order_endpoint_returns_payment_page_url(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )
    monkeypatch.setattr(
        server_module,
        "get_plan",
        lambda plan_code: {
            "plan_code": "vip_monthly",
            "plan_name": "VIP Monthly",
            "price_fen": 1990,
            "duration_days": 30,
            "status": "active",
            "tier": "vip",
            "benefits": {"model_access_level": "vip"},
        },
    )
    monkeypatch.setattr(
        server_module,
        "create_payment_order",
        lambda user_id, plan_code, pay_channel: {
            "order_no": "DAC202606050001",
            "plan_code": plan_code,
            "amount_fen": 1990,
            "status": "pending",
            "pay_channel": pay_channel,
        },
    )
    monkeypatch.setattr(
        server_module,
        "create_wechat_native_payment",
        lambda order_no, amount_fen, description: {
            "code_url": "weixin://wxpay/mock-membership",
            "prepay_id": "mock-membership-prepay",
        },
    )
    monkeypatch.setattr(
        server_module,
        "update_payment_order_provider_fields",
        lambda order_no, wechat_code_url, wechat_prepay_id: {
            "order_no": order_no,
            "plan_code": "vip_monthly",
            "amount_fen": 1990,
            "status": "pending",
            "pay_channel": "wechat_native",
            "wechat_code_url": wechat_code_url,
            "paid_at": None,
        },
    )
    monkeypatch.setattr(
        server_module,
        "build_membership_payment_page_url",
        lambda order_no, user_id: f"http://127.0.0.1:8080/payments/billing/{order_no}?token=billing-status-token-1",
    )

    response = client.post(
        "/billing/orders/wechat-native",
        json={"plan_code": "vip_monthly"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_no"] == "DAC202606050001"
    assert data["plan_code"] == "vip_monthly"
    assert data["amount_fen"] == 1990
    assert data["code_url"] == "weixin://wxpay/mock-membership"
    assert data["payment_page_url"] == "http://127.0.0.1:8080/payments/billing/DAC202606050001?token=billing-status-token-1"
