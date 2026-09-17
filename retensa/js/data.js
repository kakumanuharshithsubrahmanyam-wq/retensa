/* ============================================================
   RETENSA — Mock Data Layer
   All numbers are illustrative demo data, not live model output.
   ============================================================ */

const CAUSES = ["Pricing", "Support", "Engagement", "Contract", "Usage Drop", "Onboarding"];
const CONTRACTS = ["Month-to-month", "One year", "Two year"];
const VALUES = ["LOW", "MEDIUM", "HIGH"];

function riskFromProbability(p) {
  if (p >= 80) return "CRITICAL";
  if (p >= 60) return "HIGH";
  if (p >= 35) return "MEDIUM";
  return "LOW";
}

function seededRandom(seed) {
  let s = seed % 2147483647;
  if (s <= 0) s += 2147483646;
  return function () {
    s = (s * 16807) % 2147483647;
    return (s - 1) / 2147483646;
  };
}

const rand = seededRandom(20260917);
function pick(arr) { return arr[Math.floor(rand() * arr.length)]; }
function randInt(min, max) { return Math.floor(rand() * (max - min + 1)) + min; }
function randFloat(min, max, digits = 1) {
  return parseFloat((rand() * (max - min) + min).toFixed(digits));
}

const CUSTOMER_IDS = [
  "C1024", "C1872", "C2938", "C4017", "C5129", "C6102", "C7218", "C8341",
  "C9027", "C10384", "C11728", "C12481", "C13920", "C14271", "C15832",
  "C16590", "C17204", "C18811", "C19345", "C20017"
];

function buildFeatureContributions(primaryCause, probability) {
  const pool = [
    { name: "Contract Type", weight: 28 },
    { name: "Monthly Charges", weight: 21 },
    { name: "Short Tenure", weight: 18 },
    { name: "Support Issues", weight: 14 },
    { name: "Low Engagement", weight: 9 },
    { name: "Payment Delays", weight: 7 },
  ];
  // bias the pool so it roughly matches the primary cause
  const causeMap = {
    "Pricing": "Monthly Charges",
    "Support": "Support Issues",
    "Engagement": "Low Engagement",
    "Contract": "Contract Type",
    "Usage Drop": "Low Engagement",
    "Onboarding": "Short Tenure",
  };
  const lead = causeMap[primaryCause] || "Contract Type";
  const sorted = [...pool].sort((a, b) => (a.name === lead ? -1 : b.name === lead ? 1 : 0));
  const scale = probability / 91.4;
  const positive = sorted.map((f) => ({ name: f.name, value: Math.round(f.weight * scale) }));
  const negative = [
    { name: "Online Security Add-on", value: -Math.round(6 * scale) },
    { name: "Long-term Usage History", value: -Math.round(4 * scale) },
  ];
  return { positive, negative };
}

const CUSTOMERS = CUSTOMER_IDS.map((id, i) => {
  const probability = i === 0 ? 91.4 : randFloat(18, 96, 1);
  const risk = riskFromProbability(probability);
  const cause = pick(CAUSES);
  const tenure = randInt(1, 60);
  const monthly = randInt(19, 149);
  const contract = risk === "LOW" ? pick(CONTRACTS.slice(1)) : pick(CONTRACTS);
  const supportRequests = randInt(0, 9);
  const engagementTrend = -randInt(0, 35);
  const value = pick(VALUES);
  const opportunity = Math.max(10, Math.min(99, Math.round(probability * 0.9 + randInt(-8, 8))));
  return {
    id,
    name: id,
    probability,
    risk,
    primaryCause: cause,
    tenure,
    monthlyCharges: monthly,
    contract,
    supportRequests,
    engagementTrend,
    customerValue: value,
    opportunityScore: opportunity,
    confidence: probability > 75 || probability < 25 ? "High" : "Medium",
    contributions: buildFeatureContributions(cause, probability),
    status: pick(["New", "New", "In Progress", "Completed"]),
  };
}).sort((a, b) => b.probability - a.probability);

