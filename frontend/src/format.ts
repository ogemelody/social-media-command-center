export function formatDate(value?: string | null, locale = "en-GB") {
  if (!value) return "Not yet";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "UTC",
  }).format(new Date(value));
}
