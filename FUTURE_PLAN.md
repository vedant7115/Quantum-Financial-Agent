# Quantum — What to Build Next (simple plan)

Written 2026-11-20, after v2.1.0 went live. Plain language: what each step is, why it matters, and roughly how long it takes with Claude doing the coding and you reviewing.

---

## Where things stand today

- **The website works.** Anyone can open it and get 3 free reports a day.
- **Paid plans work, but by hand.** A Plus or Pro customer needs an **access key** (looks like `qk_pro_<expiry>_<signature>`). Today **you** create that key with one command and send it to the person. They paste it on the Pricing page and their plan unlocks.
- **No money is collected yet.** There is no Razorpay, so nobody can pay on the site.

---

## Your question: "Do we give customers this key?"

**Yes. The key is how the site knows who has paid.** What changes over time is **who makes the key**:

| Stage | How a customer gets access | Who does the work |
| :-- | :-- | :-- |
| **Now** | They pay you some other way (UPI, bank transfer). You run `python scripts/issue_access_key.py pro 30` and send them the key on WhatsApp or email. | You, by hand |
| **After Razorpay (step 2 below)** | They click "Buy Pro", pay on Razorpay's page, and the site **creates the key automatically** and shows it to them, also by email if you want. | The website |
| **Later, with accounts (step 4)** | They log in with email or Google. No key to copy; their account remembers their plan. Keys can stay as a backup. | The website |

So you can start selling **today** by hand, and Razorpay just automates the same thing.

**How the automatic version works (step 2), in 5 steps:**
1. The customer clicks **Buy Plus** or **Buy Pro** on the Pricing page.
2. Our backend asks Razorpay to create an order for ₹149 or ₹499.
3. Razorpay's own payment window opens. The customer pays with UPI, card or netbanking. **We never see card details.**
4. Razorpay tells our backend "payment successful". We check Razorpay's signature to make sure the message is genuine.
5. The backend creates the access key (the same kind you make today) and shows it on screen: "Your Pro key — save it."

---

## The plan, in order

### Step 1 — Fix company names and news on the live site
- **What:** on Render, Yahoo doesn't send company names, so the site shows "AAPL Corp." and some stocks get no news (AAPL showed "News flow: not assessed").
- **Fix:** get the name from another Yahoo call that works from Render, and search news by ticker too.
- **Why first:** every visitor sees it, and it makes reports worse.
- **Time:** about **1–2 hours**.
- **Status: done (v2.1.1, live 2026-11-21).** Still open: sector, industry and earnings date are empty on Render for the same reason.

### Step 2 — Razorpay payments (automatic keys)
- **What:** the "Buy" buttons, Razorpay checkout, payment check, automatic key on screen.
- **You must do yourself (Claude can't):**
  - Create a Razorpay account and finish its business verification (KYC): PAN, bank account, and a website with Terms, Privacy and Refund pages. Razorpay checks these. **This takes Razorpay 2–7 days.**
  - Put the Razorpay keys on Render (Claude will tell you the exact names).
- **Claude builds:**
  - two backend endpoints (create order, confirm payment);
  - the buttons and checkout on the Pricing page;
  - a "your key" screen;
  - Terms, Privacy and Refund pages;
  - tests using Razorpay's test mode.
- **Time:** about **1–2 days of building**, plus Razorpay's own approval time.
- **Note:** use **one-time payments for 30 days** first (simplest). Auto-renewing subscriptions can come later.

### Step 3 — Save things in a database
- **What:** today quotas, usage numbers and the record of who paid are kept in memory, so they're **wiped every time Render restarts**. Add a small free Postgres database (Render or Supabase free tier).
- **Why:** once people pay you, you must keep a record of every payment and key, for refunds, support and tax.
- **Time:** about **1 day**.
- **Best done together with step 2,** so payments are saved from day one.

### Step 4 — Login accounts (optional, later)
- **What:** sign in with email or Google instead of copying a key. Their plan follows them to any device.
- **Why later:** keys already work. Do this once you have regular paying users asking for it.
- **Time:** about **2–3 days**.

### Step 5 — Show the new v2.1 data on screen
- **What:** a "Mixed signals" badge and the three agent scores on the report page. The backend already sends them.
- **Time:** about **2–3 hours**.
- **Good for interviews** because it's visible.

### Step 6 — Before charging many people (business, not code)
| Item | Why | Rough cost |
| :-- | :-- | :-- |
| Licensed market data instead of Yahoo | Yahoo's terms don't allow paid products | ₹1,000–₹5,000+/month, depends on provider |
| Vercel Pro (or move the frontend) | Vercel's free plan doesn't allow commercial use | about $20/month |
| Render paid instance | Free instances sleep and are slow to wake | about $7/month |
| SEBI rules on research advice | Selling stock research in India may need registration; ask a CA or lawyer | Varies |

---

## Timeline at a glance

| When | Do |
| :-- | :-- |
| **This week** | Step 1 (names and news fix) and Step 5 (show mixed signals). You can sell Pro keys by hand right now. |
| **Next 1–2 weeks** | Apply to Razorpay (KYC). Meanwhile Claude builds steps 2 + 3 in Razorpay **test mode**. |
| **When Razorpay approves** | Switch to live keys, then real payments start. |
| **Later** | Step 4 (accounts) and the business items in step 6, once paying users arrive. |

**Building time in total:** about **4–6 working days**. Razorpay's approval runs alongside it.

---

## Keys and secrets — keep these safe

| Secret | Where it lives | What happens if it leaks |
| :-- | :-- | :-- |
| `ACCESS_KEY_SECRET` | Render, and your local `.env` (never in git) | Anyone could create free Pro keys; change it, and old keys stop working |
| `ADMIN_TOKEN` | Render only | Someone could see usage numbers and traces; change it |
| `GROQ_API_KEY` | Render, local `.env` | Someone could use your Groq allowance |
| Razorpay key secret (future) | Render only | Must never reach the frontend or git |

**To make a key by hand today:**
1. Put `ACCESS_KEY_SECRET=` (the same value as on Render) in your local `.env`.
2. Run:
```
python scripts/issue_access_key.py plus 30
python scripts/issue_access_key.py pro 30
```
The number is how many days the key lasts.
