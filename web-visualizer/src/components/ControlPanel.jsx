import React, { useMemo, useState } from "react";

function ControlPanel({
  search,
  onSearch,
  showEdges,
  setShowEdges,
  groupFilter,
  setGroupFilter,
  groups,
  onUploadFile,
  uploading,
  uploadStatus,
  onAsk,
  asking,
  question,
  answer,
  qaError,
  matches,
  onFocusNode,
}) {
  const [input, setInput] = useState(search);
  const [queryInput, setQueryInput] = useState(question || "");
  const [file, setFile] = useState(null);

  const shortMatches = useMemo(() => (matches || []).slice(0, 8), [matches]);

  const onSubmit = (e) => {
    e.preventDefault();
    onSearch(input.trim());
  };

  const onAskSubmit = (e) => {
    e.preventDefault();
    onAsk(queryInput.trim());
  };

  const onUploadSubmit = async (e) => {
    e.preventDefault();
    if (!file) return;
    await onUploadFile(file);
  };

  return (
    <div className="panel">
      <h1>Chroma Globe</h1>
      <p className="muted">Upload PDFs, auto-ingest to ChromaDB, ask questions, and inspect prompt chunks.</p>

      <form onSubmit={onUploadSubmit} className="field section">
        <label>Upload PDF to data/ (auto-ingest)</label>
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
        />
        <button type="submit" disabled={!file || uploading}>
          {uploading ? "Uploading..." : "Upload + Parse"}
        </button>
        {uploadStatus && <div className="status">{uploadStatus}</div>}
      </form>

      <form onSubmit={onAskSubmit} className="field section">
        <label>Ask your RAG assistant</label>
        <textarea
          value={queryInput}
          onChange={(e) => setQueryInput(e.target.value)}
          placeholder="Type a research question"
          rows={3}
        />
        <button type="submit" disabled={asking || !queryInput.trim()}>
          {asking ? "Thinking..." : "Ask"}
        </button>
      </form>

      <div className="field section">
        <label>Answer</label>
        <div className="answer-box">{answer || "Answer will appear here."}</div>
        {qaError && <div className="error-inline">{qaError}</div>}
      </div>

      <div className="field section">
        <label>Retrieved chunks used in prompt</label>
        <div className="sources-list">
          {shortMatches.length === 0 && <div className="muted">No retrieved chunks yet.</div>}
          {shortMatches.map((match, idx) => {
            const meta = match.metadata || {};
            const chunkId = meta.id || `match-${idx + 1}`;
            const source = meta.source || "unknown";
            const chunk = meta.chunk_index ?? "?";
            const snippet = (match.document || "").replace(/\s+/g, " ").trim();
            return (
              <div className="source-item" key={`${chunkId}-${idx}`}>
                <button
                  className="source-chip"
                  type="button"
                  onClick={() => onFocusNode(meta.id)}
                  disabled={!meta.id}
                  title={source}
                >
                  {source.split("/").pop()} #chunk{chunk}
                </button>
                <div className="source-snippet">
                  {snippet ? `${snippet.slice(0, 140)}${snippet.length > 140 ? "..." : ""}` : "No text"}
                </div>
              </div>
            );
          })}
        </div>
      </div>

      <form onSubmit={onSubmit} className="field">
        <label>Search / focus</label>
        <div className="input-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Node id or label"
          />
          <button type="submit">Go</button>
        </div>
      </form>

      <div className="field">
        <label>Group filter</label>
        <select
          value={groupFilter}
          onChange={(e) => setGroupFilter(e.target.value)}
        >
          {groups.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
      </div>

      <div className="field toggle-row">
        <label>Show edges</label>
        <input
          type="checkbox"
          checked={showEdges}
          onChange={(e) => setShowEdges(e.target.checked)}
        />
      </div>
    </div>
  );
}

export default ControlPanel;
