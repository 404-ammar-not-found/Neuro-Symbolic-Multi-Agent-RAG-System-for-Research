const colors = ["#7ee0ff", "#f7b3ff", "#7affc5", "#ffc27a", "#9fa7ff"];

function assignColors(groups) {
  const map = new Map();
  let i = 0;
  for (const g of groups) {
    map.set(g, colors[i % colors.length]);
    i += 1;
  }
  return map;
}

const nodesRaw = Array.from({ length: 60 }).map((_, i) => {
  const group = `group-${(i % 6) + 1}`;
  return {
    id: `node-${i + 1}`,
    label: `Chunk ${i + 1}`,
    group,
  };
});

const groups = new Set(nodesRaw.map((n) => n.group));
const colorMap = assignColors(groups);

const nodes = nodesRaw.map((n) => ({ ...n, groupColor: colorMap.get(n.group) }));

const links = [];
for (let i = 0; i < nodes.length; i++) {
  const target = (i + 1) % nodes.length;
  links.push({ source: nodes[i].id, target: nodes[target].id });
  const skip = (i + 7) % nodes.length;
  links.push({ source: nodes[i].id, target: nodes[skip].id });
}

export default { nodes, links };
