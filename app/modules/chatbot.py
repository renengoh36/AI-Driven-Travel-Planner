from __future__ import annotations
import re
import string

try:
    import nltk  # type: ignore
    from nltk.tokenize import word_tokenize as _wt  # type: ignore
    from nltk.corpus import stopwords as _sw_corpus  # type: ignore

    # Loads NLTK tokenisation and English stop words.
    def _load_nltk() -> tuple:
        """Download NLTK data if missing; return (tokeniser_fn, stopword_set)."""
        for pkg in ("punkt_tab", "punkt", "stopwords"):
            try:
                nltk.data.find(
                    "tokenizers/punkt" if "punkt" in pkg else f"corpora/{pkg}"
                )
            except LookupError:
                nltk.download(pkg, quiet=True)
        sw = set(_sw_corpus.words("english"))
        return _wt, sw

    _TOKENIZE, _SW_SET = _load_nltk()
    _NLTK_OK = True

except Exception:  # pragma: no cover
    _TOKENIZE, _SW_SET, _NLTK_OK = None, None, False


# BUILT-IN STOP-WORD FALLBACK 
_FALLBACK_SW = {
    "i", "me", "my", "we", "our", "you", "your", "he", "him", "his", "she",
    "her", "it", "its", "they", "them", "their", "what", "which", "who",
    "this", "that", "these", "those", "am", "is", "are", "was", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "shall", "should", "may", "might", "must", "can", "could",
    "not", "no", "nor", "a", "an", "the", "and", "but", "or", "so",
    "as", "at", "by", "for", "in", "into", "of", "on", "to", "up", "with",
    "about", "above", "after", "before", "between", "out", "over", "then",
    "there", "here", "when", "where", "why", "how", "all", "any", "each",
    "few", "more", "most", "some", "such", "very", "just", "too", "also",
    "than", "same", "own", "well", "even", "still", "back", "way", "now",
}

# Returns the available stop-word set.
def _stopwords() -> set:
    return _SW_SET if _SW_SET is not None else _FALLBACK_SW


INTEREST_OPTIONS = ["nature", "food", "history", "shopping", "adventure", "relaxation"]
BUDGET_OPTIONS   = ["budget", "mid-range", "luxury"]
WEATHER_OPTIONS  = ["warm", "cold", "moderate"]

#  KNOWN CITIES 
KNOWN_CITIES: set[str] = {
    "tokyo", "paris", "kuala lumpur", "bali", "new york city", "new york",
    "rome", "bangkok", "london", "osaka", "sydney",
    "singapore", "dubai", "hong kong", "barcelona", "amsterdam",
    "berlin", "prague", "istanbul", "seoul", "beijing", "shanghai",
    "mumbai", "delhi", "toronto", "vancouver", "chicago", "los angeles",
    "san francisco", "miami", "rio de janeiro", "cape town",
    "zurich", "vienna", "lisbon", "athens", "venice", "florence",
    "milan", "madrid", "mexico city", "cancun", "phuket",
    "taipei", "manila", "jakarta", "penang", "hanoi", "ho chi minh",
    "colombo", "kathmandu", "maldives", "zanzibar", "muscat",
    "nairobi", "accra", "casablanca", "marrakech", "cairo",
    "reykjavik", "stockholm", "oslo", "copenhagen", "helsinki",
    "warsaw", "budapest", "bucharest", "sofia", "zagreb",
}

CITY_ALIASES: dict[str, str] = {
    "kl":    "Kuala Lumpur",
    "nyc":   "New York City",
    "ny":    "New York City",
    "new york": "New York City",
    "bkk":   "Bangkok",
    "hcmc":  "Ho Chi Minh City",
    "hk":    "Hong Kong",
    "sg":    "Singapore",
}

# VOCABULARY MAPS 
INTEREST_SYNONYMS: dict[str, list[str]] = {
    "nature":      ["nature", "outdoor", "outdoors", "park", "wildlife", "hiking",
                    "trekking", "forest", "mountain", "lake", "river", "scenic",
                    "garden", "waterfall", "greenery"],
    "food":        ["food", "eat", "eating", "restaurant", "cuisine", "culinary",
                    "foodie", "dining", "taste", "drink", "street food",
                    "gastronomy", "cafe", "coffee", "dessert", "bakery"],
    "history":     ["history", "historical", "museum", "culture", "cultural",
                    "heritage", "architecture", "monument", "ancient", "temple",
                    "church", "palace", "ruins", "artifact", "landmark"],
    "shopping":    ["shopping", "shop", "mall", "market", "buy", "souvenir",
                    "boutique", "store", "retail", "flea", "night market", "bazaar"],
    "adventure":   ["adventure", "extreme", "sport", "thrill", "thrilling",
                    "exciting", "activity", "zipline", "bungee", "skydive",
                    "climb", "kayak", "surf", "adrenaline"],
    "relaxation":  ["relax", "relaxation", "spa", "beach", "rest", "calm",
                    "peaceful", "chill", "unwind", "retreat", "leisure",
                    "yoga", "meditate", "pool", "wellness", "massage"],
}

