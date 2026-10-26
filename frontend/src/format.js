// Formatting helpers. All clock times are shown in UK local time, because that is
// how the trading desk reads settlement periods.
const LONDON = "Europe/London";

const timeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  hour: "2-digit",
  minute: "2-digit",
});
const dateTimeFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  weekday: "short",
  day: "2-digit",
  month: "short",
  hour: "2-digit",
  minute: "2-digit",
});
const dayFmt = new Intl.DateTimeFormat("en-GB", {
  timeZone: LONDON,
  weekday: "short",
  day: "2-digit",
  month: "short",
});

export const fmtTime = (iso) => (iso ? timeFmt.format(new Date(iso)) : "–");
export const fmtDateTime = (iso) => (iso ? dateTimeFmt.format(new Date(iso)) : "–");
export const fmtDay = (iso) => (iso ? dayFmt.format(new Date(`${iso}T12:00:00Z`)) : "–");

export const fmtMw = (v, digits = 0) =>
  v === null || v === undefined ? "–" : `${Number(v).toLocaleString("en-GB", { maximumFractionDigits: digits, minimumFractionDigits: digits })}`;

export const fmtSigned = (v, digits = 0) => {
  if (v === null || v === undefined) return "–";
  const s = fmtMw(Math.abs(v), digits);
  return v > 0 ? `+${s}` : v < 0 ? `−${s}` : s;
};

export const fmtPct = (v, digits = 1) =>
  v === null || v === undefined ? "–" : `${(v * 100).toFixed(digits)}%`;

export const fmtHours = (v) => (v === null || v === undefined ? "–" : `${v.toFixed(1)}h`);
