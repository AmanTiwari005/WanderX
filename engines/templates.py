"""
Dynamic Suggestion Template Engine for WanderX.

Replaces hardcoded suggestion blocks with context-aware templates
that fill dynamically based on destination, weather, profile, and intel.
"""
import logging

logger = logging.getLogger("wanderx.templates")


class SuggestionTemplate:
    """
    A dynamic suggestion template with trigger condition,
    title/reason patterns, and confidence scoring.
    """
    def __init__(self, template_id, category, trigger_fn, title, reason_template,
                 tags=None, confidence_fn=None, priority=5):
        self.template_id = template_id
        self.category = category
        self.trigger_fn = trigger_fn
        self.title = title
        self.reason_template = reason_template
        self.tags = tags or []
        self.confidence_fn = confidence_fn or (lambda ctx: "Medium")
        self.priority = priority

    def matches(self, context):
        """Check if template trigger condition is met."""
        try:
            return self.trigger_fn(context)
        except Exception:
            return False

    def render(self, context):
        """Render the template with context variables."""
        try:
            reason = self.reason_template.format(**context)
        except (KeyError, IndexError):
            reason = self.reason_template

        try:
            title = self.title.format(**context) if "{" in self.title else self.title
        except (KeyError, IndexError):
            title = self.title

        return {
            "title": title,
            "reason": reason,
            "confidence": self.confidence_fn(context),
            "tags": self.tags,
            "template_id": self.template_id,
            "category": self.category,
            "priority": self.priority
        }


def _build_context_vars(raw_context, profile=None):
    """
    Extract commonly-used variables from raw context into a flat dict
    for template interpolation.
    """
    weather = raw_context.get("weather", {})
    profile = profile or {}

    return {
        # Weather
        "temp_c": weather.get("temperature_c", 25),
        "feels_like": weather.get("feels_like_c", weather.get("temperature_c", 25)),
        "weather_desc": weather.get("description", "unknown"),
        "rain_prob": weather.get("rain_probability", 0),
        "wind_speed_kmh": round(weather.get("wind_speed", 0) * 3.6),
        "uv_index": weather.get("uv_index", 0),
        # Time
        "hour": raw_context.get("time", {}).get("hour", 12),
        "daylight_remaining": raw_context.get("daylight_remaining"),
        # Crowd
        "crowd_score": raw_context.get("crowd", {}).get("crowd_score", 5),
        # Profile
        "interests": (profile.get("interests") or "").lower(),
        "budget": (profile.get("budget") or "moderate").lower(),
        "group_type": (profile.get("group_type") or "").lower(),
        "destination": profile.get("destination", "this destination"),
        # Flags
        "is_raining": weather.get("rain_probability", 0) > 0.5,
        "is_night": raw_context.get("time", {}).get("hour", 12) > 19,
        "is_hot": weather.get("temperature_c", 25) > 35,
        "is_cold": weather.get("temperature_c", 25) < 5,
        "is_crowded": raw_context.get("crowd", {}).get("crowd_score", 0) >= 7,
        # Raw for advanced templates
        "news": raw_context.get("news", {}),
        "cultural": raw_context.get("cultural", {}),
        "health": raw_context.get("health", {}),
        "sustainability": raw_context.get("sustainability", {}),
    }


# ═══════════════════════════════════════════════════════════════
# TEMPLATE REGISTRY
# ═══════════════════════════════════════════════════════════════

