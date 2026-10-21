"""Build a refreshed eBay listing feed using approved production Browse API access.

Configure EBAY_CLIENT_ID and EBAY_CLIENT_SECRET as GitHub Actions secrets.
Never put credentials in repository files or browser JavaScript.
Only run if your eBay API permissions and data-use terms allow this workflow.
"""
import base64
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

API = "https://api.ebay.com"
CAMPAIGN_ID = "5339225508"
QUERIES = {
    "Laptops": [
        "laptop", "macbook pro", "gaming laptop", "lenovo thinkpad",
        "dell xps laptop", "hp spectre laptop", "asus zenbook",
        "microsoft surface laptop", "chromebook",
    ],
    "Cameras": [
        "mirrorless camera", "sony camera", "canon eos camera",
        "nikon z camera", "fujifilm x camera", "gopro camera",
        "dji action camera", "camera lens",
    ],
    "Tools": [
        "milwaukee m18", "dewalt cordless tools", "makita cordless tools",
        "bosch power tools", "cordless impact wrench", "tool combo kit",
        "laser level", "table saw", "pressure washer",
    ],
    "Home": [
        "robot vacuum", "espresso machine", "portable power station",
        "air purifier", "stand mixer", "air fryer", "cordless vacuum",
        "dehumidifier", "home security camera", "electric lawn mower",
    ],
}
LIMIT_PER_QUERY = 50


def get_json(url, headers=None, body=None):
    req = urllib.request.Request(url, data=body, headers=headers or {})
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        detail = exc.read(1200).decode("utf-8", errors="replace")
        raise RuntimeError(f"eBay API HTTP {exc.code}: {detail}") from exc


def access_token():
    client_id = os.environ["EBAY_CLIENT_ID"]
    client_secret = os.environ["EBAY_CLIENT_SECRET"]
    basic = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
    body = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "scope": "https://api.ebay.com/oauth/api_scope",
    }).encode()
    return get_json(API + "/identity/v1/oauth2/token", {
        "Authorization": "Basic " + basic,
        "Content-Type": "application/x-www-form-urlencoded",
    }, body)["access_token"]


def collect(token):
    seen = set()
    output = []
    headers = {
        "Authorization": "Bearer " + token,
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        # eBay may return itemAffiliateWebUrl when the account is eligible.
        "X-EBAY-C-ENDUSERCTX": "affiliateCampaignId=" + CAMPAIGN_ID,
    }
    for category, queries in QUERIES.items():
        for query in queries:
            params = urllib.parse.urlencode({
                "q": query, "limit": LIMIT_PER_QUERY,
                "filter": "buyingOptions:{FIXED_PRICE}",
            })
            response = get_json(API + "/buy/browse/v1/item_summary/search?" + params, headers)
            for item in response.get("itemSummaries", []):
                item_id = item.get("itemId")
                price = item.get("price") or {}
                image = (item.get("image") or {}).get("imageUrl")
                affiliate_url = item.get("itemAffiliateWebUrl")
                if not (item_id and image and price.get("value") and affiliate_url):
                    # Do not publish untracked links as if they earn commissions.
                    continue
                if item_id in seen:
                    continue
                parsed = urllib.parse.urlparse(affiliate_url)
                if parsed.scheme != "https" or not (
                    parsed.hostname == "ebay.com" or parsed.hostname.endswith(".ebay.com")
                ):
                    continue
                seen.add(item_id)
                output.append({
                    "id": item_id,
                    "title": item.get("title") or "eBay listing",
                    "image": image,
                    "price": {"value": price["value"], "currency": price.get("currency", "USD")},
                    "condition": item.get("condition") or "See listing",
                    "seller": (item.get("seller") or {}).get("username") or "See listing",
                    "url": affiliate_url,
                    "category": category,
                })
    return output


def main():
    if not all(os.environ.get(name) for name in ("EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET")):
        sys.exit("Missing eBay production credentials; products.json unchanged.")
    listings = collect(access_token())
    if not listings:
        sys.exit("No verified affiliate listings returned; products.json unchanged.")
    result = {
        "updatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "eBay Browse API",
        "items": listings,
    }
    with open("products.json", "w", encoding="utf-8") as output:
        json.dump(result, output, indent=2, ensure_ascii=False)
        output.write("\n")
    print(f"Prepared {len(listings)} eBay affiliate listings.")


if __name__ == "__main__":
    main()
