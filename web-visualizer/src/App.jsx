import React, { useEffect, useMemo, useState } from "react";
import GlobeGraph from "./components/GlobeGraph.jsx";
import ControlPanel from "./components/ControlPanel.jsx";
import {
  EMPTY_GRAPH,
  buildGraphUrl,
  colorForGroup,
  isGraphShape,
  loadCachedGraph,
  saveCachedGraph,
} from "./utils/graphData.js";

function App() {
  const [search, setSearch] = useState("");
  const [showEdges, setShowEdges] = useState(true);
  const [groupFilter, setGroupFilter] = useState("all");
  const [highlightNode, setHighlightNode] = useState(null);
  const [graphData, setGraphData] = useState(EMPTY_GRAPH);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    const cached = loadCachedGraph();
    if (cached) {
      setGraphData(cached);
      setLoading(false);
    }

    const load = async () => {
      try {
        setRefreshing(Boolean(cached));
        if (!cached) setLoading(true);

        const url = buildGraphUrl();
        const res = await fetch(url, { cache: "no-cache" });
        if (!res.ok) throw new Error(`Failed to load data (${res.status})`);
        const json = await res.json();
        const next = isGraphShape(json) ? json : EMPTY_GRAPH;
        setGraphData(next);
        saveCachedGraph(next);
        setError("");
      } catch (err) {
        console.error(err);
        if (!cached) {
          setGraphData(EMPTY_GRAPH);
        }
        setError(
          cached
            ? "Showing cached graph data. Could not refresh latest copy."
            : "Could not load graph data. Ensure chroma-graph.json exists."
        );
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    };
    load();
  }, []);

  const coloredData = useMemo(() => {
    const nodes = graphData.nodes.map((n) => {
      const group = n.group || "ungrouped";
      const groupColor = colorForGroup(group);
      return {
        ...n,
        group,
        groupColor,
        color: n.color || groupColor,
      };
    });
    return { nodes, links: graphData.links };
  }, [graphData]);

  const groups = useMemo(() => {
    const g = new Set(coloredData.nodes.map((n) => n.group || "ungrouped"));
    return ["all", ...Array.from(g)];
  }, [coloredData]);

  const filteredData = useMemo(() => {
    const nodes = coloredData.nodes.filter((n) => {
      const matchesSearch = search
        ? n.id.toLowerCase().includes(search.toLowerCase()) ||
          (n.label || "").toLowerCase().includes(search.toLowerCase())
        : true;
      const matchesGroup = groupFilter === "all" || n.group === groupFilter;
      return matchesSearch && matchesGroup;
    });

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = coloredData.links.filter(
      (l) => nodeIds.has(l.source) && nodeIds.has(l.target)
    );

    return { nodes, links };
  }, [search, groupFilter, coloredData]);

  const onSearchSubmit = (value) => {
    setSearch(value);
    const match = coloredData.nodes.find(
      (n) =>
        n.id.toLowerCase() === value.toLowerCase() ||
        (n.label || "").toLowerCase() === value.toLowerCase()
    );
    if (match) {
      setHighlightNode(match.id);
    }
  };

  return (
    <div className="app">
      {loading && <div className="loading">Loading graph...</div>}
      {!loading && refreshing && (
        <div className="loading">Refreshing latest graph...</div>
      )}
      {error && <div className="error">{error}</div>}
      <GlobeGraph
        data={filteredData}
        highlightNode={highlightNode}
        showEdges={showEdges}
        onNodeHover={setHighlightNode}
        onNodeClick={setHighlightNode}
      />
      <ControlPanel
        search={search}
        onSearch={onSearchSubmit}
        showEdges={showEdges}
        setShowEdges={setShowEdges}
        groupFilter={groupFilter}
        setGroupFilter={setGroupFilter}
        groups={groups}
      />
    </div>
  );
}

export default App;
