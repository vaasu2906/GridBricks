import { fmtDay } from "../format.js";

export default function Controls({ deliveryDate, onDeliveryDate, demandInput, onDemandInput, meta }) {
  return (
    <section className="controls card">
      <label>
        Delivery day
        <input
          type="date"
          value={deliveryDate}
          min={meta?.decision_start}
          max={meta?.decision_end}
          onChange={(e) => e.target.value && onDeliveryDate(e.target.value)}
        />
      </label>
      <label>
        Expected demand (MW, flat)
        <input
          type="number"
          min="0"
          step="100"
          placeholder="optional"
          value={demandInput}
          onChange={(e) => onDemandInput(e.target.value)}
        />
      </label>
      <p className="hint controls-note">
        {meta
          ? `Purchase decisions in scope: ${fmtDay(meta.decision_start)} – ${fmtDay(meta.decision_end)} 2026.`
          : "Loading scope…"}{" "}
        Demand is an input you provide; the wind data itself comes only from Elexon.
      </p>
    </section>
  );
}
