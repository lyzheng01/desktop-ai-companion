from fastapi.testclient import TestClient

from backend.server import app
import backend.server as server_module


client = TestClient(app)


def test_points_topup_products_endpoint_returns_active_products(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "list_point_topup_products",
        lambda: [
            {
                "product_code": "points_pack_500",
                "product_name": "500 Points",
                "points_amount": 500,
                "price_fen": 500,
                "status": "active",
                "payload": {"badge": "starter"},
            },
            {
                "product_code": "points_pack_1100",
                "product_name": "1100 Points",
                "points_amount": 1100,
                "price_fen": 1000,
                "status": "active",
                "payload": {"badge": "bonus"},
            },
        ],
    )

    response = client.get("/points/topup-products")

    assert response.status_code == 200
    data = response.json()
    assert [item["product_code"] for item in data] == [
        "points_pack_500",
        "points_pack_1100",
    ]
    assert data[0]["points_amount"] == 500
    assert data[1]["price_fen"] == 1000


def test_create_point_topup_order_endpoint_returns_wechat_code_url(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )
    monkeypatch.setattr(
        server_module,
        "get_point_topup_product",
        lambda product_code: {
            "product_code": "points_pack_500",
            "product_name": "500 Points",
            "points_amount": 500,
            "price_fen": 500,
            "status": "active",
            "payload": {"badge": "starter"},
        },
    )
    monkeypatch.setattr(
        server_module,
        "create_point_topup_order",
        lambda user_id, product_code, pay_channel, points_amount=0, amount_fen=0: {
            "order_no": "DACP202606040001",
            "product_code": product_code,
            "amount_fen": amount_fen or 500,
            "status": "pending",
            "pay_channel": pay_channel,
        },
    )
    monkeypatch.setattr(
        server_module,
        "create_wechat_native_payment",
        lambda order_no, amount_fen, description: {
            "code_url": "weixin://wxpay/mock",
            "prepay_id": "mock-prepay-id",
        },
    )
    monkeypatch.setattr(
        server_module,
        "update_point_topup_order_provider_fields",
        lambda order_no, wechat_code_url, wechat_prepay_id: {
            "order_no": order_no,
            "product_code": "points_pack_500",
            "amount_fen": 500,
            "status": "pending",
            "pay_channel": "wechat_native",
            "wechat_code_url": wechat_code_url,
            "paid_at": None,
        },
    )
    monkeypatch.setattr(
        server_module,
        "build_point_topup_payment_page_url",
        lambda order_no, user_id: f"http://127.0.0.1:8080/payments/points/{order_no}?token=status-token-1",
    )

    response = client.post(
        "/points/topup-orders/wechat-native",
        json={"product_code": "points_pack_500"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_no"] == "DACP202606040001"
    assert data["product_code"] == "points_pack_500"
    assert data["amount_fen"] == 500
    assert data["code_url"] == "weixin://wxpay/mock"
    assert data["payment_page_url"] == "http://127.0.0.1:8080/payments/points/DACP202606040001?token=status-token-1"


def test_create_point_topup_order_endpoint_accepts_quantity_and_returns_wechat_code_url(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )
    monkeypatch.setattr(
        server_module,
        "create_point_topup_order",
        lambda user_id, product_code, pay_channel, points_amount=0, amount_fen=0: {
            "order_no": "DACP202606050009",
            "product_code": product_code,
            "amount_fen": amount_fen,
            "status": "pending",
            "pay_channel": pay_channel,
            "points_amount": points_amount,
        },
    )
    monkeypatch.setattr(
        server_module,
        "create_wechat_native_payment",
        lambda order_no, amount_fen, description: {
            "code_url": "weixin://wxpay/mock",
            "prepay_id": "mock-prepay-id",
        },
    )
    monkeypatch.setattr(
        server_module,
        "update_point_topup_order_provider_fields",
        lambda order_no, wechat_code_url, wechat_prepay_id: {
            "order_no": order_no,
            "product_code": "points_quantity_topup",
            "amount_fen": 300,
            "status": "pending",
            "pay_channel": "wechat_native",
            "wechat_code_url": wechat_code_url,
            "paid_at": None,
        },
    )
    monkeypatch.setattr(
        server_module,
        "build_point_topup_payment_page_url",
        lambda order_no, user_id: f"http://127.0.0.1:8080/payments/points/{order_no}?token=status-token-9",
    )

    response = client.post(
        "/points/topup-orders/wechat-native",
        json={"quantity": 3},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["order_no"] == "DACP202606050009"
    assert data["product_code"] == "points_quantity_topup"
    assert data["amount_fen"] == 300
    assert data["code_url"] == "weixin://wxpay/mock"


def test_render_wechat_qrcode_endpoint_returns_png():
    response = client.post(
        "/payments/wechat/qrcode",
        json={"code_url": "weixin://wxpay/mock-qr"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
    assert response.content.startswith(b"\x89PNG")


def test_wechat_notify_endpoint_marks_point_topup_order_paid_when_membership_order_is_missing(monkeypatch):
    monkeypatch.setattr(server_module, "ensure_business_ready", lambda: None)
    monkeypatch.setattr(
        server_module,
        "parse_wechat_payment_notification",
        lambda headers, body: {
            "status": "SUCCESS",
            "order_no": "DACP202606040001",
            "transaction_id": "wx_tx_001",
        },
    )
    monkeypatch.setattr(server_module, "store_payment_callback", lambda provider, event_type, payload: None)
    monkeypatch.setattr(server_module, "mark_order_paid", lambda order_no, transaction_id: None)
    monkeypatch.setattr(
        server_module,
        "mark_point_topup_order_paid",
        lambda order_no, transaction_id: {
            "order_no": order_no,
            "product_code": "points_pack_500",
            "status": "paid",
        },
    )

    response = client.post("/payments/wechat/notify", content="{}", headers={"Wechatpay-Signature": "x"})

    assert response.status_code == 200
    assert response.json()["code"] == "SUCCESS"


def test_redeem_points_endpoint_returns_updated_balance_and_entitlement(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )
    monkeypatch.setattr(
        server_module,
        "redeem_store_product",
        lambda user_id, product_code: {
            "points_balance": 700,
            "entitlement": {
                "entitlement_code": "music.world_is_mine",
                "entitlement_type": "permanent",
                "source_product_code": product_code,
                "status": "active",
                "expires_at": None,
                "payload": {"asset_key": "music/world-is-mine"},
            },
        },
    )

    response = client.post(
        "/points/redeem",
        json={"product_code": "music_item_world_is_mine_remote"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["points_balance"] == 700
    assert data["entitlement"]["source_product_code"] == "music_item_world_is_mine_remote"


def test_redeem_points_endpoint_returns_400_for_insufficient_balance(monkeypatch):
    monkeypatch.setattr(
        server_module,
        "get_current_user",
        lambda authorization: {"id": 101, "phone": "13800138000", "nickname": "owner", "avatar_url": None, "status": "active"},
    )

    def _raise_insufficient(user_id, product_code):
        raise ValueError("Insufficient points")

    monkeypatch.setattr(server_module, "redeem_store_product", _raise_insufficient)

    response = client.post(
        "/points/redeem",
        json={"product_code": "music_item_world_is_mine_remote"},
        headers={"Authorization": "Bearer access-token"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Insufficient points"
