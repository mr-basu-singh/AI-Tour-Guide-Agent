import requests

# Country name -> ISO currency code (extend anytime)
COUNTRY_CURRENCY = {
    "india": "INR", "united states": "USD", "usa": "USD", "us": "USD",
    "united kingdom": "GBP", "uk": "GBP", "japan": "JPY",
    "south korea": "KRW", "korea": "KRW", "germany": "EUR", "france": "EUR",
    "italy": "EUR", "spain": "EUR", "canada": "CAD", "australia": "AUD",
    "singapore": "SGD", "uae": "AED", "thailand": "THB", "nepal": "NPR",
    "china": "CNY", "switzerland": "CHF",
}

CURRENCY_SYMBOL = {
    "INR": "₹", "USD": "$", "GBP": "£", "JPY": "¥", "EUR": "€", "KRW": "₩",
    "CAD": "C$", "AUD": "A$", "SGD": "S$", "AED": "AED ", "THB": "฿",
    "NPR": "Rs ", "CNY": "¥", "CHF": "CHF ",
}


def currency_for_country(country: str) -> str:
    """ISO currency code for a country name (defaults to USD if unknown)."""
    return COUNTRY_CURRENCY.get(country.strip().lower(), "USD")


def symbol_for(code: str) -> str:
    return CURRENCY_SYMBOL.get(code, code + " ")


def convert(amount: float, from_code: str, to_code: str):
    """Convert money using Frankfurter (free, no key). Returns None on failure."""
    if from_code == to_code:
        return amount
    try:
        resp = requests.get(
            "https://api.frankfurter.dev/v1/latest",
            params={"base": from_code, "symbols": to_code},
            timeout=10,
        )
        resp.raise_for_status()
        rate = resp.json().get("rates", {}).get(to_code)
        return round(amount * rate, 2) if rate else None
    except Exception:
        return None