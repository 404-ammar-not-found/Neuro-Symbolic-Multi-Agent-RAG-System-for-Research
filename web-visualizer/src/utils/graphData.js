export const STORAGE_KEY = "chroma-graph-cache";
export const EMPTY_GRAPH = { nodes: [], links: [] };

export const colorForGroup = (group) => {
  const g = group || "ungrouped";
  let hash = 0;
  for (let i = 0; i < g.length; i++) {
    hash = (hash * 31 + g.charCodeAt(i)) >>> 0;
  }
  const hue = hash % 360;
  return `hsl(${hue}, 70%, 55%)`;
};

export const buildGraphUrl = (base = import.meta.env.BASE_URL || "/") => {
  const normalized = base.endsWith("/") ? base : `${base}/`;
  return `${normalized}data/chroma-graph.json`;
};

export const isGraphShape = (data) =>
  Boolean(data && Array.isArray(data.nodes) && Array.isArray(data.links));

export const loadCachedGraph = () => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    return isGraphShape(parsed) ? parsed : null;
  } catch (err) {
    console.warn("Failed to read cached graph", err);
    return null;
  }
};

export const saveCachedGraph = (data) => {
  try {
    if (!isGraphShape(data)) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch (err) {
    console.warn("Failed to cache graph", err);
  }
};
