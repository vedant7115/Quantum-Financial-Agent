import React, { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { getPlans, getUsage, getAccessKey, setAccessKey, UPGRADE_URL } from "../api";
import "../styles/quantum-next.css";

// Shown until the API answers (the backend may be waking up). Kept in step with
// PLANS in backend/services/billing_service.py, which is the source of truth.
const FALLBACK_PLANS = [
  { id: "free", name: "Free", price_inr: 0, price_usd: 0, features: ["3 research reports a day", "Overall view and 8-pillar scorecard", "Price, financials and news evidence", "US and Indian stocks"] },
  { id: "plus", name: "Plus", price_inr: 149, price_usd: 1.99, features: ["15 research reports a day", "Everything in Free", "Historical base rates for the current trend", "Bull case and bear case"] },
  { id: "pro", name: "Pro", price_inr: 499, price_usd: 5.99, features: ["60 research reports a day", "Everything in Plus", "Risk register", "What would change the view, with key dates", "PDF export"] },
];

const FAQ = [
  {
    q: "What counts as a report?",
    a: "Each company you analyse in a day counts once. Re-opening the same company the same day is free.",
  },
  {
    q: "Is this investment advice?",
    a: "No. Quantum organises public market data, company financials and news into a research brief. It does not tell you to buy or sell, and it does not know your circumstances.",
  },
  {
    q: "Where does the data come from?",
    a: "Prices, financials and headlines come from public market data and news feeds.",
  },
];

function formatPrice(plan, currency) {
  if (currency === "INR") return `₹${plan.price_inr.toLocaleString("en-IN")}`;
  return `$${plan.price_usd}`;
}

export default function PricingPage({ onStartResearch, onAccessChange }) {
  const [plans, setPlans] = useState(FALLBACK_PLANS);
  const [currency, setCurrency] = useState("INR");
  const [access, setAccess] = useState(null);
  const [keyInput, setKeyInput] = useState(getAccessKey());
  const [keyMsg, setKeyMsg] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    getPlans().then((d) => d?.plans?.length && setPlans(d.plans)).catch(() => {});
    getUsage().then(setAccess).catch(() => {});
  }, []);

  async function saveKey(e) {
    e.preventDefault();
    setSaving(true);
    setKeyMsg(null);
    setAccessKey(keyInput);
    try {
      const next = await getUsage();
      setAccess(next);
      onAccessChange?.(next);
      if (!keyInput.trim()) {
        setKeyMsg({ kind: "ok", text: "Access key removed. You are on the Free plan." });
      } else if (next.key_rejected) {
        setAccessKey("");
        setKeyMsg({ kind: "err", text: "That key is not valid or has expired. Check it and try again." });
      } else {
        setKeyMsg({ kind: "ok", text: `${next.plan_name} is active on this device.` });
      }
    } catch {
      setKeyMsg({ kind: "err", text: "Could not reach the server to check the key. Try again in a moment." });
    } finally {
      setSaving(false);
    }
  }

  const currentPlan = access?.plan || "free";

  return (
    <div className="qx">
      <div className="qx-wrap">
        <header className="qx-center">
          <p className="qx-eyebrow">Pricing</p>
          <h1 className="qx-title">Start free. Upgrade for the full picture.</h1>
          <p className="qx-lede">
            Every plan runs the same research engine on the same data. Paid plans add depth and more reports.
          </p>

          <div className="qx-seg" role="group" aria-label="Currency">
            {["INR", "USD"].map((c) => (
              <button key={c} type="button" aria-pressed={currency === c} onClick={() => setCurrency(c)}>
                {c === "INR" ? "₹ INR" : "$ USD"}
              </button>
            ))}
          </div>

          {access && (
            <p className="qx-status">
              You are on <strong>{access.plan_name}</strong> · {access.usage.remaining} of {access.usage.limit} reports left today
            </p>
          )}
        </header>

        <div className="qx-plans">
          {plans.map((plan) => {
            const featured = plan.id === "plus";
            const isCurrent = plan.id === currentPlan;
            const paid = plan.id !== "free";
            return (
              <section key={plan.id} className="qx-plan" data-featured={featured}>
                {featured && <span className="qx-plan-tag">Start here</span>}
                <h2 className="qx-plan-name">{plan.name}</h2>
                <div className="qx-price">
                  <span className="qx-price-amount">{formatPrice(plan, currency)}</span>
                  <span className="qx-price-unit">{paid ? "per month" : "forever"}</span>
                </div>
                <ul>
                  {plan.features.map((f) => (
                    <li key={f}>
                      <Check size={18} strokeWidth={2.5} aria-hidden="true" />
                      <span>{f}</span>
                    </li>
                  ))}
                </ul>
                {!paid ? (
                  <button type="button" className="qx-btn qx-btn-quiet" onClick={() => onStartResearch?.()}>
                    Start researching
                  </button>
                ) : isCurrent ? (
                  <button type="button" className="qx-btn qx-btn-quiet" disabled>
                    Your current plan
                  </button>
                ) : UPGRADE_URL ? (
                  <a className={`qx-btn ${featured ? "qx-btn-primary" : "qx-btn-quiet"}`} href={UPGRADE_URL} target="_blank" rel="noreferrer">
                    Get {plan.name}
                  </a>
                ) : (
                  <button type="button" className={`qx-btn ${featured ? "qx-btn-primary" : "qx-btn-quiet"}`} disabled>
                    Checkout opening soon
                  </button>
                )}
              </section>
            );
          })}
        </div>
        <p className="qx-note">Prices exclude applicable taxes.</p>

        <form className="qx-key" onSubmit={saveKey}>
          <h3 className="qx-h3">Have an access key?</h3>
          <p className="qx-body">Paste the key you received after purchase to unlock your plan on this device.</p>
          <div className="qx-key-row">
            <input
              className="qx-input"
              type="text"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="qk_plus_…"
              aria-label="Access key"
              autoComplete="off"
              spellCheck="false"
            />
            <button type="submit" className="qx-btn qx-btn-primary qx-btn-inline" disabled={saving}>
              {saving ? "Checking…" : "Apply key"}
            </button>
          </div>
          {keyMsg && <p className="qx-msg" data-kind={keyMsg.kind} role="status">{keyMsg.text}</p>}
        </form>

        <div className="qx-faq">
          {FAQ.map((item) => (
            <div key={item.q} className="qx-faq-item">
              <h3 className="qx-h3">{item.q}</h3>
              <p className="qx-body">{item.a}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
