"""Deterministic dummy data generators for the local e-commerce SQLite database."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import hashlib
import math
import random
from typing import Iterator


CATEGORIES: list[tuple[str, str]] = [
    (
        "Electronics",
        "Consumer electronics including headphones, chargers, and smart devices.",
    ),
    (
        "Home & Kitchen",
        "Kitchen tools, cookware, and home organization essentials.",
    ),
    (
        "Sports & Outdoors",
        "Fitness gear, outdoor equipment, and active lifestyle products.",
    ),
    (
        "Beauty & Personal Care",
        "Skincare, haircare, and personal grooming products.",
    ),
    (
        "Office Supplies",
        "Desk accessories, notebooks, and productivity tools.",
    ),
]

CATEGORY_BRANDS: dict[str, list[str]] = {
    "Electronics": ["AetherTech", "NovaByte", "PulseGear", "Circuitly"],
    "Home & Kitchen": ["Hearthline", "CulinaryNest", "BrightPantry", "FormaHome"],
    "Sports & Outdoors": ["TrailForge", "PeakMotion", "StrideLab", "AlpineKit"],
    "Beauty & Personal Care": ["LuminaSkin", "VelvetRoot", "PureAura", "GlowTheory"],
    "Office Supplies": ["Deskora", "Paperlane", "FocusCraft", "InkHarbor"],
}

PRODUCT_ADJECTIVES: dict[str, list[str]] = {
    "Electronics": [
        "Wireless",
        "Portable",
        "Smart",
        "Compact",
        "Noise-Canceling",
        "Fast-Charge",
        "Ultra-Slim",
        "Pro",
        "Magnetic",
        "Rechargeable",
    ],
    "Home & Kitchen": [
        "Non-Stick",
        "Stainless",
        "Insulated",
        "Ceramic",
        "Stackable",
        "Collapsible",
        "Ergonomic",
        "Premium",
        "Bamboo",
        "Multi-Use",
    ],
    "Sports & Outdoors": [
        "Lightweight",
        "All-Weather",
        "Breathable",
        "Impact",
        "Trail",
        "Adjustable",
        "Carbon",
        "Folding",
        "High-Grip",
        "Performance",
    ],
    "Beauty & Personal Care": [
        "Hydrating",
        "Matte",
        "Vitamin-C",
        "Fragrance-Free",
        "Nourishing",
        "SPF",
        "Soothing",
        "Daily",
        "Deep-Clean",
        "Repair",
    ],
    "Office Supplies": [
        "Ruled",
        "Wireless",
        "Recycled",
        "Magnetic",
        "Ergonomic",
        "Refillable",
        "Desktop",
        "Portable",
        "Color-Coded",
        "Heavy-Duty",
    ],
}

PRODUCT_NOUNS: dict[str, list[str]] = {
    "Electronics": [
        "Earbuds",
        "Power Bank",
        "USB Hub",
        "Bluetooth Speaker",
        "Webcam",
        "Phone Stand",
        "LED Desk Lamp",
        "Smart Plug",
        "Cable Organizer",
        "Wireless Charger",
        "Keyboard",
        "Mouse",
        "Tablet Sleeve",
        "Streaming Mic",
        "HDMI Adapter",
        "Smart Scale",
        "Fitness Tracker Band",
        "Action Camera Mount",
        "Portable SSD Case",
        "Noise Monitor",
        "AR Glasses Case",
        "VR Controller Grip",
        "Docking Station",
        "Ring Light",
        "Smart Thermostat Hub",
    ],
    "Home & Kitchen": [
        "Chef Knife",
        "Cutting Board",
        "Mixing Bowl Set",
        "Coffee Grinder",
        "French Press",
        "Air Fryer Liner",
        "Spice Rack",
        "Food Storage Set",
        "Silicone Spatula",
        "Tea Kettle",
        "Can Opener",
        "Measuring Cup Set",
        "Salad Spinner",
        "Immersion Blender",
        "Toaster Tongs",
        "Dish Drying Rack",
        "Oven Mitt Pair",
        "Pantry Label Kit",
        "Water Filter Pitcher",
        "Cast Iron Skillet",
        "Soup Ladle",
        "Bento Lunch Box",
        "Herb Scissors",
        "Electric Kettle",
        "Reusable Straw Set",
    ],
    "Sports & Outdoors": [
        "Yoga Mat",
        "Resistance Bands",
        "Jump Rope",
        "Camping Lantern",
        "Hiking Poles",
        "Water Bottle",
        "Daypack",
        "Foam Roller",
        "Bike Phone Mount",
        "Running Belt",
        "Sleeping Bag Stuff Sack",
        "Trail Gloves",
        "Picnic Blanket",
        "Kayak Dry Bag",
        "Climbing Chalk Bag",
        "Fitness Dumbbell Pair",
        "Soccer Training Cones",
        "Tennis Grip Tape",
        "Golf Alignment Stick",
        "Swim Goggles",
        "Ski Wax Kit",
        "Fishing Tackle Box",
        "Climbing Carabiner Set",
        "Camping Cook Set",
        "Outdoor First Aid Kit",
    ],
    "Beauty & Personal Care": [
        "Face Cleanser",
        "Moisturizer",
        "Serum",
        "Sunscreen Lotion",
        "Lip Balm",
        "Shampoo",
        "Conditioner",
        "Body Wash",
        "Face Mask Pack",
        "Eye Cream",
        "Hair Oil",
        "Beard Grooming Kit",
        "Nail Care Set",
        "Makeup Remover Wipes",
        "Exfoliating Scrub",
        "Hand Cream",
        "Body Lotion",
        "Deodorant Stick",
        "Facial Toner",
        "Hair Styling Cream",
        "Cotton Pad Pack",
        "Travel Toiletry Kit",
        "Scalp Treatment",
        "Cuticle Oil",
        "Bath Bomb Set",
    ],
    "Office Supplies": [
        "Notebook",
        "Ballpoint Pen Set",
        "Mechanical Pencil",
        "Sticky Notes",
        "Desk Organizer",
        "Stapler",
        "Paper Clip Box",
        "Binder Clips",
        "Whiteboard Markers",
        "File Folder Pack",
        "Desk Calendar",
        "Mouse Pad",
        "Cable Management Tray",
        "Label Maker Tape",
        "Highlighter Set",
        "Index Cards",
        "Document Tray",
        "Planner Inserts",
        "Push Pin Pack",
        "Envelope Pack",
        "Desk Lamp Bulb",
        "USB Flash Drive Sleeve",
        "Laptop Stand Riser",
        "Ergonomic Wrist Rest",
        "Clipboard",
    ],
}

US_LOCATIONS: list[tuple[str, str]] = [
    ("Seattle", "WA"),
    ("Portland", "OR"),
    ("San Francisco", "CA"),
    ("Los Angeles", "CA"),
    ("San Diego", "CA"),
    ("Phoenix", "AZ"),
    ("Denver", "CO"),
    ("Austin", "TX"),
    ("Dallas", "TX"),
    ("Houston", "TX"),
    ("Chicago", "IL"),
    ("Minneapolis", "MN"),
    ("Detroit", "MI"),
    ("Columbus", "OH"),
    ("Atlanta", "GA"),
    ("Miami", "FL"),
    ("Tampa", "FL"),
    ("Charlotte", "NC"),
    ("Raleigh", "NC"),
    ("Nashville", "TN"),
    ("Boston", "MA"),
    ("New York", "NY"),
    ("Philadelphia", "PA"),
    ("Washington", "DC"),
    ("Baltimore", "MD"),
]

FIRST_NAMES = [
    "Ava",
    "Liam",
    "Noah",
    "Emma",
    "Olivia",
    "Mason",
    "Sophia",
    "Ethan",
    "Isabella",
    "Lucas",
    "Mia",
    "James",
    "Amelia",
    "Benjamin",
    "Harper",
    "Henry",
    "Evelyn",
    "Alexander",
    "Abigail",
    "Michael",
    "Emily",
    "Daniel",
    "Ella",
    "Matthew",
    "Scarlett",
    "Samuel",
    "Grace",
    "David",
    "Chloe",
    "Joseph",
]

LAST_NAMES = [
    "Anderson",
    "Brown",
    "Chen",
    "Davis",
    "Edwards",
    "Foster",
    "Garcia",
    "Harris",
    "Ivanov",
    "Johnson",
    "Kim",
    "Lopez",
    "Martinez",
    "Nguyen",
    "Owen",
    "Patel",
    "Quinn",
    "Rivera",
    "Smith",
    "Taylor",
    "Ueda",
    "Vargas",
    "Williams",
    "Xu",
    "Young",
    "Zhang",
    "Bennett",
    "Coleman",
    "Diaz",
    "Ellis",
]

# Fulfillment lifecycle statuses used across sample order history.
ORDER_STATUSES = [
    "ordered",
    "cancelled",
    "shipped",
    "delivered",
]

# Weighted toward fulfilled orders so conversion and fulfillment analytics are useful.
# delivered = actually fulfilled end state; shipped is in-transit fulfilled progress.
ORDER_STATUS_WEIGHTS = [0.10, 0.08, 0.22, 0.60]

# Statuses that count as successful demand for engagement/conversion correlation.
DEMAND_ORDER_STATUSES = frozenset({"ordered", "shipped", "delivered"})
FULFILLED_ORDER_STATUSES = frozenset({"delivered"})

PAYMENT_METHODS = [
    "credit_card",
    "debit_card",
    "paypal",
    "apple_pay",
    "gift_card",
]

PAYMENT_METHOD_WEIGHTS = [0.48, 0.18, 0.18, 0.12, 0.04]


@dataclass(frozen=True)
class CategoryRecord:
    """Category row payload."""

    name: str
    description: str


@dataclass(frozen=True)
class ProductRecord:
    """Product row payload."""

    category_name: str
    sku: str
    name: str
    description: str
    brand: str
    unit_price: float
    cost_price: float
    stock_quantity: int
    is_active: int
    created_at: str
    updated_at: str


@dataclass(frozen=True)
class CustomerRecord:
    """Customer row payload."""

    email: str
    first_name: str
    last_name: str
    city: str
    state: str
    country: str
    signup_date: str
    is_active: int


@dataclass(frozen=True)
class OrderItemRecord:
    """Order line-item payload before order totals are finalized."""

    product_sku: str
    quantity: int
    unit_price: float
    line_total: float


@dataclass(frozen=True)
class OrderRecord:
    """Order header and line items."""

    customer_email: str
    order_number: str
    order_date: str
    status: str
    shipping_amount: float
    tax_amount: float
    discount_amount: float
    total_amount: float
    payment_method: str
    shipping_city: str
    shipping_state: str
    shipping_country: str
    items: tuple[OrderItemRecord, ...]


@dataclass(frozen=True)
class ProductEngagementRecord:
    """Daily product click and dwell-time engagement payload."""

    product_sku: str
    engagement_date: str
    click_count: int
    view_sessions: int
    time_spent_seconds: int


def build_rng(seed: int) -> random.Random:
    """Create a deterministic RNG for reproducible seed data."""
    return random.Random(seed)


def _stable_hash_int(*parts: str) -> int:
    """Create a stable non-negative integer from string parts."""
    digest = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(digest[:12], 16)


def _format_timestamp(value: datetime) -> str:
    """Format datetimes as SQLite-friendly UTC-like strings."""
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_date(value: date) -> str:
    """Format dates as ISO strings."""
    return value.isoformat()


def generate_categories() -> list[CategoryRecord]:
    """Return the fixed product category catalog."""
    return [CategoryRecord(name=name, description=description) for name, description in CATEGORIES]


def generate_products(
    rng: random.Random,
    *,
    products_per_category: int = 20,
    catalog_start: date | None = None,
) -> list[ProductRecord]:
    """Generate products across all categories."""
    if products_per_category < 1:
        raise ValueError("products_per_category must be at least 1")

    start = catalog_start or date.today().replace(year=date.today().year - 3)
    products: list[ProductRecord] = []
    used_names: set[str] = set()

    for category_name, _ in CATEGORIES:
        adjectives = PRODUCT_ADJECTIVES[category_name]
        nouns = PRODUCT_NOUNS[category_name]
        brands = CATEGORY_BRANDS[category_name]
        combo_pool = [(adj, noun) for adj in adjectives for noun in nouns]
        rng.shuffle(combo_pool)

        created_count = 0
        combo_index = 0
        while created_count < products_per_category:
            if combo_index >= len(combo_pool):
                # Fall back to numbered variants if the adjective/noun pool is exhausted.
                adj = rng.choice(adjectives)
                noun = rng.choice(nouns)
                product_name = f"{adj} {noun} {created_count + 1}"
            else:
                adj, noun = combo_pool[combo_index]
                combo_index += 1
                product_name = f"{adj} {noun}"

            if product_name in used_names:
                product_name = f"{product_name} {created_count + 1}"
            used_names.add(product_name)

            brand = brands[created_count % len(brands)]
            sku_token = _stable_hash_int(category_name, product_name, brand) % 10_000_000
            sku = f"{category_name[:3].upper()}-{sku_token:07d}"

            base_price = {
                "Electronics": rng.uniform(19.99, 249.99),
                "Home & Kitchen": rng.uniform(9.99, 129.99),
                "Sports & Outdoors": rng.uniform(12.99, 179.99),
                "Beauty & Personal Care": rng.uniform(6.99, 79.99),
                "Office Supplies": rng.uniform(2.99, 59.99),
            }[category_name]
            unit_price = round(base_price, 2)
            margin = rng.uniform(0.28, 0.55)
            cost_price = round(unit_price * (1.0 - margin), 2)
            stock_quantity = rng.randint(5, 500)
            is_active = 1 if rng.random() > 0.05 else 0

            created_offset_days = rng.randint(0, 700)
            created_at_dt = datetime.combine(start, datetime.min.time()) + timedelta(
                days=created_offset_days,
                hours=rng.randint(8, 20),
                minutes=rng.randint(0, 59),
            )
            updated_at_dt = created_at_dt + timedelta(days=rng.randint(0, 400))
            if updated_at_dt.date() > date.today():
                updated_at_dt = datetime.combine(date.today(), created_at_dt.time())

            products.append(
                ProductRecord(
                    category_name=category_name,
                    sku=sku,
                    name=product_name,
                    description=(
                        f"{product_name} from {brand} in the {category_name} category. "
                        f"Designed for everyday use with reliable quality and simple setup."
                    ),
                    brand=brand,
                    unit_price=unit_price,
                    cost_price=cost_price,
                    stock_quantity=stock_quantity,
                    is_active=is_active,
                    created_at=_format_timestamp(created_at_dt),
                    updated_at=_format_timestamp(updated_at_dt),
                )
            )
            created_count += 1

    return products


def generate_customers(
    rng: random.Random,
    *,
    customer_count: int = 120,
    history_start: date | None = None,
) -> list[CustomerRecord]:
    """Generate a customer directory spanning the order history window."""
    if customer_count < 1:
        raise ValueError("customer_count must be at least 1")

    start = history_start or (date.today() - timedelta(days=365 * 2 + 30))
    customers: list[CustomerRecord] = []
    used_emails: set[str] = set()

    for index in range(customer_count):
        first_name = FIRST_NAMES[index % len(FIRST_NAMES)]
        last_name = LAST_NAMES[(index * 3) % len(LAST_NAMES)]
        city, state = US_LOCATIONS[index % len(US_LOCATIONS)]

        local_part = f"{first_name}.{last_name}.{index + 1}".lower()
        email = f"{local_part}@example.com"
        if email in used_emails:
            email = f"{local_part}.{rng.randint(100, 999)}@example.com"
        used_emails.add(email)

        signup_offset = rng.randint(0, max((date.today() - start).days, 1))
        signup_date = start + timedelta(days=signup_offset)
        is_active = 1 if rng.random() > 0.08 else 0

        customers.append(
            CustomerRecord(
                email=email,
                first_name=first_name,
                last_name=last_name,
                city=city,
                state=state,
                country="US",
                signup_date=_format_date(signup_date),
                is_active=is_active,
            )
        )

    return customers


def _choose_order_date(
    rng: random.Random,
    *,
    history_start: date,
    history_end: date,
    customer_signup: date,
) -> date:
    """Pick an order date on or after customer signup within the history window."""
    earliest = max(history_start, customer_signup)
    if earliest > history_end:
        return history_end

    total_days = (history_end - earliest).days
    if total_days <= 0:
        return earliest

    # Mild seasonality: more orders near month-end and Q4.
    day_offset = rng.randint(0, total_days)
    candidate = earliest + timedelta(days=day_offset)
    month = candidate.month
    if month in {11, 12} and rng.random() < 0.35:
        boost = rng.randint(0, min(20, total_days))
        candidate = earliest + timedelta(days=min(total_days, day_offset + boost))
    return candidate


def generate_orders(
    rng: random.Random,
    *,
    customers: list[CustomerRecord],
    products: list[ProductRecord],
    order_count: int = 1800,
    history_years: int = 2,
) -> list[OrderRecord]:
    """Generate multi-year order history with line items."""
    if order_count < 1:
        raise ValueError("order_count must be at least 1")
    if history_years < 2:
        raise ValueError("history_years must be at least 2")
    if not customers:
        raise ValueError("customers cannot be empty")
    if not products:
        raise ValueError("products cannot be empty")

    history_end = date.today()
    history_start = history_end - timedelta(days=365 * history_years)
    active_products = [product for product in products if product.is_active] or products
    orders: list[OrderRecord] = []

    for index in range(order_count):
        customer = rng.choice(customers)
        signup_date = date.fromisoformat(customer.signup_date)
        order_day = _choose_order_date(
            rng,
            history_start=history_start,
            history_end=history_end,
            customer_signup=signup_date,
        )
        order_dt = datetime.combine(
            order_day,
            datetime.min.time(),
        ) + timedelta(hours=rng.randint(7, 22), minutes=rng.randint(0, 59), seconds=rng.randint(0, 59))

        item_count = rng.choices([1, 2, 3, 4, 5], weights=[0.42, 0.28, 0.18, 0.08, 0.04], k=1)[0]
        selected_products = rng.sample(active_products, k=min(item_count, len(active_products)))
        items: list[OrderItemRecord] = []
        subtotal = 0.0

        for product in selected_products:
            quantity = rng.choices([1, 2, 3, 4], weights=[0.62, 0.24, 0.10, 0.04], k=1)[0]
            # Small historical price drift around the current catalog price.
            drift = rng.uniform(-0.08, 0.12)
            unit_price = round(max(0.99, product.unit_price * (1.0 + drift)), 2)
            line_total = round(unit_price * quantity, 2)
            subtotal += line_total
            items.append(
                OrderItemRecord(
                    product_sku=product.sku,
                    quantity=quantity,
                    unit_price=unit_price,
                    line_total=line_total,
                )
            )

        shipping_amount = 0.0 if subtotal >= 75 else round(rng.choice([4.99, 6.99, 9.99]), 2)
        discount_amount = 0.0
        if rng.random() < 0.18:
            discount_amount = round(min(subtotal * rng.uniform(0.05, 0.20), subtotal * 0.25), 2)

        taxable = max(subtotal - discount_amount, 0.0)
        tax_amount = round(taxable * rng.uniform(0.05, 0.1025), 2)
        total_amount = round(taxable + tax_amount + shipping_amount, 2)

        status = rng.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS, k=1)[0]
        payment_method = rng.choices(PAYMENT_METHODS, weights=PAYMENT_METHOD_WEIGHTS, k=1)[0]
        shipping_city, shipping_state = rng.choice(US_LOCATIONS)

        order_number = f"ORD-{order_dt.strftime('%Y%m%d')}-{index + 1:05d}"
        orders.append(
            OrderRecord(
                customer_email=customer.email,
                order_number=order_number,
                order_date=_format_timestamp(order_dt),
                status=status,
                shipping_amount=shipping_amount,
                tax_amount=tax_amount,
                discount_amount=discount_amount,
                total_amount=total_amount,
                payment_method=payment_method,
                shipping_city=shipping_city,
                shipping_state=shipping_state,
                shipping_country="US",
                items=tuple(items),
            )
        )

    orders.sort(key=lambda order: order.order_date)
    return orders


def _units_ordered_by_product_day(
    orders: list[OrderRecord],
) -> dict[tuple[str, str], int]:
    """Aggregate ordered units by product SKU and calendar day.

    Cancelled orders are excluded so engagement correlates with real demand.
    """
    units: dict[tuple[str, str], int] = {}
    for order in orders:
        if order.status not in DEMAND_ORDER_STATUSES:
            continue
        day_key = order.order_date[:10]
        for item in order.items:
            key = (item.product_sku, day_key)
            units[key] = units.get(key, 0) + item.quantity
    return units


def generate_product_engagement(
    rng: random.Random,
    *,
    products: list[ProductRecord],
    orders: list[OrderRecord],
    history_years: int = 2,
) -> list[ProductEngagementRecord]:
    """Generate daily clicks and dwell time correlated with order demand.

    For each product/day with demand, click volume and time spent scale with
    ordered units so downstream conversion-rate analysis is meaningful. Light
    browse-only noise is added on other days so zero-order days still appear.
    """
    if not products:
        raise ValueError("products cannot be empty")
    if history_years < 2:
        raise ValueError("history_years must be at least 2")

    history_end = date.today()
    history_start = history_end - timedelta(days=365 * history_years)
    demand = _units_ordered_by_product_day(orders)
    engagement_rows: list[ProductEngagementRecord] = []

    # Stable popularity bias so some catalog items attract more browse traffic.
    popularity: dict[str, float] = {
        product.sku: 0.55 + (_stable_hash_int(product.sku, "popularity") % 100) / 100.0
        for product in products
    }

    current = history_start
    while current <= history_end:
        day_key = _format_date(current)
        is_weekend = current.weekday() >= 5
        weekend_boost = 1.15 if is_weekend else 1.0

        for product in products:
            ordered_units = demand.get((product.sku, day_key), 0)
            product_bias = popularity[product.sku]

            if ordered_units > 0:
                # Higher demand days get more product-page traffic and dwell time.
                base_clicks = int(round(ordered_units * rng.uniform(8.0, 18.0) * product_bias))
                noise_clicks = rng.randint(2, 12)
                click_count = max(ordered_units + 1, base_clicks + noise_clicks)

                view_sessions = max(
                    1,
                    int(round(click_count * rng.uniform(0.55, 0.85))),
                )
                # Average session length grows mildly with demand (seconds).
                avg_seconds = rng.uniform(45.0, 180.0) + ordered_units * rng.uniform(20.0, 90.0)
                time_spent_seconds = max(
                    view_sessions * 15,
                    int(round(view_sessions * avg_seconds * weekend_boost)),
                )
            else:
                # Sparse browse-only activity so inactive SKUs still have a trail.
                browse_chance = 0.04 * product_bias
                if product.is_active == 0:
                    browse_chance *= 0.35
                if rng.random() > browse_chance:
                    continue

                click_count = rng.randint(1, max(2, int(6 * product_bias)))
                view_sessions = max(1, int(round(click_count * rng.uniform(0.5, 0.9))))
                time_spent_seconds = int(
                    round(view_sessions * rng.uniform(20.0, 95.0) * weekend_boost)
                )

            engagement_rows.append(
                ProductEngagementRecord(
                    product_sku=product.sku,
                    engagement_date=day_key,
                    click_count=click_count,
                    view_sessions=view_sessions,
                    time_spent_seconds=time_spent_seconds,
                )
            )

        current += timedelta(days=1)

    engagement_rows.sort(key=lambda row: (row.engagement_date, row.product_sku))
    return engagement_rows


def summarize_seed(
    *,
    categories: list[CategoryRecord],
    products: list[ProductRecord],
    customers: list[CustomerRecord],
    orders: list[OrderRecord],
    engagement: list[ProductEngagementRecord] | None = None,
) -> dict[str, object]:
    """Build a compact summary for logging and verification."""
    order_items = sum(len(order.items) for order in orders)
    order_dates = [datetime.strptime(order.order_date, "%Y-%m-%d %H:%M:%S").date() for order in orders]
    products_by_category: dict[str, int] = {}
    for product in products:
        products_by_category[product.category_name] = products_by_category.get(product.category_name, 0) + 1

    status_counts: dict[str, int] = {status: 0 for status in ORDER_STATUSES}
    for order in orders:
        status_counts[order.status] = status_counts.get(order.status, 0) + 1

    fulfilled_orders = status_counts.get("delivered", 0)
    non_cancelled = sum(count for status, count in status_counts.items() if status != "cancelled")
    fulfillment_rate = round(fulfilled_orders / non_cancelled, 4) if non_cancelled else 0.0

    engagement_rows = engagement or []
    total_clicks = sum(row.click_count for row in engagement_rows)
    total_time_seconds = sum(row.time_spent_seconds for row in engagement_rows)
    total_time_hours = round(total_time_seconds / 3600.0, 2)

    return {
        "categories": len(categories),
        "products": len(products),
        "products_per_category_min": min(products_by_category.values()) if products_by_category else 0,
        "customers": len(customers),
        "orders": len(orders),
        "order_items": order_items,
        "order_status_counts": status_counts,
        "fulfilled_orders": fulfilled_orders,
        "fulfillment_rate": fulfillment_rate,
        "order_date_min": min(order_dates).isoformat() if order_dates else None,
        "order_date_max": max(order_dates).isoformat() if order_dates else None,
        "order_span_days": (max(order_dates) - min(order_dates)).days if order_dates else 0,
        "revenue_estimate": round(
            sum(
                order.total_amount
                for order in orders
                if order.status in DEMAND_ORDER_STATUSES
            ),
            2,
        ),
        "product_engagement_rows": len(engagement_rows),
        "total_clicks": total_clicks,
        "total_time_spent_hours": total_time_hours,
    }


def monthly_order_buckets(orders: list[OrderRecord]) -> Iterator[tuple[str, int, float]]:
    """Yield monthly order counts and revenue for quick analytics smoke checks."""
    buckets: dict[str, list[float]] = {}
    for order in orders:
        month_key = order.order_date[:7]
        buckets.setdefault(month_key, []).append(order.total_amount)

    for month_key in sorted(buckets):
        totals = buckets[month_key]
        yield month_key, len(totals), round(sum(totals), 2)


def expected_history_days(history_years: int) -> int:
    """Approximate day span for the configured history window."""
    return int(math.ceil(365 * history_years))