SUGGESTION_TEMPLATES = [
    # ── Weather-Adaptive ──────────────────────────────────────
    SuggestionTemplate(
        template_id="rain_indoor",
        category="weather",
        trigger_fn=lambda ctx: ctx.get("is_raining", False),
        title="Indoor Cultural Dive",
        reason_template="Rain expected ({weather_desc}). Perfect time for museums, galleries, or cozy cafés.",
        tags=["weather-adaptive", "indoor"],
        confidence_fn=lambda ctx: "High" if ctx.get("rain_prob", 0) > 0.7 else "Medium",
        priority=8
    ),
    SuggestionTemplate(
        template_id="heat_retreat",
        category="weather",
        trigger_fn=lambda ctx: ctx.get("is_hot", False) and not ctx.get("is_night", False),
        title="Beat the Heat — Pool, Spa or AC Retreat",
        reason_template="It's {temp_c}°C (feels like {feels_like}°C). Cool off with an indoor or water experience.",
        tags=["weather-adaptive", "indoor"],
        confidence_fn=lambda _: "High",
        priority=8
    ),
    SuggestionTemplate(
        template_id="cold_cozy",
        category="weather",
        trigger_fn=lambda ctx: ctx.get("is_cold", False),
        title="Warm & Cozy Experience",
        reason_template="It's {temp_c}°C outside. Enjoy hot beverages, warm local cuisine, or a fireside stay.",
        tags=["weather-adaptive", "indoor"],
        confidence_fn=lambda _: "High",
        priority=7
    ),
    SuggestionTemplate(
        template_id="clear_day_walk",
        category="weather",
        trigger_fn=lambda ctx: not ctx.get("is_raining") and not ctx.get("is_night") and not ctx.get("is_hot"),
        title="Scenic Nature Walk",
        reason_template="Weather is pleasant ({temp_c}°C, {weather_desc}). Great for outdoor exploration.",
        tags=["weather-adaptive", "outdoor"],
        confidence_fn=lambda _: "High",
        priority=6
    ),

    # ── Time-Adaptive ─────────────────────────────────────────
    SuggestionTemplate(
        template_id="golden_hour",
        category="time",
        trigger_fn=lambda ctx: ctx.get("daylight_remaining") is not None and 1 < ctx["daylight_remaining"] < 2.5 and not ctx.get("is_raining"),
        title="Golden Hour Viewpoint",
        reason_template="Sunset in ~{daylight_remaining:.0f}h! Head to a scenic viewpoint for stunning photos.",
        tags=["time-adaptive", "photography"],
        confidence_fn=lambda _: "High",
        priority=9
    ),
    SuggestionTemplate(
        template_id="night_dining",
        category="time",
        trigger_fn=lambda ctx: ctx.get("is_night", False),
        title="Safe Featured Dining",
        reason_template="Late hours are best for relaxed dining. Pick well-lit restaurant districts.",
        tags=["time-adaptive", "dining"],
        confidence_fn=lambda _: "Medium",
        priority=6
    ),
    SuggestionTemplate(
        template_id="sunrise_walk",
        category="time",
        trigger_fn=lambda ctx: 5 <= ctx.get("hour", 12) <= 7 and not ctx.get("is_raining"),
        title="Sunrise & Morning Walk",
        reason_template="Best time for peaceful walks, sunrise views, and beating the crowds.",
        tags=["time-adaptive", "outdoor"],
        confidence_fn=lambda _: "High",
        priority=7
    ),

    # ── Crowd-Adaptive ────────────────────────────────────────
    SuggestionTemplate(
        template_id="crowd_offpeak",
        category="crowd",
        trigger_fn=lambda ctx: ctx.get("is_crowded", False),
        title="Off-Peak Visit Strategy",
        reason_template="Crowd score is {crowd_score}/10. Visit attractions early morning or during lunch hours.",
        tags=["crowd-adaptive"],
        confidence_fn=lambda _: "Medium",
        priority=7
    ),

    # ── Budget-Adaptive ───────────────────────────────────────
    SuggestionTemplate(
        template_id="budget_gems",
        category="budget",
        trigger_fn=lambda ctx: ctx.get("budget", "moderate") in ("low", "budget", "backpacker"),
        title="Budget-Friendly Local Gems",
        reason_template="Explore free attractions, street food, and walking tours to maximize your budget.",
        tags=["budget-adaptive"],
        confidence_fn=lambda _: "High",
        priority=5
    ),
    SuggestionTemplate(
        template_id="premium_experience",
        category="budget",
        trigger_fn=lambda ctx: ctx.get("budget", "moderate") in ("luxury", "premium", "high"),
        title="Premium Experience",
        reason_template="Indulge in exclusive dining, private tours, or luxury wellness experiences.",
        tags=["budget-adaptive"],
        confidence_fn=lambda _: "Medium",
        priority=5
    ),

    # ── Interest-Based ────────────────────────────────────────
    SuggestionTemplate(
        template_id="foodie_tour",
        category="interest",
        trigger_fn=lambda ctx: "food" in ctx.get("interests", ""),
        title="Local Food Tour",
        reason_template="Your interest in food matches perfectly — explore authentic local cuisine and street food.",
        tags=["interest-based", "food"],
        confidence_fn=lambda _: "High",
        priority=6
    ),
    SuggestionTemplate(
        template_id="history_walk",
        category="interest",
        trigger_fn=lambda ctx: "history" in ctx.get("interests", ""),
        title="Heritage Walking Tour",
        reason_template="Explore historical landmarks and cultural heritage through a guided walk.",
        tags=["interest-based", "history"],
        confidence_fn=lambda _: "High",
        priority=6
    ),
    SuggestionTemplate(
        template_id="adventure_activity",
        category="interest",
        trigger_fn=lambda ctx: "adventure" in ctx.get("interests", "") and not ctx.get("is_raining"),
        title="Outdoor Adventure Activity",
        reason_template="Conditions are right for adrenaline activities — explore nature's playground.",
        tags=["interest-based", "adventure"],
        confidence_fn=lambda _: "High",
        priority=6
    ),
    SuggestionTemplate(
        template_id="beach_day",
        category="interest",
        trigger_fn=lambda ctx: "beach" in ctx.get("interests", "") and not ctx.get("is_raining") and not ctx.get("is_cold"),
        title="Beach & Water Sports",
        reason_template="Great day for sun, sand, and water at {temp_c}°C with {weather_desc}.",
        tags=["interest-based", "beach"],
        confidence_fn=lambda _: "High",
        priority=6
    ),
    SuggestionTemplate(
        template_id="nature_explore",
        category="interest",
        trigger_fn=lambda ctx: "nature" in ctx.get("interests", "") and not ctx.get("is_raining"),
        title="Wildlife & Nature Trail",
        reason_template="Explore the local biodiversity and natural landscapes.",
        tags=["interest-based", "nature"],
        confidence_fn=lambda _: "High",
        priority=6
    ),
    SuggestionTemplate(
        template_id="photography_walk",
        category="interest",
        trigger_fn=lambda ctx: "photo" in ctx.get("interests", ""),
        title="Photo Walk",
        reason_template="Capture the beauty of {destination} — great light conditions today.",
        tags=["interest-based", "photography"],
        confidence_fn=lambda _: "High",
        priority=5
    ),
    SuggestionTemplate(
        template_id="wellness_retreat",
        category="interest",
        trigger_fn=lambda ctx: "wellness" in ctx.get("interests", "") or "spa" in ctx.get("interests", ""),
        title="Spa & Wellness Retreat",
        reason_template="Recharge with local wellness traditions — yoga, ayurveda, or spa treatments.",
        tags=["interest-based", "wellness"],
        confidence_fn=lambda _: "High",
        priority=5
    ),
    SuggestionTemplate(
        template_id="shopping_bazaar",
        category="interest",
        trigger_fn=lambda ctx: "shop" in ctx.get("interests", ""),
        title="Local Market & Bazaar",
        reason_template="Browse authentic handicrafts, spices, and souvenirs at local markets.",
        tags=["interest-based", "shopping"],
        confidence_fn=lambda _: "Medium",
        priority=5
    ),
    SuggestionTemplate(
        template_id="culture_immersion",
        category="interest",
        trigger_fn=lambda ctx: "culture" in ctx.get("interests", ""),
        title="Cultural Immersion Experience",
        reason_template="Discover local art, temples, and traditional experiences.",
        tags=["interest-based", "culture"],
        confidence_fn=lambda _: "High",
        priority=6
    ),

    # ── Sustainability ────────────────────────────────────────
    SuggestionTemplate(
        template_id="eco_option",
        category="sustainability",
        trigger_fn=lambda ctx: bool(ctx.get("sustainability", {}).get("eco_activities") or
                                     ctx.get("sustainability", {}).get("responsible_tips")),
        title="🌱 Eco-Friendly Option",
        reason_template="Sustainable travel choices available at this destination.",
        tags=["sustainability"],
        confidence_fn=lambda _: "Medium",
        priority=4
    ),
]