BUDGET_SYNONYMS: dict[str, list[str]] = {
    "luxury":    ["luxury", "luxurious", "premium", "expensive", "high-end",
                  "5-star", "five-star", "lavish", "splurge", "upscale",
                  "fancy", "first class", "vip"],
    "mid-range": ["mid-range", "midrange", "mid range", "mid", "moderate",
                  "medium", "standard", "reasonable", "average", "normal"],
    "budget":    ["budget travel", "budget trip", "cheap", "affordable",
                  "economical", "low-cost", "inexpensive", "frugal",
                  "backpacker", "low budget", "thrifty", "save money"],
}

WEATHER_SYNONYMS: dict[str, list[str]] = {
    "warm":     ["warm", "hot", "sunny", "tropical", "heat", "summer", "humid"],
    "cold":     ["cold", "cool", "winter", "snow", "snowy", "chilly", "freezing", "icy"],
    "moderate": ["moderate", "mild", "temperate", "spring", "autumn", "fall"],
}

# Intent keyword sets
_GREETING  = {"hi", "hello", "hey", "greetings", "howdy", "morning", "afternoon",
               "evening", "sup", "yo", "hiya", "hai", "helo"}
_BYE       = {"bye", "goodbye", "farewell", "ciao", "later", "see you", "take care"}
_HELP      = {"help", "assist", "support", "capabilities", "commands",
               "guide", "instruction", "tutorial"}
_GEN_VERB  = {"generate", "create", "make", "plan", "build", "draft",
               "suggest", "give", "need", "want"}
_ITIN_NOUN = {"itinerary", "plan", "schedule", "trip", "route", "agenda", "journey"}
_VIEW_VERB = {"show", "view", "see", "display", "check", "look", "get",
               "fetch", "retrieve", "open"}
_DEST_VERB = {"go", "travel", "visit", "fly", "heading", "going",
               "explore", "destination", "vacation", "holiday"}
_RATE_KW   = {"rate", "rating", "stars", "feedback", "review", "score"}
_SUGGEST_V = {"suggest", "recommend", "find", "show", "tell", "list", "give"}
_SUGGEST_CTX = {"any", "good", "best", "top", "near", "nearby", "around", "where"}


# Tokenises text and removes stop words and non-alphabetic tokens.
def tokenise(text: str) -> list[str]:
    text = text.lower().strip()

    if _TOKENIZE:
        try:
            raw_tokens = _TOKENIZE(text)
        except Exception:
            raw_tokens = text.translate(str.maketrans("", "", string.punctuation)).split()
    else:
        raw_tokens = text.translate(str.maketrans("", "", string.punctuation)).split()

    sw = _stopwords()
    return [t for t in raw_tokens if t.isalpha() and t not in sw]


# Identifies the user's preferred budget type from the text.
def extract_destination(text: str) -> str | None:
    lower = text.lower()

    for alias, canonical in CITY_ALIASES.items():
        if re.search(r"\b" + re.escape(alias) + r"\b", lower):
            return canonical

    for city in sorted(KNOWN_CITIES, key=len, reverse=True):
        if re.search(r"\b" + re.escape(city) + r"\b", lower):
            return city.title()

    return None

 # Identifies the user's preferred budget type from the text.
def extract_budget_type(tokens: list[str], text: str) -> str | None:
    lower = text.lower()
    for btype, synonyms in BUDGET_SYNONYMS.items():
        for syn in synonyms:
            if re.search(r"\b" + re.escape(syn) + r"\b", lower):
                return btype
    return None

# Extracts the number of travel days from the text.
def extract_days(text: str) -> int | None:
    m = re.search(r"\b(\d+)\s*(?:day|days|night|nights)\b", text.lower())
    if m:
        n = int(m.group(1))
        return n if 1 <= n <= 30 else None
    return None

 # Identifies travel interests mentioned in the text.
