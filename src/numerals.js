// Answer normalisation for the Grammar tab's two numeral drills.
export function normNum(s) {
  return String(s || "").toLowerCase().replace(/ё/g, "е").replace(/[.,!?;:«»"()—–-]+/g, " ").replace(/\s+/g, " ").trim();
}
