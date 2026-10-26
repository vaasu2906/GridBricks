import { useEffect, useState } from "react";
import { fetchAccuracy, fetchDecision, fetchMeta } from "./api.js";
import Controls from "./components/Controls.jsx";
import SummaryCards from "./components/SummaryCards.jsx";
import ForecastChart from "./components/ForecastChart.jsx";
import PeriodsTable from "./components/PeriodsTable.jsx";
import AccuracyPanel from "./components/AccuracyPanel.jsx";
import VintagesPanel from "./components/VintagesPanel.jsx";

const DEFAULT_DAY = "2026-01-15";

export default function App() {
  const [meta, setMeta] = useState(null);
  const [deliveryDate, setDeliveryDate] = useState(DEFAULT_DAY);
  const [demandInput, setDemandInput] = useState("20000");
  const [decision, setDecision] = useState(null);
  const [accuracy, setAccuracy] = useState(null);
  const [selectedTarget, setSelectedTarget] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetchMeta().then(setMeta).catch((e) => setError(e.message));
    const ac = new AbortController();
    fetchAccuracy(undefined, undefined, ac.signal)
      .then(setAccuracy)
      .catch((e) => e.name !== "AbortError" && setError(e.message));
    return () => ac.abort();
  }, []);

  useEffect(() => {
    const demand = demandInput.trim() === "" ? undefined : Number(demandInput);
    const ac = new AbortController();
    setLoading(true);
    setError(null);
    fetchDecision(deliveryDate, demand, ac.signal)
      .then((d) => {
        setDecision(d);
        setSelectedTarget((prev) =>
          prev && d.periods.some((p) => p.start_time === prev) ? prev : d.periods[Math.floor(d.periods.length / 2)]?.start_time
        );
      })
      .catch((e) => e.name !== "AbortError" && setError(e.message))
      .finally(() => setLoading(false));
    return () => ac.abort();
  }, [deliveryDate, demandInput]);

  const demandMw = demandInput.trim() === "" ? null : Number(demandInput);

  return (
    <div className="app">
      <header className="topbar">
        <div>
          <h1>Wind Forecast Portal</h1>
          <p className="subtitle">
            Day-ahead wind outlook and forecast accuracy · GB national wind (Elexon) · UK local time
          </p>
        </div>
        {meta && (
          <span className={`source-badge source-${meta.source}`}>
            {meta.source === "sample" ? "Synthetic sample data" : "Live Elexon data"}
          </span>
        )}
      </header>

      <Controls
        deliveryDate={deliveryDate}
        onDeliveryDate={setDeliveryDate}
        demandInput={demandInput}
        onDemandInput={setDemandInput}
        meta={meta}
      />

      {error && <div className="alert">Could not load data: {error}</div>}
      {loading && !decision && <div className="muted">Loading decision view…</div>}

      {decision && (
        <>
          <SummaryCards decision={decision} />
          <div className="grid-2">
            <section className="card">
              <h2>Latest forecast at gate closure vs. outturn</h2>
              <p className="hint">
                Forecast used = most recent WINDFOR publication before gate closure at{" "}
                {meta ? `${String(meta.gate_closure_hour).padStart(2, "0")}:00 UK time on D−1` : "D−1"}.
                Dashed line = planned wind after the {meta ? Math.round(meta.buffer_quantile * 100) : 90}% confidence buffer.
              </p>
              <ForecastChart
                decision={decision}
                selectedTarget={selectedTarget}
                onSelect={setSelectedTarget}
              />
            </section>
            <VintagesPanel
              deliveryDate={deliveryDate}
              targetTime={selectedTarget}
              cutoffIso={decision.decision_cutoff}
            />
          </div>
          <PeriodsTable decision={decision} demandMw={demandMw} />
        </>
      )}

      {accuracy && <AccuracyPanel accuracy={accuracy} />}

      <footer className="footer">
        Forecasts and actuals: Elexon BMRS (FUELHH, WINDFOR). Calibration uses only days
        before each delivery day; figures are indicative and not trading advice.
      </footer>
    </div>
  );
}
