import { fmtDateTime, fmtHours, fmtMw, fmtPct } from "../format.js";

function Card({ label, value, unit, sub }) {
  return (
    <div className="stat">
      <div className="stat-label">{label}</div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit"> {unit}</span>}
      </div>
      {sub && <div className="stat-sub">{sub}</div>}
    </div>
  );
}

export default function SummaryCards({ decision }) {
  const s = decision.summary;
  const acc = s.accuracy;
  const hasDemand = decision.demand_mw !== null && decision.demand_mw !== undefined;
  return (
    <section className="stats">
      <Card
        label="Gate closure"
        value={fmtDateTime(decision.decision_cutoff)}
        sub={`Forecasts published after this are excluded`}
      />
      <Card
        label="Mean lead time"
        value={fmtHours(s.mean_horizon_hours)}
        sub={`${s.periods_without_forecast} periods without a forecast`}
      />
      <Card
        label="Forecast MAE"
        value={fmtMw(acc.mae_mw)}
        unit="MW"
        sub={acc.nmae_pct !== null ? `${acc.nmae_pct.toFixed(1)}% of mean output · RMSE ${fmtMw(acc.rmse_mw)} MW` : "no outturn yet"}
      />
      <Card
        label="Bias (forecast − actual)"
        value={acc.bias_mw === null ? "–" : `${acc.bias_mw > 0 ? "+" : ""}${fmtMw(acc.bias_mw)}`}
        unit="MW"
        sub={acc.bias_mw > 0 ? "forecast too high on average" : acc.bias_mw < 0 ? "forecast too low on average" : ""}
      />
      <Card
        label="Buffer coverage"
        value={fmtPct(s.coverage_rate)}
        sub="share of periods where outturn met the buffered wind level (target 90%)"
      />
      <Card
        label={hasDemand ? "Thermal to procure (P90)" : "Wind buffer total"}
        value={fmtMw(hasDemand ? s.thermal_p90_mwh : s.planning_buffer_mwh)}
        unit="MWh"
        sub={
          hasDemand
            ? `central ${fmtMw(s.thermal_central_mwh)} MWh · difference is the risk premium`
            : "enter demand above to size thermal procurement"
        }
      />
    </section>
  );
}
