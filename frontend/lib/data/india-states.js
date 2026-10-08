/**
 * भारत के राज्य + केंद्र शासित प्रदेश — REFERENCE DATA (बिंदु 18: No Hardcoding)
 *
 * यह सूची component/logic के अंदर नहीं, अलग data file में रहती है —
 * एक ही सच्चा स्रोत (single source of truth)। बदलना हो तो सिर्फ़ यहाँ बदलो।
 */

export const STATES = [
  "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
  "Delhi", "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
  "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
  "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab", "Rajasthan",
  "Sikkim", "Tamil Nadu", "Telangana", "Tripura", "Uttar Pradesh",
  "Uttarakhand", "West Bengal",
  "Jammu and Kashmir", "Ladakh", "Chandigarh", "Puducherry",
  "Andaman and Nicobar Islands", "Dadra and Nagar Haveli and Daman and Diu",
  "Lakshadweep",
];

/** नक्शे का आख़िरी सहारा: पूरे भारत का केंद्र (जब state geocode भी असफल हो) */
export const INDIA_CENTER = [20.5937, 78.9629];

/** नक्शे का शुरुआती zoom: राज्य-स्तर */
export const STATE_ZOOM = 7;
/** शहर-स्तर zoom (जब geocode सटीक मिले) */
export const CITY_ZOOM = 12;
