import os
import random
import base64
import hashlib
import hmac
import json
import time

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def send_login_sms(phone: str, code: str) -> dict:
    provider = os.getenv("DESKTOP_AI_COMPANION_SMS_PROVIDER", "mock").strip().lower() or "mock"
    if provider == "tencent":
        return _send_tencent_sms(phone, code)
    if provider != "mock":
        raise NotImplementedError(f"Unsupported SMS provider: {provider}")

    print(f"[MOCK_SMS] phone={phone} code={code}")
    return {"provider": "mock", "debug_code": code}


def generate_sms_code() -> str:
    fixed = os.getenv("DESKTOP_AI_COMPANION_FIXED_SMS_CODE", "").strip()
    if fixed:
        return fixed
    return f"{random.randint(0, 999999):06d}"


def create_wechat_native_payment(order_no: str, amount_fen: int, description: str) -> dict:
    provider = os.getenv("DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER", "mock").strip().lower() or "mock"
    if provider == "wechat":
        return _create_wechat_native_payment(order_no, amount_fen, description)
    if provider != "mock":
        raise NotImplementedError(f"Unsupported WeChat Pay provider: {provider}")

    code_url = f"weixin://wxpay/bizpayurl/mock?pr={order_no}"
    return {
        "provider": "mock",
        "code_url": code_url,
        "prepay_id": f"mock_prepay_{order_no}",
        "description": description,
        "amount_fen": amount_fen,
    }


def parse_wechat_payment_notification(headers: dict[str, str], body: str) -> dict:
    provider = os.getenv("DESKTOP_AI_COMPANION_WECHAT_PAY_PROVIDER", "mock").strip().lower() or "mock"
    if provider == "wechat":
        return _parse_wechat_payment_notification(headers, body)
    if provider != "mock":
        raise NotImplementedError(f"Unsupported WeChat Pay provider: {provider}")
    payload = json.loads(body)
    return {
        "provider": "mock",
        "order_no": payload["order_no"],
        "transaction_id": payload.get("transaction_id"),
        "status": payload.get("status", "SUCCESS"),
        "raw": payload,
    }


