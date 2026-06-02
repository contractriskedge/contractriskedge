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
