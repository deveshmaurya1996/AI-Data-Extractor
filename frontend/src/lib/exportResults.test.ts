import { escapeCsvCell, rowsToCsv } from "./exportResults";

describe("escapeCsvCell", () => {
  it("returns empty string for nullish", () => {
    expect(escapeCsvCell(null)).toBe("");
    expect(escapeCsvCell(undefined)).toBe("");
  });

  it("quotes when needed", () => {
    expect(escapeCsvCell('say "hi"')).toBe('"say ""hi"""');
    expect(escapeCsvCell("a,b")).toBe('"a,b"');
  });
});

describe("rowsToCsv", () => {
  it("builds header and rows", () => {
    const csv = rowsToCsv([
      { a: 1, b: "x" },
      { a: 2, b: "y" },
    ]);
    expect(csv).toBe("a,b\n1,x\n2,y");
  });

  it("returns empty string for no rows", () => {
    expect(rowsToCsv([])).toBe("");
  });
});
