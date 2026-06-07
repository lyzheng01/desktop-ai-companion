import json

from backend import provider_services


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return self._payload


def test_send_login_sms_tencent_uses_single_template_param(monkeypatch):
    captured = {}

    monkeypatch.setenv("DESKTOP_AI_COMPANION_SMS_PROVIDER", "tencent")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_ID", "AKID_TEST")
    monkeypatch.setenv("TENCENTCLOUD_SECRET_KEY", "SECRET_TEST")
    monkeypatch.setenv("TENCENTCLOUD_SMS_APP_ID", "1401134331")
    monkeypatch.setenv("TENCENTCLOUD_SMS_SIGN_NAME", "合肥凌烨科技")
    monkeypatch.setenv("TENCENTCLOUD_SMS_TEMPLATE_ID", "2655911")
    monkeypatch.setattr(provider_services.time, "time", lambda: 1700000000)
    monkeypatch.setattr(provider_services.time, "strftime", lambda fmt, ts: "2023-11-14")

    def fake_post(url: str, headers: dict, content: str, timeout: int):
        captured["url"] = url
        captured["headers"] = headers
        captured["payload"] = json.loads(content)
        captured["timeout"] = timeout
        return _FakeResponse(
            {
                "Response": {
                    "SendStatusSet": [
                        {
                            "Code": "Ok",
                            "Message": "send success",
                        }
                    ]
                }
            }
        )

    monkeypatch.setattr(provider_services.httpx, "post", fake_post)

    result = provider_services.send_login_sms("18326081058", "123456")

    assert result["provider"] == "tencent"
    assert captured["url"] == "https://sms.tencentcloudapi.com"
    assert captured["payload"]["PhoneNumberSet"] == ["+8618326081058"]
    assert captured["payload"]["TemplateParamSet"] == ["123456"]