class TemplateEngine:
    """
    Renders matching suggestion templates for a given context.
    """
    def __init__(self, templates=None):
        self.templates = templates or SUGGESTION_TEMPLATES

    def render_suggestions(self, raw_context, profile=None, max_results=12):
        """
        Evaluate all templates against context and return matching suggestions.
        
        Args:
            raw_context: Dict with weather, time, crowd, news, etc.
            profile: User profile dict
            max_results: Maximum suggestions to return
            
        Returns:
            list: Rendered suggestion dicts, sorted by priority
        """
        context_vars = _build_context_vars(raw_context, profile)
        suggestions = []
        seen_ids = set()

        for template in self.templates:
            if template.template_id in seen_ids:
                continue
            if template.matches(context_vars):
                rendered = template.render(context_vars)
                suggestions.append(rendered)
                seen_ids.add(template.template_id)

        # Sort by priority (highest first), then by confidence
        confidence_order = {"High": 3, "Medium": 2, "Low": 1}
        suggestions.sort(
            key=lambda s: (s.get("priority", 0), confidence_order.get(s.get("confidence"), 0)),
            reverse=True
        )

        return suggestions[:max_results]

    def add_template(self, template):
        """Register a new template at runtime."""
        self.templates.append(template)

    def get_categories(self):
        """Return all unique template categories."""
        return list(set(t.category for t in self.templates))
