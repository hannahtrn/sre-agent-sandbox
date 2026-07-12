MOCK_SERVICE_TRAFFIC = {
    "checkout-service": {"requests_per_minute": 1200, "user_base": 45000},
    "user-service":     {"requests_per_minute": 800,  "user_base": 45000},
    "auth-service":     {"requests_per_minute": 2000, "user_base": 45000},
    "api-gateway":      {"requests_per_minute": 5000, "user_base": 45000},
    "payment-service":  {"requests_per_minute": 400,  "user_base": 45000},
}

IMPACT_DESCRIPTIONS = {
    "critical": "Complete service outage. Revenue impact active. Escalate immediately.",
    "high":     "Significant degradation. Subset of users unable to complete flows.",
    "medium":   "Partial degradation. Elevated error rate but core flows operational.",
    "low":      "Minor degradation. Monitoring closely. No immediate user impact.",
}


def estimate_impact(
    service_name: str,
    error_rate: float,
    severity: str,
) -> dict:
    traffic = MOCK_SERVICE_TRAFFIC.get(service_name, {
        "requests_per_minute": 500,
        "user_base": 10000,
    })

    affected_rpm   = int(traffic["requests_per_minute"] * error_rate)
    affected_users = int(traffic["user_base"] * error_rate)

    impact_summary = (
        f"Approximately {affected_users:,} users affected "
        f"({error_rate:.0%} of traffic on {service_name}). "
        f"{affected_rpm:,} requests/min failing. "
        f"{IMPACT_DESCRIPTIONS.get(severity, 'Impact unknown.')}"
    )

    return {
        "estimated_users_affected": affected_users,
        "impact_summary":           impact_summary,
    }
