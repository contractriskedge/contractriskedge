import {
  categoriesCompatible,
  inferCategoryFromText,
  isSectionLabelOnly,
  isSubstantiveClauseText,
  reconcileRedlineAssociations,
} from "./redlineIntegrity";

describe("redlineIntegrity", () => {
  it("detects fees vs indemnification mismatch", () => {
    const result = reconcileRedlineAssociations(
      {
        clause_type: "payment",
        section: "Fees",
        page: 2,
        original_text: "§ Fees",
        proposed_text:
          "Indemnification: Each party agrees to indemnify, defend, and hold harmless the other party.",
        finding_id: null,
        finding_title: null,
        locator_section: "Fees",
      },
    );
    expect(result.mismatch_warning).toMatch(/mapping error/i);
    expect(result.proposed_category).toBe("indemnification");
    expect(result.source_category).toBe("fees");
  });

  it("aligns labels and original from finding when finding matches proposed", () => {
    const result = reconcileRedlineAssociations(
      {
        clause_type: "payment",
        section: "Fees",
        page: 2,
        original_text: "§ Fees",
        proposed_text:
          "Each party shall indemnify, defend, and hold harmless the other from third-party claims.",
        finding_id: "f-1",
        finding_title: "Unbalanced Indemnification",
        locator_section: "Fees",
      },
      {
        finding_id: "f-1",
        clause_type: "indemnification",
        title: "Unbalanced Indemnification",
        clause_text:
          "Vendor shall indemnify Customer against all claims arising from the Services.",
        page_numbers: [8],
      },
    );
    expect(result.clause_type).toBe("indemnification");
    expect(result.original_text).toContain("indemnify");
    expect(categoriesCompatible(result.finding_category, result.proposed_category)).toBe(true);
  });

  it("does not inject finding text when finding category conflicts with proposed", () => {
    const result = reconcileRedlineAssociations(
      {
        clause_type: "payment",
        section: "Fees",
        page: 2,
        original_text: "§ Fees",
        proposed_text:
          "Each party shall indemnify, defend, and hold harmless the other from third-party claims.",
        finding_id: "f-fees",
        finding_title: "Payment terms unclear",
      },
      {
        finding_id: "f-fees",
        clause_type: "payment",
        title: "Payment terms unclear",
        clause_text: "Customer shall pay Vendor the fees set forth in Exhibit B within 30 days.",
        page_numbers: [2],
      },
    );
    expect(result.original_text).toBe("§ Fees");
    expect(result.mismatch_warning).toBeTruthy();
  });

  it("rejects liability redline linked to privacy finding", () => {
    const result = reconcileRedlineAssociations(
      {
        clause_type: "liability",
        section: "4",
        page: 4,
        original_text: "4. Warranties",
        proposed_text: "Limitation of Liability. Cap at 12 months fees.",
        finding_id: "f-privacy",
        finding_title: "Missing Data Privacy Clause",
      },
      {
        finding_id: "f-privacy",
        clause_type: "data_privacy",
        title: "Missing Data Privacy Clause",
        clause_text: "Vendor shall comply with GDPR data processing requirements.",
      },
    );
    expect(result.mapping_status).toBe("invalid_mapping");
    expect(result.mapping_valid).toBe(false);
  });

  it("accepts liability finding with liability redline", () => {
    const result = reconcileRedlineAssociations(
      {
        clause_type: "liability",
        section: "12",
        page: 12,
        original_text: "No liability cap present.",
        proposed_text: "Aggregate liability shall not exceed 12 months fees.",
        finding_id: "f-liability",
        finding_title: "Missing Liability Cap Clause",
      },
      {
        finding_id: "f-liability",
        clause_type: "liability",
        title: "Missing Liability Cap Clause",
        clause_text: "Contract lacks a limitation of liability clause.",
      },
    );
    expect(result.mapping_status).toBe("valid");
    expect(result.mapping_valid).toBe(true);
  });

  it("accepts IP finding with IP redline", () => {
    const result = reconcileRedlineAssociations(
      {
        clause_type: "ip",
        section: "8",
        page: 8,
        original_text: "Work product ownership unclear.",
        proposed_text: "All intellectual property rights vest in Customer.",
        finding_id: "f-ip",
        finding_title: "IP Ownership Risk",
      },
      {
        finding_id: "f-ip",
        clause_type: "intellectual_property",
        title: "IP Ownership Risk",
        clause_text: "Vendor retains broad IP rights in deliverables.",
      },
    );
    expect(result.mapping_status).toBe("valid");
    expect(categoriesCompatible(result.finding_category, result.proposed_category)).toBe(true);
  });

  it("classifies section labels vs substantive text", () => {
    expect(isSectionLabelOnly("§ Fees")).toBe(true);
    expect(isSectionLabelOnly("2. Fees")).toBe(true);
    expect(
      isSubstantiveClauseText(
        "Customer shall pay Vendor the fees set forth in Exhibit B within thirty (30) days.",
      ),
    ).toBe(true);
    expect(inferCategoryFromText("Indemnification: Each party agrees")).toBe("indemnification");
  });
});
