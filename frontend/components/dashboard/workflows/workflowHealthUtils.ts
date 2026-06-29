import type { ValidationIssue, ValidationResult } from "@/services/api/workflowAdmin";

export type HealthTier = "healthy" | "warning" | "critical";

export function getHealthTier(score: number): HealthTier {
  if (score >= 90) return "healthy";
  if (score >= 70) return "warning";
  return "critical";
}

export function getHealthLabel(tier: HealthTier): string {
  switch (tier) {
    case "healthy": return "Healthy";
    case "warning": return "Warning";
    case "critical": return "Critical";
  }
}

export function getHealthColors(score: number) {
  const tier = getHealthTier(score);
  switch (tier) {
    case "healthy":
      return {
        tier,
        text: "text-emerald-600",
        bg: "bg-emerald-50 border-emerald-200",
        badge: "bg-emerald-100 text-emerald-700",
      };
    case "warning":
      return {
        tier,
        text: "text-amber-600",
        bg: "bg-amber-50 border-amber-200",
        badge: "bg-amber-100 text-amber-700",
      };
    case "critical":
      return {
        tier,
        text: "text-red-600",
        bg: "bg-red-50 border-red-200",
        badge: "bg-red-100 text-red-700",
      };
  }
}

/** Derive health breakdown from pack data and optional validation result */
export function buildHealthDetails(
  healthScore: number,
  warningCount: number,
  validation?: ValidationResult | null,
) {
  const errors = validation?.errors ?? [];
  const warnings = validation?.warnings ?? [];
  const publishBlockers = errors.filter((e) => e.severity === "error");
  const validationWarnings = warnings.length > 0 ? warnings : [];

  const recommendations: string[] = [];
  if (healthScore < 90) {
    recommendations.push("Resolve validation warnings to improve health score");
  }
  if (publishBlockers.length > 0) {
    recommendations.push("Fix all blocking errors before publishing");
  }
  if (warningCount > 0 && validationWarnings.length === 0) {
    recommendations.push(`Review ${warningCount} outstanding configuration issue${warningCount !== 1 ? "s" : ""}`);
  }
  publishBlockers.forEach((e) => {
    if (e.suggestion) recommendations.push(e.suggestion);
  });
  validationWarnings.slice(0, 3).forEach((w) => {
    if (w.suggestion) recommendations.push(w.suggestion);
  });

  const calculation = validation
    ? `Score: ${validation.score}/100 · ${errors.length} error${errors.length !== 1 ? "s" : ""}, ${warnings.length} warning${warnings.length !== 1 ? "s" : ""}`
    : `Base score: ${healthScore}/100 · ${warningCount} configuration warning${warningCount !== 1 ? "s" : ""}`;

  return {
    score: validation?.score ?? healthScore,
    tier: getHealthTier(validation?.score ?? healthScore),
    validationIssues: errors,
    warnings: validationWarnings,
    publishBlockers,
    calculation,
    recommendations: [...new Set(recommendations)].slice(0, 5),
    canPublish: publishBlockers.length === 0 && (validation?.is_valid ?? healthScore >= 70),
  };
}

export function issueSeverityClass(severity: ValidationIssue["severity"]) {
  return severity === "error"
    ? "text-red-600 bg-red-50 border-red-100"
    : "text-amber-600 bg-amber-50 border-amber-100";
}
