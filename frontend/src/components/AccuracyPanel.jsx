import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { fmtDay, fmtMw, fmtPct } from "../format.js";

// Out-of-sample accuracy across the whole January scope. Each day's calibration uses only earlier data.
export default function AccuracyPanel({ accuracy }) {
  const o = accuracy.overall;
  const perDay = accuracy.per_day.map((d) => ({
    day: fmtDay(d.delivery_date),
    mae: d.accuracy.mae_mw === null ? null : Math.round(d.accuracy.mae_mw),
    coverage: d.coverage_rate,
  }));

  return (
    <section className="card">
      <h2>Forecast accuracy — January 2026 (out-of-sample)</h2>
      <div className="stats stats-compact">
        <div className="stat">
          <div className="stat-label">Overall MAE</div>
          <div className="stat-value">{fmtMw(o.mae_mw)} <span className="stat-unit">MW</span></div>
          <div className="stat-sub">{o.nmae_pct !== null ? `${o.nmae_pct.toFixed(1)}% of mean output` : ""}</div>
        </div>
        <div className="stat">
          <div className="stat-label">Overall RMSE</div>
          <div className="stat-value">{fmtMw(o.rmse_mw)} <span className="stat-unit">MW</span></div>
        </div>
        <div className="stat">
          <div className="stat-label">Buffer coverage</div>
          <div className="stat-value">{fmtPct(accuracy.coverage_rate)}</div>
          <div className="stat-sub">target 90% — check it is close</div>
        </div>
        <div className="stat">
          <div className="stat-label">Periods scored</div>
          <div className="stat-value">{o.n.toLocaleString("en-GB")}</div>
        </div>
      </div>

      <div className="grid-2">
        <div>
          <h3>Error by lead time</h3>
          <table>
            <thead>
              <tr>
                <th>Lead time</th>
                <th>Periods</th>
                <th>MAE (MW)</th>
                <th>RMSE (MW)</th>
                <th>Bias (MW)</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(accuracy.by_horizon).map(([label, b]) => (
                <tr key={label}>
                  <td>{label}</td>
                  <td className="num">{b.n}</td>
                  <td className="num">{fmtMw(b.mae_mw)}</td>
                  <td className="num">{fmtMw(b.rmse_mw)}</td>
                  <td className="num">{fmtMw(b.bias_mw)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div>
          <h3>Daily MAE (MW)</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={perDay} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
              <XAxis dataKey="day" tick={{ fontSize: 10 }} interval={3} />
              <YAxis tick={{ fontSize: 11 }} width={48} />
              <Tooltip formatter={(v) => [`${fmtMw(v)} MW`, "MAE"]} />
              <Bar dataKey="mae" fill="var(--c-forecast)" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