def extract_interests(tokens: list[str]) -> list[str]:
    found: list[str] = []
    token_set = set(tokens)
    joined = " ".join(tokens)  # for multi-word synonyms
    for interest, synonyms in INTEREST_SYNONYMS.items():
        for syn in synonyms:
            words = syn.split()
            hit = (
                syn in token_set          # single word in token set
                if len(words) == 1
                else syn in joined        # multi-word phrase in joined tokens
            )
            if hit:
                if interest not in found:
                    found.append(interest)
                break
    return found

# Identifies the user's preferred weather condition.
def extract_weather(tokens: list[str], text: str) -> str | None:
    """Return 'warm', 'cold', or 'moderate' if found in text."""
    lower = text.lower()
    for wtype, synonyms in WEATHER_SYNONYMS.items():
        for syn in synonyms:
            if re.search(r"\b" + re.escape(syn) + r"\b", lower):
                return wtype
    return None

# Extracts the place or attraction type requested by the user.
def extract_place_keyword(text: str) -> str | None:
    lower = text.lower()
    patterns = [
        r"(?:suggest|recommend|find\s+me?|show\s+me?|give\s+me?)\s+(?:a\s+|an\s+|some\s+|any\s+|me\s+a\s+|me\s+some\s+)?(.+?)(?:\s+(?:in|at|near|around|for)\s+|$)",
        r"(?:any\s+good|best|top(?:\s+\d+)?)\s+(.+?)(?:\s+(?:in|at|near|around)\s+|$)",
        r"where\s+(?:can\s+i\s+)?(?:find\s+|get\s+|eat\s+)?(.+?)(?:\s+(?:in|at|near)\s+|$)",
    ]
    for p in patterns:
        m = re.search(p, lower)
        if m:
            kw = m.group(1).strip().rstrip("?.,!")
            # Remove trailing stop words
            kw = re.sub(r"\s+(in|at|near|around|please|here).*$", "", kw).strip()
            if kw and len(kw) > 1:
                return kw
    return None

# Extracts a 1-to-5 star rating from the text.
def extract_rating(text: str) -> int | None:
    m = re.search(
        r"\b([1-5])\s*(?:star|stars|out\s*of\s*5|\/5)\b",
        text.lower(),
    )
    if m:
        return int(m.group(1))
    m2 = re.search(
        r"(?:give|gave|rating|rate|score)\s+(?:it\s+)?(?:a\s+)?([1-5])\b",
        text.lower(),
    )
    if m2:
        return int(m2.group(1))
    return None


 # Classifies the user's message into a supported chatbot intent.
def detect_intent(tokens: list[str], text: str) -> str:
    token_set = set(tokens)
    lower     = text.lower()

    # ── Priority 1: greetings / farewells / help ──────────────────────────
    if token_set & _GREETING:
        return "greet"
    if token_set & _BYE or any(p in lower for p in ("see you", "take care")):
        return "goodbye"
    if token_set & _HELP:
        return "help"

    # ── Priority 2: rating / feedback ─────────────────────────────────────
    if (extract_rating(text) is not None
            or token_set & _RATE_KW
            or "came back" in lower
            or "just returned" in lower):
        return "rate_itinerary"

    # ── Priority 3: generate itinerary ────────────────────────────────────
    if (token_set & _GEN_VERB and token_set & _ITIN_NOUN) or any(
        p in lower
        for p in ("plan my trip", "create itinerary", "make itinerary",
                  "generate itinerary", "build itinerary", "suggest places",
                  "book trip")
    ):
        return "generate_itinerary"

    # ── Priority 4: view existing itinerary ───────────────────────────────
    if token_set & _VIEW_VERB and token_set & _ITIN_NOUN:
        return "view_itinerary"

    # ── Priority 5: suggest places ───────────────────────────────────────
    if (token_set & _SUGGEST_V or token_set & _SUGGEST_CTX) and extract_place_keyword(text):
        return "suggest_places"

    # ── Priority 6: destination ───────────────────────────────────────────
    dest = extract_destination(text)
    if dest and (
        token_set & _DEST_VERB
        or any(p in lower for p in ("go to", "travel to", "visit", "want to"))
    ):
        return "update_destination"

    # ── Priority 6: days ──────────────────────────────────────────────────
    if extract_days(text) is not None:
        return "update_days"

    # ── Priority 7: budget ────────────────────────────────────────────────
    if extract_budget_type(tokens, text):
        return "update_budget"

    # ── Priority 8: interests ─────────────────────────────────────────────
    if extract_interests(tokens):
        return "update_interests"

    # ── Priority 9: weather ───────────────────────────────────────────────
    if extract_weather(tokens, text):
        return "update_weather"

    # ── Priority 10: bare destination mention ─────────────────────────────
    if dest:
        return "update_destination"

    return "unknown"


