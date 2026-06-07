import json

from backend.business_store import PLAN_DEFINITIONS


def test_membership_plan_definitions_use_1990_and_3990_pricing():
    plans = {item["plan_code"]: item for item in PLAN_DEFINITIONS}

    assert plans["vip_monthly"]["price_fen"] == 1990
    assert plans["svip_monthly"]["price_fen"] == 3990


def test_membership_plan_definitions_use_10_30_and_unlimited_daily_chat_quota():
    plans = {item["plan_code"]: item for item in PLAN_DEFINITIONS}

    free_benefits = json.loads(plans["free"]["benefits_json"])
    vip_benefits = json.loads(plans["vip_monthly"]["benefits_json"])
    svip_benefits = json.loads(plans["svip_monthly"]["benefits_json"])

    assert free_benefits["daily_message_quota"] == 10
    assert vip_benefits["daily_message_quota"] == 30
    assert svip_benefits["daily_message_quota"] == -1
