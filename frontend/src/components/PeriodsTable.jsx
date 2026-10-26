import { fmtDateTime, fmtHours, fmtMw, fmtSigned, fmtTime } from "../format.js";

export default function PeriodsTable({ decision, demandMw }) {
  const hasDemand = demandMw !== null && demandMw !== undefined;
  return (
    <section className="card">
      <h2>Settlement periods — {decision.periods.length} periods</h2>
      <p className="hint">
        “Latest forecast” is the WINDFOR vintage published closest to, but before, gate closure. Error = forecast − actual
        (positive = wind was over-forecast, so thermal cover is needed).
      </p>
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Period (UK)</th>
              <th>Latest forecast</th>
              <th>Published</th>
              <th>Lead</th>
              <th>Buffer</th>
              <th>Planned wind</th>
              <th>Actual</th>
              <th>Error</th>
              <th>Covered?</th>
              {hasDemand && <th>Thermal central</th>}
              {hasDemand && <th>Thermal P90</th>}
            </tr>
          </thead>
          <tbody>
            {decision.periods.map((p) => (
              <tr key={p.start_time} className={p.forecast_mw === null ? "row-missing" : ""}>
                <td>{fmtTime(p.start_time)}</td>
                <td className="num">{fmtMw(p.forecast_mw)}</td>
                <td>{fmtDateTime(p.publish_time)}</td>
                <td className="num">{fmtHours(p.horizon_hours)}</td>
                <td className="num">{fmtMw(p.buffer_mw)}</td>
                <td className="num">{fmtMw(p.covered_wind_mw)}</td>
                <td className="num">{fmtMw(p.actual_mw)}</td>
                <td className="num">{fmtSigned(p.error_mw)}</td>
                <td>
                  {p.within_coverage === null ? "–" : p.within_coverage ? <span className="ok">yes</span> : <span className="bad">no</span>}
                </td>
                {hasDemand && <td className="num">{fmtMw(p.thermal_central_mw)}</td>}
                {hasDemand && <td className="num">{fmtMw(p.thermal_p90_mw)}</td>}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