# ═══════════════════════════════════════════════════════════════════════════════
#  REPLY TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════

_GREET_REPLIES = [
    ("Hi! I'm the Pengo assistant. "
     "Tell me your destination, how many days you have, and what you enjoy — "
     "I'll help refine your perfect itinerary. Where are you thinking of going?"),
    ("Hello! Ready to plan your next adventure? "
     "Share a destination, your budget, and your interests and I'll get started."),
]

_UNK_REPLIES = [
    ("I'm not sure I understood that. "
     "Try saying something like <em>\"I want to visit Tokyo for 5 days\"</em> "
     "or type <strong>help</strong> to see what I can do."),
    ("Hmm, I didn't quite catch that. "
     "You can tell me your destination, budget, travel days, or interests. "
     "Type <strong>help</strong> for a full list."),
]

HELP_TEXT = (
    "Here's what I can help with:<br>"
    "🗺️ &nbsp;<strong>Destination</strong> — <em>\"I want to go to Tokyo\"</em><br>"
    "📅 &nbsp;<strong>Travel days</strong> — <em>\"5 days\"</em> or <em>\"a week\"</em><br>"
    "💰 &nbsp;<strong>Budget</strong> — <em>\"my budget is mid-range\"</em><br>"
    "🎯 &nbsp;<strong>Interests</strong> — <em>\"I love food and history\"</em><br>"
    "🌤️ &nbsp;<strong>Weather</strong> — <em>\"I prefer warm weather\"</em><br>"
    "📋 &nbsp;<strong>Generate itinerary</strong> — <em>\"plan my trip\"</em><br>"
    "⭐ &nbsp;<strong>Rate trip</strong> — <em>\"I'd give it 4 stars\"</em>"
)


