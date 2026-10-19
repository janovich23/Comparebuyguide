"""Refresh approved eBay Browse API listings into a JSON feed.
Requires EBAY_CLIENT_ID and EBAY_CLIENT_SECRET in the execution environment.
Never commit API credentials. Run on a trusted scheduler and publish output to
products.json only after reviewing eBay API and affiliate program terms.
"""
import base64, json, os, sys, urllib.parse, urllib.request
from datetime import datetime, timezone

API = "https://api.ebay.com"
QUERIES = ["laptop", "mirrorless camera", "cordless power tool", "robot vacuum"]
CAMPAIGN_ID = "5339225508"

def request(url, headers=None, data=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    with urllib.request.urlopen(req, timeout=25) as response:
        return json.load(response)

def token():
    cid, secret = os.environ["EBAY_CLIENT_ID"], os.environ["EBAY_CLIENT_SECRET"]
    auth = base64.b64encode(f"{cid}:{secret}".encode()).decode()
    return request(API + "/identity/v1/oauth2/token",
        {"Authorization": "Basic " + auth,
         "Content-Type": "application/x-www-form-urlencoded"},
        urllib.parse.urlencode({"grant_type": "client_credentials",
                                "scope": "https://api.ebay.com/oauth/api_scope"}).encode())["access_token"]

def collect(access_token):
    items = []
    seen = set()
    for query in QUERIES:
        url = API + "/buy/browse/v1/item_summary/search?" + urllib.parse.urlencode(
            {"q": query, "limit": 25, "filter": "buyingOptions:{FIXED_PRICE}"})
        payload = request(url, {"Authorization": "Bearer " + access_token,
                                "X-EBAY-C-MARKETPLACE-ID": "EBAY_US"})
        for item in payload.get("itemSummaries", []):
            item_id = item.get("itemId")
            image = (item.get("image") or {}).get("imageUrl")
            price = item.get("price") or {}
            item_url = item.get("itemWebUrl")
            if not all((item_id, image, price.get("value"), item_url)) or item_id in seen:
                continue
            seen.add(item_id)
            items.append({"id": item_id, "title": item.get("title"),
                          "image": image, "price": price,
                          "condition": item.get("condition"),
                          "seller": (item.get("seller") or {}).get("username"),
                          "url": item_url, "category": query})
    return items

def main():
    if not all(os.getenv(k) for k in ("EBAY_CLIENT_ID", "EBAY_CLIENT_SECRET")):
        sys.exit("Missing eBay developer credentials; no feed generated.")
    result = {"updatedAt": datetime.now(timezone.utc).isoformat(),
              "source": "eBay Browse API", "items": collect(token())}
    with open("products.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"Generated {len(result['items'])} listings; affiliate URLs require separate verification.")

if __name__ == "__main__":
    main()
