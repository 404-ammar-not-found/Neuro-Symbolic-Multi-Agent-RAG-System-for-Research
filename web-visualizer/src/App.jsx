import React, { useEffect, useMemo, useState } from "react";
import GlobeGraph from "./components/GlobeGraph.jsx";
import ControlPanel from "./components/ControlPanel.jsx";
import { askQuestion, uploadPdf } from "./utils/api.js";
import {
  EMPTY_GRAPH,
  buildGraphUrl,
  colorForGroup,
  isGraphShape,
  loadCachedGraph,
  saveCachedGraph,
} from "./utils/graphData.js";

function endpointId(endpoint) {
  if (endpoint && typeof endpoint === "object") {
    return endpoint.id;
  }
  return endpoint;
}

function App() {
  const [search, setSearch] = useState("");
  const [showEdges, setShowEdges] = useState(true);
  const [groupFilter, setGroupFilter] = useState("all");
  const [highlightNode, setHighlightNode] = useState(null);
  const [activeNodeIds, setActiveNodeIds] = useState([]);
  const [graphData, setGraphData] = useState(EMPTY_GRAPH);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [uploadStatus, setUploadStatus] = useState("");
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [answer, setAnswer] = useState("");
  const [qaError, setQaError] = useState("");
  const [matches, setMatches] = useState([]);

  const loadGraph = async ({ preferCache = true } = {}) => {
    const cached = preferCache ? loadCachedGraph() : null;
    if (cached) {
      setGraphData(cached);
      setLoading(false);
    }

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

  useEffect(() => {
    loadGraph();
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
    const activeSet = new Set(activeNodeIds);
    const nodes = coloredData.nodes.filter((n) => {
      const matchesSearch = search
        ? n.id.toLowerCase().includes(search.toLowerCase()) ||
          (n.label || "").toLowerCase().includes(search.toLowerCase())
        : true;
      const matchesGroup = groupFilter === "all" || n.group === groupFilter;
      const usedInPrompt = activeSet.has(n.id);
      return (matchesSearch || usedInPrompt) && matchesGroup;
    });

    const nodeIds = new Set(nodes.map((n) => n.id));
    const links = coloredData.links.filter(
      (l) => nodeIds.has(endpointId(l.source)) && nodeIds.has(endpointId(l.target))
    );

    return { nodes, links };
  }, [search, groupFilter, coloredData, activeNodeIds]);

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

  const handleUpload = async (file) => {
    if (!file) return;
    try {
      setUploading(true);
      setUploadStatus("Uploading and ingesting...");
      setError("");
      const res = await uploadPdf(file);
      setUploadStatus(`${res.filename} ingested (${res.newChunks} new chunks).`);
      await loadGraph({ preferCache: false });
    } catch (err) {
      setUploadStatus("");
      setError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleAsk = async (query) => {
    if (!query) return;
    try {
      setAsking(true);
      setQaError("");
      setQuestion(query);
      const res = await askQuestion(query);
      const used = Array.isArray(res.usedNodeIds) ? res.usedNodeIds : [];
      setAnswer(res.answer || "");
      setMatches(Array.isArray(res.matches) ? res.matches : []);
      setActiveNodeIds(used);
      if (used.length > 0) {
        setHighlightNode(used[0]);
      }
    } catch (err) {
      setQaError(err.message || "Query failed.");
      setAnswer("");
      setMatches([]);
      setActiveNodeIds([]);
    } finally {
      setAsking(false);
    }
  };

  const focusNode = (nodeId) => {
    if (!nodeId) return;
    setHighlightNode(nodeId);
    setSearch(nodeId);
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
        activeNodeIds={activeNodeIds}
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
        onUploadFile={handleUpload}
        uploading={uploading}
        uploadStatus={uploadStatus}
        onAsk={handleAsk}
        asking={asking}
        question={question}
        answer={answer}
        qaError={qaError}
        matches={matches}
        onFocusNode={focusNode}
      />
    </div>
  );
}

export default App;
