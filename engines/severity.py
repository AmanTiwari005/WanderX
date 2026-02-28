"""
Typed Severity System for WanderX Engines.

Replaces raw string comparisons ("High", "Medium") with structured SeverityLevel
objects that carry numeric scores, colors, icons, and comparison operators.
"""
import logging

logger = logging.getLogger("wanderx.severity")


class SeverityLevel:
    """
    A typed severity level with numeric score, UI metadata, and escalation config.
    Supports comparison operators so engines can do: if level >= Severity.HIGH
    """
    __slots__ = ("name", "score", "color", "icon", "escalates_after_min", "priority")

    def __init__(self, name, score, color, icon, escalates_after_min=None, priority=0):
        self.name = name
        self.score = score
        self.color = color
        self.icon = icon
        self.escalates_after_min = escalates_after_min
        self.priority = priority

    # ── Comparison operators (by score) ────────────────────────
    def __eq__(self, other):
        if isinstance(other, SeverityLevel):
            return self.score == other.score
        if isinstance(other, str):
            return self.name.lower() == other.lower()
        return NotImplemented

    def __lt__(self, other):
        if isinstance(other, SeverityLevel):
            return self.score < other.score
        return NotImplemented

    def __le__(self, other):
        if isinstance(other, SeverityLevel):
            return self.score <= other.score
        return NotImplemented

    def __gt__(self, other):
        if isinstance(other, SeverityLevel):
            return self.score > other.score
        return NotImplemented

    def __ge__(self, other):
        if isinstance(other, SeverityLevel):
            return self.score >= other.score
        return NotImplemented

    def __hash__(self):
        return hash(self.name)

    def __repr__(self):
        return f"Severity.{self.name.upper()}"

    def __str__(self):
        return self.name

    def to_dict(self):
        """Serialize for JSON output."""
        return {
            "level": self.name,
            "score": self.score,
            "color": self.color,
            "icon": self.icon,
            "priority": self.priority
        }


class Severity:
    """
    Static severity levels used across all engines.
    Usage: Severity.CRITICAL, Severity.HIGH, etc.
    """
    CRITICAL = SeverityLevel(
        name="critical", score=90, color="#FF1744", icon="🔴",
        escalates_after_min=None, priority=5
    )
    HIGH = SeverityLevel(
        name="high", score=70, color="#FF9100", icon="🟠",
        escalates_after_min=60, priority=4
    )
    MEDIUM = SeverityLevel(
        name="medium", score=45, color="#FFC400", icon="🟡",
        escalates_after_min=120, priority=3
    )
    LOW = SeverityLevel(
        name="low", score=20, color="#00E676", icon="🟢",
        escalates_after_min=None, priority=2
    )
    INFO = SeverityLevel(
        name="info", score=5, color="#448AFF", icon="🔵",
        escalates_after_min=None, priority=1
    )

    # Ordered list for escalation lookup
    _LEVELS = [INFO, LOW, MEDIUM, HIGH, CRITICAL]

    @classmethod
    def from_string(cls, name):
        """Convert a string like 'High' to the corresponding SeverityLevel."""
        mapping = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "medium": cls.MEDIUM,
            "low": cls.LOW,
            "info": cls.INFO,
            # Legacy mappings
            "warning": cls.MEDIUM,
        }
        return mapping.get(name.lower(), cls.INFO)

    @classmethod
    def escalate(cls, current_level):
        """Return the next severity level up, or CRITICAL if already at max."""
        for i, lvl in enumerate(cls._LEVELS):
            if lvl.name == current_level.name:
                if i + 1 < len(cls._LEVELS):
                    return cls._LEVELS[i + 1]
                return cls.CRITICAL
        return cls.CRITICAL

    @classmethod
    def all_levels(cls):
        """Return all severity levels in ascending order."""
        return list(cls._LEVELS)

    @classmethod
    def score_weights(cls):
        """Return a dict mapping severity names to risk engine weights."""
        return {
            "Critical": 30,
            "High": 22,
            "Medium": 12,
            "Low": 6,
            "Info": 2,
            # Case-insensitive fallbacks
            "critical": 30,
            "high": 22,
            "medium": 12,
            "low": 6,
            "info": 2,
        }
