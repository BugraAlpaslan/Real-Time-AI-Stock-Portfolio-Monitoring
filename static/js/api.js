const API = window.location.origin;

export async function api(method, path, body) {
  const r = await fetch(`${API}${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let message = r.statusText;
    try {
      const err = await r.json();
      const detail = err.detail;
      if (detail && typeof detail === "object") {
        message = detail.code || detail.detail || JSON.stringify(detail);
        if (detail.code && detail.detail) {
          message = `${detail.code}: ${detail.detail}`;
        }
      } else {
        message = detail || err.code || message;
        if (err.code && !String(message).includes(err.code)) {
          message = `${err.code}: ${message}`;
        }
      }
    } catch {
      /* ignore parse errors */
    }
    const error = new Error(message);
    error.status = r.status;
    throw error;
  }
  if (r.status === 204) return null;
  return r.json();
}
