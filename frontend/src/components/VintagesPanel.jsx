import { useEffect, useState } from "react";
import { fetchVintages } from "../api.js";
import { fmtDateTime, fmtHours, fmtMw, fmtTime } from "../format.js";

// Shows how the forecast for one settlement period evolved before gate closure.
export default function VintagesPanel({ deliveryDate, targetTime, cutoffIso }) {
  const [state, setState] = useState({ vintages: null, error: null });

  useEffect(() => {
    if (!targetTime) return;
    const ac = new AbortController();
    setState({ vintages: null, error: null });
    fetchVintages(targetTime, deliveryDate, ac.signal)
      .then((r) => setState({ vintages: r.vintages, error: null }))
      .catch((e) => e.name !== "AbortError" && setState({ vintages: null, error: e.message }));
    return () => ac.abort();
  }, [deliveryDate, targetTime]);

  return (
    <section className="card">
      <h2>Forecast history · {targetTime ? fmtTime(targetTime) : "select a period"}</h2>
      <p className="hint">
        Every WINDFOR publication for this period. Rows at or before gate closure ({fmtDateTime(cutoffIso)}) are eligible;
        the highlighted one is the forecast used for the decision.
      </p>
      {state.error && <div className="alert">{state.error}</div>}
      {state.vintages && (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Published</th>
                <th>Lead</th>
                <th>Forecast</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {state.vintages.map((v) => (
                <tr key={v.publish_time} className={v.chosen ? "row-chosen" : v.published_before_cutoff ? "" : "row-late"}>
                  <td>{fmtDateTime(v.publish_time)}</td>
                  <td className="num">{fmtHours(v.horizon_hours)}</td>
                  <td className="num">{fmtMw(v.forecast_mw)} MW</td>
                  <td>
                    {v.chosen ? "used" : v.published_before_cutoff ? "superseded" : "after gate closure"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
