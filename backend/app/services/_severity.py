"""Constantes partagees autour de la severite des controles.

Centralise ce qui sinon serait duplique entre les services qui agregent
des non-conformites (executive_summary, recommendations, remediation_plan)
et risquerait de driver dans le temps.
"""

# Ordre de severite, du plus critique au moins critique
SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "medium": 2,
    "low": 3,
    "info": 4,
    "unknown": 5,
}

# Mapping severite -> horizon temporel pour le plan de remediation
SEVERITY_TO_HORIZON: dict[str, str] = {
    "critical": "quick_wins",
    "high": "short_term",
    "medium": "mid_term",
    "low": "long_term",
    "info": "long_term",
}

# Charge estimee par defaut (jours-homme) quand le controle n'a pas
# d'estimation specifique sur son champ effort_days. Vocation a etre
# remplace par une estimation contextuelle generee par LLM.
DEFAULT_EFFORT_BY_SEVERITY: dict[str, float] = {
    "critical": 0.25,
    "high": 1.0,
    "medium": 3.0,
    "low": 5.0,
    "info": 5.0,
}
