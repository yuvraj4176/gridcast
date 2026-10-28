export function formatNumber(n?: number | null): string {
  if (n === undefined || n === null || isNaN(n)) return "-";
  return n.toLocaleString(undefined, { maximumFractionDigits: 0 });
}

export function formatDate(dateStr?: string): string {
  if (!dateStr) return "";
  return new Date(dateStr).toLocaleString();
}
