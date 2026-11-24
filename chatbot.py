"""Small, deterministic supermarket assistant; no frontend or API dependencies."""
from decimal import Decimal, ROUND_HALF_UP
from difflib import get_close_matches
from pathlib import Path
import re
import pandas as pd
DATA_PATH = Path(__file__).with_name("products.csv")
WELCOME = ("Hello! Welcome to our supermarket. How can I help you today? "
           "You can ask me about product availability, prices, discounts, and offers.")
class DatasetError(ValueError):
    """A readable error for missing or invalid supermarket data."""
def final_price(product):
    """Round selling prices to paise using ordinary financial rounding."""
    return (Decimal(str(product["price"])) *
            (1 - Decimal(str(product["discount"])) / 100)).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP)
def load_products(path=DATA_PATH):
    """Read and validate the CSV once at startup."""
    try:
        frame = pd.read_csv(Path(path))
        required = {"product_id", "product_name", "category", "price", "stock", "discount", "unit"}
        if not required.issubset(frame.columns) or frame.empty:
            raise ValueError("The CSV must contain products and columns: " + ", ".join(sorted(required)))
        for column in ("product_id", "product_name", "category", "unit"):
            if frame[column].isna().any() or frame[column].astype(str).str.strip().eq("").any():
                raise ValueError(f"{column} must not be empty.")
            frame[column] = frame[column].astype(str).str.strip()
        if frame.product_id.duplicated().any() or frame.product_name.str.lower().duplicated().any():
            raise ValueError("Product IDs and names must be unique.")
        for column in ("price", "stock", "discount"):
            frame[column] = pd.to_numeric(frame[column], errors="raise")
            if frame[column].isna().any() or not frame[column].map(lambda n: float('-inf') < n < float('inf')).all():
                raise ValueError(f"{column} must contain finite numbers.")
            if (frame[column] < 0).any():
                raise ValueError(f"{column} cannot be negative.")
        if (frame.discount > 100).any() or (frame.stock % 1 != 0).any():
            raise ValueError("Discount must be 0–100 and stock must be a whole number.")
        return frame
    except (OSError, ValueError, pd.errors.ParserError) as exc:
        raise DatasetError(f"Cannot load product data: {exc}") from exc


def normalize(text):
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def variants(name):
    """Common English plurals, including multiword product names."""
    forms = {name}
    if name.endswith("ies"):
        forms.add(name[:-3] + "y")
    elif name.endswith("s") and not name.endswith("ss"):
        forms.add(name[:-1])
    else:
        forms.add(name + "s")
        forms.add(name + "es")
    if name.endswith("y"):
        forms.add(name[:-1] + "ies")
    return forms


