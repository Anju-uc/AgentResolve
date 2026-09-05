from agent.simulator import execute_purchase, PurchaseBlockedError


def test_multicategory_catalog_supports_clothing_and_shoes():
    dress = execute_purchase("Buy a black dress size L for women")
    assert dress.merchant_snapshot.title == "Women Black Bodycon Dress"
    assert dress.merchant_snapshot.attributes["category"].advertised == "dress"

    shoes = execute_purchase("Buy Nike running shoes size 9")
    assert shoes.merchant_snapshot.title == "Nike Air Max Running Shoes"


def test_no_compliant_product_blocks_purchase():
    try:
        execute_purchase("Buy a black smartphone under $500")
    except PurchaseBlockedError as exc:
        assert exc.constraints.price_usd == 500.0
        assert exc.candidates
    else:
        raise AssertionError("Non-compliant purchase should be blocked")


def test_explicit_override_records_constraint_override_event():
    txn = execute_purchase("Buy a black smartphone under $500", allow_constraint_override=True)
    actions = [event["action"] for event in txn.lifecycle.event_log]
    assert "constraint_override" in actions
