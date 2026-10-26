// Thin wrapper around the backend API. Base path is relative so the same build works
// behind the nginx proxy (Docker) and the Vite dev proxy.
const BASE = import.meta.env.VITE_API_BASE || "/api";

export async function getJson(path, params = {}, signal) {
  const qs = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== "") qs.set(k, v);
  });
  const url = `${BASE}${path}${qs.toString() ? `?${qs}` : ""}`;
  const res = await fetch(url, { signal });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail || detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return res.json();
}

export const fetchMeta = () => getJson("/meta");
export const fetchDecision = (deliveryDate, demandMw, signal) =>
  getJson("/decision", { delivery_date: deliveryDate, demand_mw: demandMw }, signal);
export const fetchAccuracy = (startDate, endDate, signal) =>
  getJson("/accuracy", { start_date: startDate, end_date: endDate }, signal);
export const fetchVintages = (targetTime, deliveryDate, signal) =>
  getJson("/forecast-vintages", { target_time: targetTime, delivery_date: deliveryDate }, signal);
