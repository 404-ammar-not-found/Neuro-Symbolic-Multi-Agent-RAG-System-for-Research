import React, { useState } from "react";

function ControlPanel({
  search,
  onSearch,
  showEdges,
  setShowEdges,
  groupFilter,
  setGroupFilter,
  groups,
}) {
  const [input, setInput] = useState(search);

  const onSubmit = (e) => {
    e.preventDefault();
    onSearch(input.trim());
  };

  return (
    <div className="panel">
      <h1>Chroma Globe</h1>
      <p className="muted">Explore chunk embeddings in 3D.</p>

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