const KPI_DATA = {
  totalCustomers: 7043,
  totalCustomersTrend: "+2.1% this month",
  highRisk: 1284,
  highRiskTrend: "+8.4% this month",
  criticalRisk: 317,
  criticalRiskTrend: "+3.9% this month",
  avgChurnProbability: 31.8,
  avgChurnTrend: "-1.2% this month",
  retentionOpportunities: 486,
  retentionOpportunitiesTrend: "+14 this week",
};

const RISK_SUMMARY = { LOW: 3586, MEDIUM: 2173, HIGH: 967, CRITICAL: 317 };

const CHURN_DRIVERS = [
  { name: "Contract Type", value: 31 },
  { name: "Monthly Charges", value: 24 },
  { name: "Tenure", value: 19 },
  { name: "Support Issues", value: 14 },
  { name: "Low Engagement", value: 9 },
  { name: "Payment Method", value: 3 },
];

function buildTrendSeries(days) {
  const out = [];
  let base = 34;
  for (let i = days; i >= 0; i--) {
    base += randFloat(-1.4, 1.4, 2);
    base = Math.max(24, Math.min(40, base));
    const d = new Date();
    d.setDate(d.getDate() - i);
    out.push({ date: d, value: parseFloat(base.toFixed(1)) });
  }
  return out;
}

const CHURN_TREND = {
  "7D": buildTrendSeries(7),
  "30D": buildTrendSeries(30),
  "90D": buildTrendSeries(90),
};

const RISK_BY_CONTRACT = [
  { label: "Month-to-month", value: 58 },
  { label: "One year", value: 27 },
  { label: "Two year", value: 15 },
];

const RISK_BY_TENURE = [
  { label: "0-6 mo", value: 61 },
  { label: "6-12 mo", value: 44 },
  { label: "1-2 yr", value: 29 },
  { label: "2yr+", value: 14 },
];

const RISK_BY_VALUE = [
  { label: "Low value", value: 22 },
  { label: "Medium value", value: 38 },
  { label: "High value", value: 34 },
];

const RISK_BY_CHARGES = [
  { label: "$0-40", value: 18 },
  { label: "$40-80", value: 33 },
  { label: "$80-120", value: 52 },
  { label: "$120+", value: 61 },
];

const AI_RESPONSES = {
  default: {
    text: "I can help you explore churn risk, root causes, and recommended retention actions across your customer base. Try one of the suggested prompts, or ask about a specific customer ID.",
  },
  "which customers should we save today": {
    text: "Based on predicted probability and customer value, the top three customers to prioritize today are C1024 (91.4%, HIGH value), C1872 (88.2%, HIGH value), and C2938 (84.7%, MEDIUM value). All three have retention opportunity scores above 80.",
    recommendation: { title: "Suggested focus", body: "Start outreach with C1024 — critical risk, high value, pricing-driven." },
  },
  "why is c1024 at risk": {
    text: "C1024 has a 91.4% predicted churn probability. The strongest contributing factors are contract type (+28%), monthly charges (+21%), short tenure (+18%), and support issues (+14%).",
    recommendation: { title: "Recommended action", body: "Offer an annual plan incentive within 7 days and route to priority support." },
  },
  "what are the biggest churn drivers": {
    text: "Across the full customer base, contract type (31%) and monthly charges (24%) are the two largest churn drivers, followed by tenure (19%) and support issues (14%). Engagement and payment method contribute less.",
    recommendation: { title: "Portfolio insight", body: "Month-to-month contracts account for the largest share of high-risk accounts." },
  },
  "show me high-value customers at risk": {
    text: "There are 214 HIGH-value customers currently flagged MEDIUM risk or above. The largest concentration sits in the 60-85% probability band, primarily driven by pricing and support friction.",
    recommendation: { title: "Suggested focus", body: "Prioritize high-value accounts in the CRITICAL and HIGH bands first — they carry the greatest revenue impact." },
  },
  "which intervention should we prioritize": {
    text: "Annual plan incentives show the strongest simulated impact on contract-driven risk, while priority support routing has the largest effect on support-driven risk. For this week's queue, pricing-driven cases outnumber support-driven cases roughly 2 to 1.",
    recommendation: { title: "Recommended sequencing", body: "Run pricing incentives first, then route remaining support-driven accounts to priority support." },
  },
};
