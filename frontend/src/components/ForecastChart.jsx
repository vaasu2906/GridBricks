import {
  CartesianGrid,
  Legend,
  Line,
  ComposedChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { fmtMw, fmtTime } from "../format.js";

export default function ForecastChart({ decision, selectedTarget, onSelect }) {
  const data = decision.periods.map((p) => ({
    t: p.start_time,
    label: fmtTime(p.start_time),
    forecast: p.forecast_mw,
    actual: p.actual_mw,
    covered: p.covered_wind_mw,
    demand: decision.demand_mw ?? null,
  }));

  const handleClick = (state) => {
    if (state && state.activeLabel) {
      const hit = decision.periods.find((p) => fmtTime(p.start_time) === state.activeLabel);
      if (hit) onSelect(hit.start_time);
    }
  };

  const selectedLabel = selectedTarget ? fmtTime(selectedTarget) : null;

  return (
    <div className="chart">
      <ResponsiveContainer width="100%" height={340}>
        <ComposedChart data={data} onClick={handleClick} margin={{ top: 8, right: 16, bottom: 0, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
          <XAxis dataKey="label" interval={5} tick={{ fontSize: 12 }} />
          <YAxis
            tick={{ fontSize: 12 }}
            tickFormatter={(v) => `${Math.round(v / 1000)} GW`}
            width={56}
          />
          <Tooltip
            formatter={(v, name) => [v === null || v === undefined ? "–" : `${fmtMw(v)} MW`, name]}
            labelFormatter={(l) => `Settlement period ${l} UK`}
          />
          <Legend />
          <Line type="monotone" dataKey="forecast" name="Forecast at gate closure" stroke="var(--c-forecast)" strokeWidth={2} dot={false} connectNulls={false} />
          <Line type="monotone" dataKey="actual" name="Actual outturn" stroke="var(--c-actual)" strokeWidth={2} dot={false} connectNulls={false} />
          <Line type="monotone" dataKey="covered" name="Planned wind (buffered)" stroke="var(--c-covered)" strokeWidth={2} strokeDasharray="6 4" dot={false} connectNulls={false} />
          {decision.demand_mw !== null && decision.demand_mw !== undefined && (
            <Line type="monotone" dataKey="demand" name="Demand (input)" stroke="var(--c-demand)" strokeDasharray="2 4" dot={false} />
          )}
        </ComposedChart>
      </ResponsiveContainer>
      <p className="hint">Click the chart to inspect a settlement period’s forecast history.{selectedLabel ? ` Selected: ${selectedLabel}.` : ""}</p>
    </div>
  );
}