# Processes the user message and returns the detected intent, entities, updates, and reply.
def process_message(text: str, context: dict | None = None) -> dict:
    ctx     = context or {}
    tokens  = tokenise(text)
    intent  = detect_intent(tokens, text)

    entities: dict = {
        "destination":   None,
        "days":          None,
        "budget_type":   None,
        "weather_pref":  None,
        "interests":     [],
        "rating":        None,
        "place_keyword": None,
    }
    updates: dict = {}
    reply         = ""

    # ── Greet ─────────────────────────────────────────────────────────────
    if intent == "greet":
        idx   = hash(text) % len(_GREET_REPLIES)
        reply = _GREET_REPLIES[idx]

    # ── Goodbye ───────────────────────────────────────────────────────────
    elif intent == "goodbye":
        reply = "Safe travels! Come back whenever you're ready to plan your next trip. ✈️"

    # ── Help ──────────────────────────────────────────────────────────────
    elif intent == "help":
        reply = HELP_TEXT

    # ── Suggest places (DB query handled in the Flask route) ─────────────
    elif intent == "suggest_places":
        kw   = extract_place_keyword(text)
        dest = extract_destination(text)
        entities["place_keyword"]  = kw
        entities["destination"]    = dest
        # Reply is filled in by the route after querying the DB.
        # Set a fallback in case the route doesn't override it.
        reply = f"Let me search for <strong>{kw}</strong> in our database…"

    # ── Destination update ────────────────────────────────────────────────
    elif intent == "update_destination":
        dest = extract_destination(text)
        days = extract_days(text)          # user might say "go to Paris for 4 days"
        entities["destination"] = dest
        entities["days"]        = days
        if dest and days:
            reply = (
                f"Great choice! <strong>{dest}</strong> for "
                f"<strong>{days} day{'s' if days != 1 else ''}</strong> sounds wonderful. 🌏 "
                "What's your budget range? (budget / mid-range / luxury)"
            )
        elif dest:
            reply = (
                f"<strong>{dest}</strong> is on the list! 🌍 "
                "How many days are you planning to stay?"
            )
        else:
            reply = "I couldn't identify a destination. Which city would you like to visit?"

    # ── Days update ───────────────────────────────────────────────────────
    elif intent == "update_days":
        days  = extract_days(text)
        dest  = extract_destination(text)
        entities["days"]        = days
        entities["destination"] = dest
        if dest and days:
            reply = (
                f"Got it — <strong>{dest}</strong> for "
                f"<strong>{days} day{'s' if days != 1 else ''}</strong>! "
                "What's your budget range? (budget / mid-range / luxury)"
            )
        else:
            reply = (
                f"Noted — <strong>{days} day{'s' if days != 1 else ''}</strong> of travel. "
                "Do you have a destination in mind?"
            )

    # ── Budget update ─────────────────────────────────────────────────────
    elif intent == "update_budget":
        btype = extract_budget_type(tokens, text)
        entities["budget_type"] = btype
        updates["budget_type"]  = btype
        current = ctx.get("budget_type", "not set")
        reply = (
            f"Budget updated to <strong>{btype}</strong> ✅ "
            f"(was: {current}). "
            "What kind of activities do you enjoy? "
            "E.g. <em>food, history, adventure</em>…"
        )

    # ── Interests update ──────────────────────────────────────────────────
    elif intent == "update_interests":
        interests = extract_interests(tokens)
        entities["interests"] = interests
        if interests:
            current = list(ctx.get("interests", []))
            merged  = list(dict.fromkeys(current + interests))
            updates["interests"] = merged
            listed = ", ".join(f"<strong>{i}</strong>" for i in interests)
            reply = (
                f"Added {listed} to your interests ✅ "
                f"Your full list: <em>{', '.join(merged)}</em>. "
                "Anything else to tweak?"
            )
        else:
            reply = (
                "I didn't recognise any interests. "
                "Try: <em>nature, food, history, shopping, adventure,</em> or <em>relaxation</em>."
            )

    # ── Weather update ────────────────────────────────────────────────────
    elif intent == "update_weather":
        wpref = extract_weather(tokens, text)
        entities["weather_pref"] = wpref
        if wpref:
            updates["weather_pref"] = wpref
            reply = (
                f"Weather preference set to <strong>{wpref}</strong> ✅ "
                "What destination are you thinking of?"
            )
        else:
            reply = "Options are: <em>warm, cold,</em> or <em>moderate</em>. Which do you prefer?"

    # ── Generate itinerary ────────────────────────────────────────────────
    elif intent == "generate_itinerary":
        reply = (
            "Ready to generate your itinerary! 🗺️ "
            "Head to the <strong>Recommendations</strong> page, pick your favourite attractions, "
            "then click <strong>Generate Itinerary</strong>. "
            "The route will be optimised using Haversine + Nearest Neighbour to minimise travel time."
        )

    # ── View itinerary ────────────────────────────────────────────────────
    elif intent == "view_itinerary":
        reply = (
            "Your saved itineraries are on the "
            "<a href='/itinerary' style='color:var(--pengo-blue)'>Itinerary</a> page. "
            "Want me to help update any preferences first?"
        )

    # ── Rate / feedback ───────────────────────────────────────────────────
    elif intent == "rate_itinerary":
        rating = extract_rating(text)
        entities["rating"] = rating
        if rating:
            stars = "⭐" * rating + "☆" * (5 - rating)
            reply = (
                f"Thanks for the {stars} rating! "
                "Your feedback helps us improve future recommendations. "
                "You can also add written feedback on the "
                "<a href='/itinerary' style='color:var(--pengo-blue)'>Itinerary</a> page."
            )
        else:
            reply = (
                "You can rate your trip (1–5 stars) on the "
                "<a href='/itinerary' style='color:var(--pengo-blue)'>Itinerary</a> page. "
                "What would you like to do next?"
            )

    # ── Unknown: attempt opportunistic entity extraction ──────────────────
    else:
        dest      = extract_destination(text)
        days      = extract_days(text)
        btype     = extract_budget_type(tokens, text)
        interests = extract_interests(tokens)
        wpref     = extract_weather(tokens, text)

        if any([dest, days, btype, interests, wpref]):
            parts = []
            if dest:
                entities["destination"] = dest
                parts.append(f"destination: <strong>{dest}</strong>")
            if days:
                entities["days"] = days
                parts.append(f"duration: <strong>{days} days</strong>")
            if btype:
                entities["budget_type"] = btype
                updates["budget_type"]  = btype
                parts.append(f"budget: <strong>{btype}</strong>")
            if interests:
                entities["interests"] = interests
                merged = list(dict.fromkeys(list(ctx.get("interests", [])) + interests))
                updates["interests"] = merged
                parts.append(f"interests: <strong>{', '.join(interests)}</strong>")
            if wpref:
                entities["weather_pref"] = wpref
                updates["weather_pref"]  = wpref
                parts.append(f"weather: <strong>{wpref}</strong>")

            saved = " Preferences saved!" if updates else ""
            reply = (
                f"I picked up: {', '.join(parts)}.{saved} "
                "Is there anything else you'd like to adjust?"
            )
        else:
            reply = _UNK_REPLIES[hash(text) % len(_UNK_REPLIES)]

    return {
        "intent":   intent,
        "entities": entities,
        "updates":  updates,
        "reply":    reply,
    }
