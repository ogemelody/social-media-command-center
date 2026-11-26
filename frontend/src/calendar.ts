export type CalendarDay = { date: Date; key: string; current: boolean };

export function calendarDays(cursor: Date): CalendarDay[] {
  const first = new Date(cursor.getFullYear(), cursor.getMonth(), 1);
  const mondayOffset = (first.getDay() + 6) % 7;
  const start = new Date(first);
  start.setDate(first.getDate() - mondayOffset);

  return Array.from({ length: 42 }, (_, index) => {
    const date = new Date(start);
    date.setDate(start.getDate() + index);
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    return { date, key, current: date.getMonth() === cursor.getMonth() };
  });
}
