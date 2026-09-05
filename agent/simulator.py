"""Deterministic shopping-agent simulator for realistic commerce transactions."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List

from app.models.transaction import (
    AgentDecision,
    AgentInterpretation,
    Constraints,
    Dispute,
    MerchantSnapshot,
    Transaction,
    UserRequest,
)
from app.models.lifecycle import (
    AuthorizationRecord,
    FulfillmentRecord,
    PaymentRecord,
    TransactionLifecycle,
)
from agent.execution_trace import build_event, derive_validated_fields
from app.engine.helpers import constraint_is_satisfied


class PurchaseBlockedError(Exception):
    """Raised when the agent cannot safely buy a non-compliant product."""

    def __init__(self, query: str, constraints: Constraints, candidates: List[Dict[str, Any]]):
        self.query = query
        self.constraints = constraints
        self.candidates = candidates
        super().__init__("No compliant product found; purchase blocked.")


# Controlled multi-category merchant catalog used by the shopping-agent simulator.
# Prices are canonical USD; the UI can display them in another currency.
CATALOG: List[Dict[str, Any]] = [
    # Phones
    {"item_id":"PHONE-S25-256","title":"Samsung Galaxy S25","category":"smartphone","brand":"Samsung","seller":"OfficialStore","price":799.0,"storage_gb":256,"ram_gb":12,"color":"Black","condition":"New","delivery_days":2,"tags":["android","5g"]},
    {"item_id":"PHONE-S24-128","title":"Samsung Galaxy S24","category":"smartphone","brand":"Samsung","seller":"OfficialStore","price":649.0,"storage_gb":128,"ram_gb":8,"color":"Black","condition":"New","delivery_days":2,"tags":["android","5g"]},
    {"item_id":"PHONE-I15-256","title":"Apple iPhone 15","category":"smartphone","brand":"Apple","seller":"OfficialStore","price":899.0,"storage_gb":256,"ram_gb":8,"color":"Blue","condition":"New","delivery_days":3,"tags":["ios","5g"]},
    # Laptops
    {"item_id":"LAP-DELL-16","title":"Dell Inspiron 14","category":"laptop","brand":"Dell","seller":"DellStore","price":749.0,"storage_gb":512,"ram_gb":16,"color":"Silver","condition":"New","delivery_days":3,"tags":["windows","ultrabook"]},
    {"item_id":"LAP-LEN-16","title":"Lenovo IdeaPad Slim 5","category":"laptop","brand":"Lenovo","seller":"LenovoStore","price":899.0,"storage_gb":1024,"ram_gb":16,"color":"Grey","condition":"New","delivery_days":4,"tags":["windows","ultrabook"]},
    {"item_id":"LAP-MAC-18","title":"MacBook Pro M3 Pro","category":"laptop","brand":"Apple","seller":"AppleStore","price":1999.0,"storage_gb":512,"ram_gb":18,"color":"Space Gray","condition":"New","delivery_days":4,"tags":["macos","m3 pro","14-inch"]},
    # Clothing
    {"item_id":"CLOTH-DRESS-01","title":"Women Midi Floral Dress","category":"dress","brand":"UrbanThread","seller":"UrbanThread","price":59.0,"color":"Blue","condition":"New","delivery_days":4,"tags":["women","midi","floral","casual"],"attributes":{"size":"M","gender":"women","fit":"regular","material":"cotton"}},
    {"item_id":"CLOTH-DRESS-02","title":"Women Black Bodycon Dress","category":"dress","brand":"StyleWorks","seller":"StyleWorks","price":72.0,"color":"Black","condition":"New","delivery_days":3,"tags":["women","bodycon","party"],"attributes":{"size":"L","gender":"women","fit":"slim","material":"polyester"}},
    {"item_id":"CLOTH-TSHIRT-01","title":"Men Classic Cotton T-Shirt","category":"tshirt","brand":"BasicsCo","seller":"BasicsCo","price":24.0,"color":"Black","condition":"New","delivery_days":3,"tags":["men","cotton","casual"],"attributes":{"size":"L","gender":"men","fit":"regular","material":"cotton"}},
    {"item_id":"CLOTH-JACKET-01","title":"Unisex Lightweight Jacket","category":"jacket","brand":"NorthPeak","seller":"NorthPeak","price":89.0,"color":"Black","condition":"New","delivery_days":5,"tags":["unisex","outerwear","water-resistant"],"attributes":{"size":"M","gender":"unisex","fit":"regular","material":"nylon"}},
    # Shoes
    {"item_id":"SHOE-NIKE-01","title":"Nike Air Max Running Shoes","category":"running shoes","brand":"Nike","seller":"NikeStore","price":129.0,"color":"Red","condition":"New","delivery_days":4,"tags":["running","sports"],"attributes":{"size":"9","gender":"unisex","material":"mesh"}},
    {"item_id":"SHOE-ADIDAS-01","title":"Adidas Ultraboost Running Shoes","category":"running shoes","brand":"Adidas","seller":"AdidasStore","price":149.0,"color":"Black","condition":"New","delivery_days":4,"tags":["running","sports"],"attributes":{"size":"10","gender":"unisex","material":"mesh"}},
    # Cameras / headphones / watches
    {"item_id":"CAM-SONY-A7","title":"Sony Alpha Mirrorless Camera","category":"camera","brand":"Sony","seller":"CameraHub","price":999.0,"storage_gb":128,"color":"Black","condition":"New","delivery_days":4,"tags":["mirrorless","photography"],"attributes":{"sensor":"full-frame","video":"4k"}},
    {"item_id":"AUDIO-SONY-XM5","title":"Sony WH-1000XM5 Headphones","category":"headphones","brand":"Sony","seller":"AudioStore","price":349.0,"color":"Black","condition":"New","delivery_days":2,"tags":["wireless","noise cancelling"],"attributes":{"connectivity":"bluetooth","noise_cancellation":True}},
    {"item_id":"WATCH-APPLE-10","title":"Apple Watch Series 10","category":"smartwatch","brand":"Apple","seller":"AppleStore","price":449.0,"storage_gb":64,"color":"Black","condition":"New","delivery_days":3,"tags":["wearable","fitness"],"attributes":{"case_size":"46mm","gender":"unisex"}},
    # Home
    {"item_id":"HOME-AIRFRY-01","title":"Philips Digital Air Fryer","category":"air fryer","brand":"Philips","seller":"HomeStore","price":149.0,"color":"White","condition":"New","delivery_days":3,"tags":["kitchen","appliance"],"attributes":{"capacity_l":6}},
    {"item_id":"HOME-CHAIR-01","title":"Ergonomic Office Chair","category":"office chair","brand":"WorkNest","seller":"OfficeStore","price":299.0,"color":"Black","condition":"New","delivery_days":6,"tags":["office","ergonomic"],"attributes":{"material":"mesh","adjustable":True}},
    {"item_id":"HOME-TV-55","title":"LG 55 inch OLED TV","category":"tv","brand":"LG","seller":"LGStore","price":1099.0,"color":"Black","condition":"New","delivery_days":5,"tags":["oled","smart tv"],"attributes":{"screen_size":"55-inch","resolution":"4k"}},
    {"item_id":"HOME-FRIDGE-300","title":"Samsung 300L Refrigerator","category":"refrigerator","brand":"Samsung","seller":"ApplianceStore","price":699.0,"color":"Silver","condition":"New","delivery_days":7,"tags":["kitchen","appliance"],"attributes":{"capacity_l":300}},
]


def _parse_query(query: str) -> Constraints:
    """Parse common shopping constraints while preserving unspecified fields."""
    text = query.lower()
    c = Constraints()

    price = re.search(r"(?:under|below|less than|at most|maximum|max|budget(?: of)?)\s*(?:₹|\$|€|£)?\s*([\d,]+)\s*(?:in\s*)?(?:inr|usd|eur|gbp|rupees?|rs\.?|dollars?|euros?|pounds?)?", text)
    if price:
        value = float(price.group(1).replace(",", ""))
        # The simulator uses USD as its canonical internal currency. These
        # static demo rates are display/simulation rates only and do not affect
        # forensic attribution.
        if re.search(r"(?:₹|\binr\b|rupees?|\brs\.?\b)", text):
            value *= 0.0119
        elif re.search(r"(?:€|\beur\b|euros?)", text):
            value *= 1.08
        elif re.search(r"(?:£|\bgbp\b|pounds?)", text):
            value *= 1.28
        c.price_usd = round(value, 2)
        c.price_usd_operator = "under"

    ram = re.search(r"(?:at least|minimum|with)\s*(\d+)\s*gb\s*ram", text)
    if ram:
        c.ram_gb = float(ram.group(1)); c.ram_gb_operator = "minimum"

    storage = re.search(r"(?:at least|minimum|with)\s*(\d+)\s*gb\s*storage", text)
    if storage:
        c.storage_gb = int(storage.group(1)); c.storage_gb_operator = "minimum"

    delivery = re.search(r"(?:within|in|under|at most)\s*(\d+)\s*(?:day|days)", text)
    if delivery:
        c.delivery_days = int(delivery.group(1)); c.delivery_days_operator = "at most"

    for color in ("black", "white", "blue", "red", "silver", "grey", "gray", "gold", "space gray"):
        if color in text:
            c.color = "Space Gray" if color == "space gray" else color.title()
            break

    for condition in ("new", "refurbished", "used"):
        if condition in text:
            c.condition = condition.title()
            break

    # Common arbitrary commerce attributes.
    brand = re.search(r"\b(?:from|by)\s+(apple|samsung|sony|dell|lenovo|nike|adidas|lg|philips)\b", text)
    if brand:
        c.custom_attributes["brand"] = brand.group(1).title()

    size = re.search(r"\bsize\s*([a-z]+|\d+(?:\.\d+)?)\b", text)
    if size:
        c.custom_attributes["size"] = size.group(1).upper() if size.group(1).isalpha() else size.group(1)

    gender = re.search(r"\b(women|woman|men|man|unisex)\b", text)
    if gender:
        g = gender.group(1)
        c.custom_attributes["gender"] = "women" if g in {"women", "woman"} else "men" if g in {"men", "man"} else "unisex"

    material = re.search(r"\b(cotton|wool|leather|nylon|polyester|mesh|linen)\b", text)
    if material:
        c.custom_attributes["material"] = material.group(1)

    category_phrases = [
        ("running shoes", "running shoes"), ("sneakers", "running shoes"),
        ("smartphone", "smartphone"), ("phone", "smartphone"),
        ("laptop", "laptop"), ("t-shirt", "tshirt"), ("tshirt", "tshirt"),
        ("dress", "dress"), ("jacket", "jacket"),
        ("headphones", "headphones"), ("smartwatch", "smartwatch"), ("watch", "smartwatch"),
        ("air fryer", "air fryer"), ("office chair", "office chair"), ("chair", "office chair"),
        ("television", "tv"), ("tv", "tv"),
        ("refrigerator", "refrigerator"), ("fridge", "refrigerator"), ("camera", "camera"),
    ]
    # Prefer longest phrases first and use word boundaries so "headphones"
    # never accidentally becomes a "phone" request.
    for phrase, category in sorted(category_phrases, key=lambda item: len(item[0]), reverse=True):
        if re.search(r"\b" + re.escape(phrase) + r"\b", text):
            c.custom_attributes["category"] = category
            break

    return c


def _candidate_score(product: Dict[str, Any], query: str) -> int:
    tokens = {t for t in re.findall(r"[a-z0-9]+", query.lower()) if len(t) > 2}
    searchable = " ".join([
        product.get("title", ""), product.get("category", ""), product.get("brand", ""),
        " ".join(product.get("tags", [])),
    ]).lower()
    return sum(1 for token in tokens if token in searchable)


def _matches(product: Dict[str, Any], constraints: Constraints) -> bool:
    """Return True only when every recorded hard constraint is satisfied."""
    standard = {
        "price_usd": product.get("price"),
        "ram_gb": product.get("ram_gb"),
        "storage_gb": product.get("storage_gb"),
        "color": product.get("color"),
        "seller": product.get("seller"),
        "delivery_days": product.get("delivery_days"),
        "condition": product.get("condition"),
    }

    for field, value in standard.items():
        target = getattr(constraints, field, None)
        if target is None:
            continue
        if value is None or not constraint_is_satisfied(value, constraints, field):
            return False

    for field, target in constraints.custom_attributes.items():
        expected = target.get("value") if isinstance(target, dict) else target
        operator = target.get("operator", "exactly") if isinstance(target, dict) else "exactly"

        actual = product.get(field)
        if actual is None and field != "category":
            actual = product.get("attributes", {}).get(field)
        if field == "category":
            actual = product.get("category")

        if actual is None:
            return False

        custom_constraint = Constraints(
            custom_attributes={
                field: {
                    "value": expected,
                    "operator": operator,
                }
            }
        )
        if not constraint_is_satisfied(actual, custom_constraint, field):
            return False

    return True


def _field_constraint_satisfied(
    product: Dict[str, Any],
    constraints: Constraints,
    field: str,
) -> bool:
    """
    Evaluate exactly one field in isolation.

    This is used only for validation evidence. It deliberately does not call
    _matches(), because _matches() evaluates the entire constraint set.
    """
    canonical = str(field).strip().lower()

    standard = {
        "price_usd": product.get("price"),
        "ram_gb": product.get("ram_gb"),
        "storage_gb": product.get("storage_gb"),
        "color": product.get("color"),
        "seller": product.get("seller"),
        "delivery_days": product.get("delivery_days"),
        "condition": product.get("condition"),
    }

    if canonical in standard:
        target = getattr(constraints, canonical, None)
        if target is None:
            return False

        actual = standard[canonical]
        if actual is None:
            return False

        return bool(
            constraint_is_satisfied(
                actual,
                constraints,
                canonical,
            )
        )

    custom = constraints.custom_attributes.get(field)
    if custom is None:
        return False

    expected = custom.get("value") if isinstance(custom, dict) else custom
    operator = custom.get("operator", "exactly") if isinstance(custom, dict) else "exactly"

    if field == "category":
        actual = product.get("category")
    else:
        actual = product.get(field)
        if actual is None:
            actual = product.get("attributes", {}).get(field)

    if actual is None:
        return False

    custom_constraint = Constraints(
        custom_attributes={
            field: {
                "value": expected,
                "operator": operator,
            }
        }
    )

    return bool(
        constraint_is_satisfied(
            actual,
            custom_constraint,
            field,
        )
    )


def execute_purchase(query: str, currency: str = "USD", allow_constraint_override: bool = False) -> Transaction:
    now = datetime.now(timezone.utc).replace(microsecond=0)
    constraints = _parse_query(query)
    ranked = sorted(CATALOG, key=lambda p: _candidate_score(p, query), reverse=True)
    candidates = [p for p in ranked if _candidate_score(p, query) > 0 or constraints.custom_attributes.get("category")]
    valid = [p for p in candidates if _matches(p, constraints)]

    if not valid and not allow_constraint_override:
        raise PurchaseBlockedError(query, constraints, candidates[:5])

    if valid:
        product = valid[0]
    else:
        # Explicitly user-authorized override: choose the best textual candidate.
        product = candidates[0] if candidates else CATALOG[0]

    events = []
    parent = None

    def ev(action: str, arguments: Dict[str, Any] | None = None, result: Dict[str, Any] | None = None, status: str = "RECORDED") -> None:
        nonlocal parent
        event = build_event(
            f"EVT-{len(events)+1:03d}", action, arguments or {}, result or {},
            timestamp=(now + timedelta(seconds=len(events))).isoformat(),
            parent_hash=parent, status=status,
        )
        events.append(event)
        parent = event.content_hash

    ev("parse_request", {"query": query}, {"constraint_count": sum(v is not None for k, v in constraints.model_dump().items() if not k.endswith("_operator") and k != "custom_attributes")})
    ev("search_catalog", {"query": query}, {"candidate_count": len(candidates), "categories": sorted({p["category"] for p in candidates})})

    # Each validation event evaluates ONLY the field named by the event.
    # This keeps the execution trace auditable at field level.
    for field in ("price_usd", "ram_gb", "storage_gb", "color", "delivery_days", "condition"):
        if getattr(constraints, field, None) is not None:
            passed = _field_constraint_satisfied(product, constraints, field)
            ev(
                "validate_constraint",
                {
                    "field": field,
                    "expected": getattr(constraints, field),
                },
                {
                    "field": field,
                    "passed": passed,
                },
                status="RECORDED" if passed else "FAILED",
            )

    for field, target in constraints.custom_attributes.items():
        expected = target.get("value") if isinstance(target, dict) else target
        passed = _field_constraint_satisfied(product, constraints, field)
        ev(
            "validate_constraint",
            {
                "field": field,
                "expected": expected,
            },
            {
                "field": field,
                "passed": passed,
            },
            status="RECORDED" if passed else "FAILED",
        )

    overridden = not valid
    if overridden:
        ev("constraint_override", {"constraints": constraints.model_dump(exclude_none=True)}, {"user_confirmed": True}, status="RECORDED")

    ev("authorize_purchase", {"amount": product["price"], "currency": "USD"}, {"status": "AUTHORIZED"})
    ev("checkout", {"item_id": product["item_id"], "category": product["category"]}, {"status": "CHECKOUT_ACCEPTED"})
    ev("payment_capture", {"amount": product["price"]}, {"status": "CAPTURED"})
    ev("order_created", {"item_id": product["item_id"]}, {"status": "CREATED"})

    attrs = dict(product.get("attributes", {}))
    attrs.update({"category": product["category"], "brand": product["brand"], "color": product.get("color")})

    snapshot = MerchantSnapshot(
        item_id=product["item_id"], title=product["title"], seller=product["seller"], seller_at_checkout=product["seller"],
        price=product["price"], price_at_checkout=product["price"], ram_gb=product.get("ram_gb"), ram_gb_actual=product.get("ram_gb"),
        storage_gb=product.get("storage_gb"), storage_gb_actual=product.get("storage_gb"), delivery_days=product["delivery_days"],
        delivery_days_actual=product["delivery_days"], specs=attrs, attributes={k:{"advertised":v,"checkout":v,"delivered":v} for k,v in attrs.items()},
    )

    validated_fields = derive_validated_fields(events)
    lifecycle = TransactionLifecycle(
        authorization=AuthorizationRecord(
            user_authorized=True, initiated_by_agent=True, consent_recorded=True,
            authorization_limit=constraints.price_usd, authorized_amount=product["price"], currency="USD",
            final_cart_approved=not overridden, authorization_scope="USER_REQUEST_CONSTRAINTS",
            timestamp=(now + timedelta(seconds=len(events)-3)).isoformat(),
        ),
        payment=PaymentRecord(status="CAPTURED", authorized_amount=product["price"], captured_amount=product["price"], currency="USD", timestamp=(now + timedelta(seconds=len(events)-2)).isoformat()),
        fulfillment=FulfillmentRecord(order_status="CREATED", shipment_status="PENDING", delivered=False),
        event_log=[e.model_dump() for e in events],
    )

    txn_id = f"AR-{now.strftime('%Y%m%d-%H%M%S')}-{product['item_id'].split('-')[-1]}"
    return Transaction(
        transaction_id=txn_id,
        timestamp=(now + timedelta(seconds=len(events))).isoformat(),
        user_request=UserRequest(raw_text=query, timestamp=now.isoformat(), explicit_constraints=constraints),
        agent_interpretation=AgentInterpretation(parsed_constraints=constraints, accessed_constraint_keys=[k for k,v in constraints.model_dump().items() if v is not None and not k.endswith("_operator") and k != "custom_attributes"], execution_trace=events),
        merchant_snapshot=snapshot,
        agent_decision=AgentDecision(
            selected_item_id=product["item_id"], purchased_price=product["price"], purchased_ram_gb=product.get("ram_gb"),
            purchased_seller=product["seller"], purchased_delivery_days=product["delivery_days"],
            validation_steps_performed=validated_fields, attributes=attrs,
        ),
        dispute=Dispute(disputed_field="price", user_claim="No dispute filed yet", dispute_timestamp=(now + timedelta(seconds=len(events)+1)).isoformat()),
        lifecycle=lifecycle,
    )