def _require_env(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value


def _sha256_hex(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _hmac_sha256(key: bytes, message: str) -> bytes:
    return hmac.new(key, message.encode("utf-8"), hashlib.sha256).digest()


def _send_tencent_sms(phone: str, code: str) -> dict:
    secret_id = _require_env("TENCENTCLOUD_SECRET_ID")
    secret_key = _require_env("TENCENTCLOUD_SECRET_KEY")
    sdk_app_id = _require_env("TENCENTCLOUD_SMS_APP_ID")
    sign_name = _require_env("TENCENTCLOUD_SMS_SIGN_NAME")
    template_id = _require_env("TENCENTCLOUD_SMS_TEMPLATE_ID")
    endpoint = "sms.tencentcloudapi.com"
    service = "sms"
    host = endpoint
    action = "SendSms"
    version = "2021-01-11"
    region = os.getenv("TENCENTCLOUD_SMS_REGION", "ap-guangzhou")
    timestamp = int(time.time())
    date = time.strftime("%Y-%m-%d", time.gmtime(timestamp))
    payload = {
        "SmsSdkAppId": sdk_app_id,
        "SignName": sign_name,
        "TemplateId": template_id,
        "TemplateParamSet": [code, "5"],
        "PhoneNumberSet": [f"+86{phone}"],
    }
    payload_json = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    canonical_headers = f"content-type:application/json; charset=utf-8\nhost:{host}\nx-tc-action:{action.lower()}\n"
    signed_headers = "content-type;host;x-tc-action"
    canonical_request = "\n".join([
        "POST",
        "/",
        "",
        canonical_headers,
        signed_headers,
        _sha256_hex(payload_json.encode("utf-8")),
    ])
    credential_scope = f"{date}/{service}/tc3_request"
    string_to_sign = "\n".join([
        "TC3-HMAC-SHA256",
        str(timestamp),
        credential_scope,
        _sha256_hex(canonical_request.encode("utf-8")),
    ])
    secret_date = _hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
    secret_service = hmac.new(secret_date, service.encode("utf-8"), hashlib.sha256).digest()
    secret_signing = hmac.new(secret_service, b"tc3_request", hashlib.sha256).digest()
    signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()
    authorization = (
        f"TC3-HMAC-SHA256 Credential={secret_id}/{credential_scope}, "
        f"SignedHeaders={signed_headers}, Signature={signature}"
    )
    headers = {
        "Authorization": authorization,
        "Content-Type": "application/json; charset=utf-8",
        "Host": host,
        "X-TC-Action": action,
        "X-TC-Timestamp": str(timestamp),
        "X-TC-Version": version,
        "X-TC-Region": region,
    }
    response = httpx.post(f"https://{endpoint}", headers=headers, content=payload_json, timeout=15)
    response.raise_for_status()
    data = response.json()
    send_status = (((data.get("Response") or {}).get("SendStatusSet") or [{}])[0])
    if send_status.get("Code") != "Ok":
        raise RuntimeError(send_status.get("Message") or "Tencent SMS send failed")
    return {"provider": "tencent", "debug_code": None, "response": data}


def _load_private_key_from_env(env_name: str):
    pem = _require_env(env_name).replace("\\n", "\n").encode("utf-8")
    return serialization.load_pem_private_key(pem, password=None)


def _build_wechat_signature(method: str, canonical_url: str, timestamp: str, nonce: str, body: str) -> str:
    private_key = _load_private_key_from_env("WECHAT_PAY_PRIVATE_KEY_PEM")
    message = f"{method}\n{canonical_url}\n{timestamp}\n{nonce}\n{body}\n".encode("utf-8")
    signature = private_key.sign(message, padding.PKCS1v15(), hashes.SHA256())
    return base64.b64encode(signature).decode("utf-8")


def _create_wechat_native_payment(order_no: str, amount_fen: int, description: str) -> dict:
    mchid = _require_env("WECHAT_PAY_MCH_ID")
    appid = _require_env("WECHAT_PAY_APP_ID")
    serial_no = _require_env("WECHAT_PAY_SERIAL_NO")
    notify_url = _require_env("WECHAT_PAY_NOTIFY_URL")
    endpoint = os.getenv("WECHAT_PAY_API_BASE", "https://api.mch.weixin.qq.com").rstrip("/")
    nonce = os.urandom(16).hex()
    timestamp = str(int(time.time()))
    canonical_url = "/v3/pay/transactions/native"
    payload = {
        "appid": appid,
        "mchid": mchid,
        "description": description,
        "out_trade_no": order_no,
        "notify_url": notify_url,
        "amount": {"total": amount_fen, "currency": "CNY"},
    }
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    signature = _build_wechat_signature("POST", canonical_url, timestamp, nonce, body)
    authorization = (
        f'WECHATPAY2-SHA256-RSA2048 mchid="{mchid}",'
        f'serial_no="{serial_no}",nonce_str="{nonce}",timestamp="{timestamp}",signature="{signature}"'
    )
    headers = {
        "Authorization": authorization,
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "desktop-ai-companion/0.1",
    }
    response = httpx.post(f"{endpoint}{canonical_url}", headers=headers, content=body, timeout=20)
    response.raise_for_status()
    data = response.json()
    code_url = data.get("code_url")
    if not isinstance(code_url, str) or not code_url:
        raise RuntimeError("WeChat Pay native order response missing code_url")
    return {
        "provider": "wechat",
        "code_url": code_url,
        "prepay_id": data.get("prepay_id") or order_no,
        "description": description,
        "amount_fen": amount_fen,
        "response": data,
    }


def _verify_wechat_signature(headers: dict[str, str], body: str) -> None:
    signature = headers.get("Wechatpay-Signature") or headers.get("wechatpay-signature")
    nonce = headers.get("Wechatpay-Nonce") or headers.get("wechatpay-nonce")
    timestamp = headers.get("Wechatpay-Timestamp") or headers.get("wechatpay-timestamp")
    if not signature or not nonce or not timestamp:
        raise RuntimeError("Missing WeChat Pay callback signature headers")
    public_key_pem = _require_env("WECHAT_PAY_PLATFORM_PUBLIC_KEY_PEM").replace("\\n", "\n").encode("utf-8")
    public_key = serialization.load_pem_public_key(public_key_pem)
    message = f"{timestamp}\n{nonce}\n{body}\n".encode("utf-8")
    public_key.verify(base64.b64decode(signature), message, padding.PKCS1v15(), hashes.SHA256())


def _decrypt_wechat_resource(resource: dict) -> dict:
    api_v3_key = _require_env("WECHAT_PAY_API_V3_KEY").encode("utf-8")
    nonce = resource["nonce"]
    associated_data = resource.get("associated_data", "")
    ciphertext = resource["ciphertext"]
    aesgcm = AESGCM(api_v3_key)
    plaintext = aesgcm.decrypt(
        nonce.encode("utf-8"),
        base64.b64decode(ciphertext),
        associated_data.encode("utf-8"),
    )
    return json.loads(plaintext.decode("utf-8"))


def _parse_wechat_payment_notification(headers: dict[str, str], body: str) -> dict:
    _verify_wechat_signature(headers, body)
    payload = json.loads(body)
    resource = payload.get("resource")
    if not isinstance(resource, dict):
        raise RuntimeError("Invalid WeChat Pay callback resource")
    decrypted = _decrypt_wechat_resource(resource)
    return {
        "provider": "wechat",
        "order_no": decrypted["out_trade_no"],
        "transaction_id": decrypted.get("transaction_id"),
        "status": decrypted.get("trade_state", payload.get("event_type", "SUCCESS")),
        "raw": payload,
        "resource": decrypted,
    }
