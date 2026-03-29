export async function uploadPdf(file) {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch("/api/upload", {
    method: "POST",
    body: form,
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data?.detail || `Upload failed (${response.status})`;
    throw new Error(detail);
  }
  return data;
}

export async function askQuestion(question) {
  const response = await fetch("/api/ask", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = data?.detail || `Query failed (${response.status})`;
    throw new Error(detail);
  }
  return data;
}
