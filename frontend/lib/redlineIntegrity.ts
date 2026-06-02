/**
 * Redline association integrity — detect and reconcile mismatched
 * source clause metadata vs proposed text vs linked finding.
 */

export interface LinkedFindingInput {
  finding_id: string;
  clause_type?: string | null;
  title?: string | null;
  clause_text?: string | null;
  description?: string | null;
  page_numbers?: number[];
  category?: string | null;
}

export interface RedlineIntegrityResult {
  clause_type: string;
  section: string;
  page: number;
  original_text: string;
  proposed_text: string;
  finding_id: string | null;
  finding_title: string | null;
  mismatch_warning: string | null;
  source_category: string | null;
  proposed_category: string | null;
  finding_category: string | null;
}

const CATEGORY_ALIASES: Record<string, string[]> = {
  fees: ["fees", "fee", "payment", "payments", "pricing", "invoice", "payment_terms"],
  indemnification: ["indemnification", "indemnify", "indemn", "hold_harmless"],
  liability: ["liability", "liability_caps", "limitation", "limitation_of_liability"],
  termination: ["termination", "term", "renewal", "auto_renewal"],
  confidentiality: ["confidentiality", "confidential", "nda"],
  sla: ["sla", "service_level", "availability", "uptime"],
  ip: ["ip", "intellectual_property", "intellectual", "ownership"],
  data_protection: ["data_protection", "privacy", "gdpr", "dpa"],
};

const TEXT_CATEGORY_PATTERNS: [string, RegExp][] = [
  ["indemnification", /\bindemnif/i],
  ["fees", /\b(fees?|payment terms?|pricing|invoice|payable|exhibit\s+[a-z]?\s*fees)\b/i],
  ["liability", /\b(liabilit|limitation of liability|aggregate liability)\b/i],
  ["termination", /\b(terminat|renewal|non-?renewal)\b/i],
  ["confidentiality", /\b(confidential|non-?disclosure)\b/i],
  ["sla", /\b(service level|uptime|availability|sla)\b/i],
  ["ip", /\b(intellectual property|infringement|work product)\b/i],
  ["data_protection", /\b(personal data|gdpr|data processing)\b/i],
];

