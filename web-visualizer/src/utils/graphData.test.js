import { describe, expect, it } from "vitest";
import {
  buildGraphUrl,
  colorForGroup,
  isGraphShape,
} from "./graphData";

describe("graphData utils", () => {
  it("produces deterministic colors per group", () => {
    const g1 = colorForGroup("alpha");
    const g2 = colorForGroup("alpha");
    const g3 = colorForGroup("beta");
    expect(g1).toBe(g2);
    expect(g1).not.toBe(g3);
  });

  it("builds a graph URL with normalized base", () => {
    expect(buildGraphUrl("/" )).toBe("/data/chroma-graph.json");
    expect(buildGraphUrl("/foo")).toBe("/foo/data/chroma-graph.json");
    expect(buildGraphUrl("/bar/" )).toBe("/bar/data/chroma-graph.json");
  });

  it("validates graph shape", () => {
    expect(isGraphShape({ nodes: [], links: [] })).toBe(true);
    expect(isGraphShape({ nodes: [] })).toBe(false);
    expect(isGraphShape(null)).toBe(false);
  });
});
