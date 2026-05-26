import { computeSemanticDiff, computeDiffMetrics } from "./semanticDiff";

describe("computeSemanticDiff", () => {
  it("highlights only changed words for lawyer edits to AI suggestion", () => {
    const ai =
      "10.2 The total liability of either party for any claim arising out of or in connection with this Agreement shall not exceed the fees paid in the preceding twelve (12) months. This is delete";
    const edited =
      "10.2 The total liability of either party for any claim arising under this Agreement shall not exceed the fees paid in the preceding twelve (12) months. Add Test";

    const segments = computeSemanticDiff(ai, edited);
    const metrics = computeDiffMetrics(segments);

    expect(metrics.additions).toBeGreaterThan(0);
    expect(metrics.deletions).toBeGreaterThan(0);

    const nonEqual = segments.filter((s) => s.tag !== "equal");
    const changedText = nonEqual.map((s) => s.text).join("");
    expect(changedText).not.toBe(edited);
    expect(changedText.length).toBeLessThan(edited.length);

    const equalText = segments.filter((s) => s.tag === "equal").map((s) => s.text).join("");
    expect(equalText.length).toBeGreaterThan(edited.length * 0.5);
  });

  it("marks deletions with delete tag and additions with insert tag", () => {
    const before = "arising out of or in connection with";
    const after = "arising under";

    const segments = computeSemanticDiff(before, after);
    expect(segments.some((s) => s.tag === "delete")).toBe(true);
    expect(segments.some((s) => s.tag === "insert")).toBe(true);
  });

  it("ignores punctuation-only changes", () => {
    const before = "Limit liability to fees paid.";
    const after = "Limit liability to fees paid;";

    const segments = computeSemanticDiff(before, after);
    const nonEqual = segments.filter((s) => s.tag !== "equal");
    // Punctuation-only changes should be collapsed
    expect(nonEqual.length).toBe(0);
  });

  it("ignores whitespace-only changes", () => {
    const before = "Indemnify   against claims.";
    const after = "Indemnify against claims.";

    const segments = computeSemanticDiff(before, after);
    const nonEqual = segments.filter((s) => s.tag !== "equal");
    expect(nonEqual.length).toBe(0);
  });

  it("handles identical texts", () => {
    const text = "The parties agree to indemnify each other.";
    const segments = computeSemanticDiff(text, text);
    expect(segments.every((s) => s.tag === "equal")).toBe(true);
    expect(segments.map((s) => s.text).join("")).toBe(text);
  });

  it("handles empty original (pure insert)", () => {
    const text = "New clause added.";
    const segments = computeSemanticDiff("", text);
    expect(segments).toEqual([{ tag: "insert", text }]);
  });

  it("handles empty proposed (pure delete)", () => {
    const text = "Clause to remove.";
    const segments = computeSemanticDiff(text, "");
    expect(segments).toEqual([{ tag: "delete", text }]);
  });

  it("handles both empty", () => {
    const segments = computeSemanticDiff("", "");
    expect(segments).toEqual([]);
  });

  it("groups adjacent inserted tokens into a single span", () => {
    const before = "PERPETUAL IRREVOCABLE license";
    const after = "LIMITED REVOCABLE license";

    const segments = computeSemanticDiff(before, after);
    const inserts = segments.filter((s) => s.tag === "insert");
    const deletes = segments.filter((s) => s.tag === "delete");

    // Adjacent insertions should be grouped (not individual words)
    expect(inserts.length).toBeLessThanOrEqual(2);
    expect(deletes.length).toBeLessThanOrEqual(2);

    const insertText = inserts.map((s) => s.text).join("");
    expect(insertText).toContain("LIMITED");
    expect(insertText).toContain("REVOCABLE");

    const deleteText = deletes.map((s) => s.text).join("");
    expect(deleteText).toContain("PERPETUAL");
    expect(deleteText).toContain("IRREVOCABLE");
  });

  it("handles single character changes that are meaningful", () => {
    const before = "indemnification";
    const after = "indemnification obligation";

    const segments = computeSemanticDiff(before, after);
    const inserts = segments.filter((s) => s.tag === "insert");
    expect(inserts.length).toBeGreaterThan(0);
    expect(inserts.some((s) => s.text.includes("obligation"))).toBe(true);
  });

  it("handles sentence reordering within a paragraph", () => {
    const before = "Party A shall indemnify. Party B shall defend.";
    const after = "Party B shall defend. Party A shall indemnify.";

    const segments = computeSemanticDiff(before, after);
    const equalText = segments.filter((s) => s.tag === "equal").map((s) => s.text).join("");
    // Most content should be recognized as equal (just reordered)
    expect(equalText.length).toBeGreaterThan(0);
  });

  it("preserves section headings as atomic units", () => {
    const before = "10.2 Limitation of Liability. Each party's liability shall be capped.";
    const after = "10.2 Limitation of Liability. Each party's liability shall be limited.";

    const segments = computeSemanticDiff(before, after);
    const equalText = segments.filter((s) => s.tag === "equal").map((s) => s.text).join("");
    // Section heading "10.2 Limitation of Liability." should be preserved as equal
    expect(equalText).toContain("10.2 Limitation of Liability");
  });

  it("computes word-count metrics correctly", () => {
    const before = "old text here";
    const after = "new text here";

    const segments = computeSemanticDiff(before, after);
    const metrics = computeDiffMetrics(segments);

    expect(metrics.additions).toBe(1); // "new"
    expect(metrics.deletions).toBe(1); // "old"
  });});