function pickString(...values: unknown[]): string {
  for (const v of values) {
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

function tokenizeCategory(input: string): string {
  return input.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

export function normalizeCategory(input: string | null | undefined): string | null {
  const raw = pickString(input);
  if (!raw) return null;
  const token = tokenizeCategory(raw);
  for (const [canonical, aliases] of Object.entries(CATEGORY_ALIASES)) {
    if (aliases.some((a) => token.includes(a) || a.includes(token))) return canonical;
  }
  for (const [canonical, pattern] of TEXT_CATEGORY_PATTERNS) {
    if (pattern.test(raw)) return canonical;
  }
  return token.length > 2 ? token : null;
}

export function inferCategoryFromText(text: string): string | null {
  const t = pickString(text);
  if (!t) return null;
  for (const [canonical, pattern] of TEXT_CATEGORY_PATTERNS) {
    if (pattern.test(t)) return canonical;
  }
  return normalizeCategory(t);
}

export function categoriesCompatible(
  a: string | null | undefined,
  b: string | null | undefined,
): boolean {
  const ca = a ? normalizeCategory(a) : null;
  const cb = b ? normalizeCategory(b) : null;
  if (!ca || !cb) return true;
  return ca === cb;
}

/** True when text looks like a section heading only, not clause body. */
export function isSectionLabelOnly(text: string): boolean {
  const t = text.trim();
  if (!t) return true;
  if (t.length > 120) return false;
  if (/^§?\s*[\d.]+\s*[\w\s/&-]{2,40}$/i.test(t)) return true;
  if (/^(§\s*)?[A-Z][a-z]+(\s+[A-Z][a-z]+){0,3}$/.test(t) && t.length < 45 && !t.includes(",")) {
    return true;
  }
  return false;
}

export function isSubstantiveClauseText(text: string): boolean {
  const t = text.trim();
  if (t.length < 40) return false;
  if (isSectionLabelOnly(t)) return false;
  return true;
}

function formatSectionLabel(
  section: string,
  clauseType: string,
  page?: number,
): string {
  if (section && section !== "—") return section;
  if (page && page > 0) return String(page);
  return clauseType || "—";
}

function categoryLabel(cat: string | null): string {
  if (!cat) return "unknown";
  return cat.replace(/_/g, " ");
}

export interface ReconcileRedlineInput {
  clause_type: string;
  section: string;
  page: number;
  original_text: string;
  proposed_text: string;
  context_excerpt?: string;
  finding_id: string | null;
  finding_title: string | null;
  locator_section?: string | null;
  locator_legal_domain?: string | null;
}

/**
 * Reconcile display fields when API locator/labels disagree with proposed text
 * or linked finding. Prefers finding metadata when it matches proposed content.
 */
export function reconcileRedlineAssociations(
  input: ReconcileRedlineInput,
  finding?: LinkedFindingInput | null,
): RedlineIntegrityResult {
  const proposed = pickString(input.proposed_text);
  const explicitOriginal = pickString(input.original_text);
  const context = pickString(input.context_excerpt);

  const proposedCat = inferCategoryFromText(proposed);
  const sourceCat = normalizeCategory(
    [input.clause_type, input.locator_legal_domain, input.locator_section, input.section]
      .filter(Boolean)
      .join(" "),
  );
  const originalCat = inferCategoryFromText(explicitOriginal);
  const findingCat = finding
    ? normalizeCategory(
        [finding.clause_type, finding.category, finding.title, finding.clause_text].join(" "),
      ) || inferCategoryFromText(finding.clause_text || finding.description || "")
    : null;

  let clauseType = input.clause_type || "clause";
  let section = input.section || "—";
  let page = input.page || 0;
  let findingId = input.finding_id;
  let findingTitle = input.finding_title;
  let originalText = explicitOriginal;
  const warnings: string[] = [];

  const findingMatchesProposed =
    finding && proposedCat && findingCat && categoriesCompatible(findingCat, proposedCat);
  const findingMatchesSource =
    finding && sourceCat && findingCat && categoriesCompatible(findingCat, sourceCat);

  if (proposedCat && sourceCat && !categoriesCompatible(proposedCat, sourceCat)) {
    warnings.push(
      `Source clause appears to be ${categoryLabel(sourceCat)} (${formatSectionLabel(section, clauseType)}) but proposed text is ${categoryLabel(proposedCat)}.`,
    );
  }

  if (finding && proposedCat && findingCat && !categoriesCompatible(findingCat, proposedCat)) {
    warnings.push(
      `Linked finding "${finding.title || "Finding"}" (${categoryLabel(findingCat)}) does not match proposed redline (${categoryLabel(proposedCat)}).`,
    );
  }

  if (findingMatchesProposed) {
    clauseType = pickString(finding.clause_type, finding.category, clauseType) || clauseType;
    findingTitle = pickString(finding.title, findingTitle) || findingTitle;
    findingId = finding.finding_id;
    if (finding.page_numbers?.[0]) page = finding.page_numbers[0];
    const findingSection = finding.page_numbers?.[0]
      ? String(finding.page_numbers[0])
      : clauseType;
    if (sourceCat && !categoriesCompatible(sourceCat, findingCat)) {
      section = findingSection;
    }
  } else if (findingMatchesSource && !proposedCat) {
    clauseType = pickString(finding.clause_type, clauseType) || clauseType;
    findingTitle = pickString(finding.title, findingTitle) || findingTitle;
  }

  const sourceAlignedWithProposed =
    !proposedCat || !sourceCat || categoriesCompatible(proposedCat, sourceCat);

  if (!isSubstantiveClauseText(originalText)) {
    if (findingMatchesProposed && isSubstantiveClauseText(finding.clause_text || "")) {
      originalText = pickString(finding.clause_text);
    } else if (
      findingMatchesSource &&
      sourceAlignedWithProposed &&
      isSubstantiveClauseText(finding.clause_text || "")
    ) {
      originalText = pickString(finding.clause_text);
    } else if (isSubstantiveClauseText(context)) {
      originalText = context;
    } else if (
      explicitOriginal &&
      originalCat &&
      proposedCat &&
      categoriesCompatible(originalCat, proposedCat)
    ) {
      originalText = explicitOriginal;
    } else if (explicitOriginal && !proposedCat) {
      originalText = explicitOriginal;
    }
  }

  if (
    proposedCat &&
    originalText &&
    !isSubstantiveClauseText(originalText) &&
    !categoriesCompatible(inferCategoryFromText(originalText), proposedCat)
  ) {
    if (!warnings.some((w) => w.includes("Original clause"))) {
      warnings.push(
        "Original clause text is missing or only shows a section heading — use Locate Source Clause to verify the baseline.",
      );
    }
  }

  const mismatch_warning =
    warnings.length > 0
      ? `${warnings.join(" ")} Possible mapping error — verify before accepting.`
      : null;

  return {
    clause_type: clauseType,
    section,
    page,
    original_text: originalText,
    proposed_text: proposed,
    finding_id: findingId,
    finding_title: findingTitle,
    mismatch_warning,
    source_category: sourceCat,
    proposed_category: proposedCat,
    finding_category: findingCat,
  };
}
