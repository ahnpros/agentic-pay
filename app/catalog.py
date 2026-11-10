"""Mock product catalog for the Agentic Pay demo.

Prices are in USD to match the PayPal Sandbox Orders API without extra
conversion steps at payment time. The user-facing budget may be entered in
KRW in the UI; it is converted to USD at a fixed, clearly labeled demo rate
before the budget guard runs (see README: "Currency handling").
"""

PRODUCTS = [
    {
        "id": "chips-sea-salt",
        "name": "Sea Salt Potato Chips (12-pack)",
        "category": "chips",
        "price_usd": 14.99,
        "rating": 4.7,
    },
    {
        "id": "cookies-choc-chip",
        "name": "Chocolate Chip Cookies (24 ct)",
        "category": "cookies",
        "price_usd": 12.49,
        "rating": 4.8,
    },
    {
        "id": "sparkling-water",
        "name": "Sparkling Water Variety Pack (12 cans)",
        "category": "drinks",
        "price_usd": 11.99,
        "rating": 4.5,
    },
    {
        "id": "cold-brew",
        "name": "Cold Brew Coffee Cans (8-pack)",
        "category": "drinks",
        "price_usd": 18.99,
        "rating": 4.6,
    },
    {
        "id": "trail-mix",
        "name": "Trail Mix (2 lb bag)",
        "category": "nuts",
        "price_usd": 16.99,
        "rating": 4.4,
    },
    {
        "id": "gummy-bears",
        "name": "Gummy Bears Share Bag (2 lb)",
        "category": "candy",
        "price_usd": 9.99,
        "rating": 4.3,
    },
    {
        "id": "cheese-crackers",
        "name": "Cheese Crackers (20-pack)",
        "category": "crackers",
        "price_usd": 13.49,
        "rating": 4.6,
    },
    {
        "id": "dark-chocolate",
        "name": "Dark Chocolate Bars (10-pack)",
        "category": "candy",
        "price_usd": 15.99,
        "rating": 4.9,
    },
    {
        "id": "roasted-almonds",
        "name": "Roasted Almonds (1.5 lb)",
        "category": "nuts",
        "price_usd": 17.49,
        "rating": 4.5,
    },
]