class SupermarketChatbot:
    """Pass a mutable context dictionary; Streamlit stores it per session."""

    def __init__(self, path=DATA_PATH):
        self.products = load_products(path).to_dict("records")
        self.categories = sorted({p["category"] for p in self.products})

    def match(self, text, names):
        # Longest matches consume their spans: Orange Juice never becomes Orange.
        matches, occupied = [], set()
        for name in sorted(names, key=lambda n: -len(n)):
            for form in variants(normalize(name)):
                found = re.search(r"\b" + re.escape(form) + r"\b", text)
                if found and not occupied.intersection(range(*found.span())):
                    matches.append(name)
                    occupied.update(range(*found.span()))
                    break
        return matches

    def describe(self, product):
        price = f"₹{product['price']:g} / {product['unit']}"
        if product["discount"] > 0:
            price += f"; {product['discount']:g}% off → ₹{final_price(product):.2f}"
        return f"**{product['product_name']}** — {price}"

    def listing(self, products, heading):
        return heading + "\n\n" + "\n".join("- " + self.describe(p) for p in products) if products else "No available products match that request."

    def reply(self, message, context=None):
        context = context if context is not None else {}
        text = normalize(message)
        if not text:
            return "Please enter a product name or a supermarket question."
        names = [p["product_name"] for p in self.products]
        matched = self.match(text, names)
        categories = self.match(text, self.categories)
        if not matched and not categories:
            # A shared fragment such as "juice" needs a choice, not a guess.
            fragments = {word for word in text.split() if len(word) >= 4}
            partial = [name for name in names if fragments.intersection(normalize(name).split())]
            if len(partial) > 1:
                return "Which product do you mean: " + ", ".join(partial) + "?"
        # Correct a small typo only when one candidate is clearly best.
        if not matched and not categories:
            candidates = set()
            words = text.split()
            request_words = set("what which is are do does you have show me list all any the a an of on for in it its that this them those price prices cost much discount discounts discounted offer offers sale available availability stock product products alternatives under below between rupees please current today".split())
            for size in (1, 2, 3):
                for start in range(len(words) - size + 1):
                    phrase = " ".join(words[start:start + size])
                    if len(phrase) >= 4 and not request_words.intersection(phrase.split()):
                        close = get_close_matches(phrase, [normalize(n) for n in names], n=2, cutoff=0.84)
                        if len(close) == 1:
                            candidates.add(names[[normalize(n) for n in names].index(close[0])])
            if len(candidates) == 1:
                matched = list(candidates)
        if len(matched) > 1 or len(categories) > 1:
            return "Please ask about one product or category at a time: " + ", ".join(matched or categories) + "."
        product = next((p for p in self.products if matched and p["product_name"] == matched[0]), None)
        category = categories[0] if categories else None
        followup = bool(re.search(r"\b(it|its|that|this|them|those)\b", text))
        alternatives = bool(re.search(r"\b(alternative|alternatives|substitute|substitutes)\b", text))
        offers = bool(re.search(r"\b(discount|discounts|offer|offers|sale|discounted)\b", text))
        price = bool(re.search(r"\b(price|cost|much)\b", text))
        if not product and not category and (followup or alternatives):
            product = next((p for p in self.products if p["product_name"] == context.get("product")), None)
            category = context.get("category")
        if product:
            context.update(product=product["product_name"], category=product["category"])
        elif category:
            context.update(product=None, category=category)
        if offers and not product and not category and re.search(r"\b(?:on|for)\s+(?!sale\b)", text):
            return "Which product do you mean? I could not find that product in our demo catalogue."
        available = [p for p in self.products if p["stock"] > 0]
        if alternatives:
            if not category and not product:
                return "Which product or category would you like alternatives for?"
            category = product["category"] if product else category
            return self.listing([p for p in available if p["category"] == category and p != product], f"Available alternatives in {category}:")
        # Budgets use rounded final prices. Under/below are strictly less than.
        amount = r"(?:₹\s*|rs\.?\s*|inr\s*)?(\d+(?:\.\d+)?)"
        raw = message.lower()
        between = re.search(r"between\s*" + amount + r"\s*(?:rupees\s*)?and\s*" + amount, raw)
        upper = re.search(r"(?:under|below|less than)\s*" + amount, raw)
        if between or upper:
            low, high = (map(Decimal, between.groups()) if between else (Decimal("0"), Decimal(upper.group(1))))
            if low > high:
                return "Please put the smaller budget amount first."
            selected = [p for p in available if (not category or p["category"] == category)
                        and (not product or p == product) and low <= final_price(p)
                        and (final_price(p) <= high if between else final_price(p) < high)
                        and (not offers or p["discount"] > 0)]
            return self.listing(selected, "Products matching your budget:")
        if re.search(r"\b(under|below|between|budget)\b", text):
            return "Please specify a budget, such as 'snacks under 100' or 'between 50 and 200 rupees'."
        if product:
            if offers:
                if not product["discount"]:
                    return f"Currently, there is no discount on {product['product_name']}."
                suffix = " Currently out of stock; this offer is unavailable." if not product["stock"] else ""
                return self.describe(product) + suffix
            if price:
                return self.describe(product) + (" Currently out of stock." if not product["stock"] else "")
            if product["stock"] > 0:
                return f"Yes, {product['product_name']} is available. " + self.describe(product)
            return f"Sorry, {product['product_name']} is currently out of stock.\n\n" + self.listing(
                [p for p in available if p["category"] == product["category"]], f"Other {product['category']} products:")
        if followup and not category:
            return "Which product or category do you mean?"
        if offers:
            return self.listing([p for p in available if p["discount"] > 0 and (not category or p["category"] == category)],
                                f"Current offers in {category}:" if category else "Current supermarket offers:")
        if category:
            return self.listing([p for p in available if p["category"] == category], f"Available {category} products:")
        if re.search(r"\bcategor(?:y|ies)\b", text):
            return "Available categories: " + ", ".join(self.categories) + "."
        if text in {"hi", "hello", "hey", "good morning", "good evening"}:
            return WELCOME
        if text in {"check availability", "availability"}:
            return "Please enter the product name you would like to check."
        if price:
            return "Which product's price would you like? If you named a product, I could not find it in our demo catalogue."
        if re.search(r"\b(available|have|stock|buy|sell|product|products)\b", text):
            return "I could not find that product in our demo catalogue. Please check its name or browse categories."
        return "I can help with supermarket availability, prices, discounts, categories, alternatives, and budgets. Try 'Is milk available?'"
