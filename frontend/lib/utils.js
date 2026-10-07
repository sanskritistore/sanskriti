/**
 * Shared utilities — kept simple and non-technical.
 */

/** Format a number as Indian Rupees: 1500 → "₹1,500" */
export function formatRupees(amount) {
  if (amount === null || amount === undefined || isNaN(Number(amount))) {
    return "₹0";
  }
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(Number(amount));
}

/** Validate a 10-digit Indian mobile number */
export function isValidPhone(phone) {
  return /^[6-9]\d{9}$/.test(String(phone || "").replace(/\s|-/g, ""));
}

/** Validate a 6-digit OTP */
export function isValidOtp(otp) {
  return /^\d{6}$/.test(String(otp || "").trim());
}

/**
 * Build the simple report headline:
 * "₹X spent → Y customers" (architecture rule: money language, no jargon)
 */
export function reportHeadline(spent, customers) {
  return `${formatRupees(spent)} → ${customers ?? 0}`;
}

/** Simple fetch wrapper with error normalization (used outside APIProvider if needed) */
export async function apiFetch(url, options = {}) {
  try {
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`Request failed: ${res.status}`);
    return await res.json();
  } catch (err) {
    console.error("[apiFetch]", err);
    throw err;
  }
}
