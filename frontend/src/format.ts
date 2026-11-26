export function formatDate(value?: string | null, locale = "en-GB") {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

export function formatMetric(value: number | null, unit: string, locale = "en-GB") {
  if (value == null) return "Unavailable";
  if (unit === "seconds") {
    const rounded = Math.round(value);
    if (rounded < 60) return `${rounded}s`;
    return `${Math.floor(rounded / 60)}m ${rounded % 60}s`;
  }
  if (unit === "minutes") {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value)} min`;
  }
  if (unit === "percentage") {
    return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(value)}%`;
  }
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
}
