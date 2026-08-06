# 📱 Molum Mini App — Integration Guide & Technical Manual

This guide outlines how to integrate the new **Snapshot & Token Claim** and **Community Contests** systems from the Telegram Bot database into your **Solana Mini App (Next.js / React / Vercel)**.

Because both the Telegram Bot and the Mini App share the exact same **Supabase / PostgreSQL database**, integration is highly streamlined, secure, and operates in real-time.

---

## 🗄️ 1. Database Schema Reference

The tables used by these features are fully declared in `schema.sql`:

### A. Table: `claim_snapshots` (Token Claim Allocation)
Stores the snapshot balances and allocated tokens once the admin triggers a snapshot.
*   `id` (`bigint`, Primary Key)
*   `telegram_id` (`bigint`, Unique, references `profiles.telegram_id`)
*   `wallet_address` (`text`, Solana wallet address captured during snapshot)
*   `points_snap` (`integer`, User's total points at the moment of snapshot)
*   `tokens_allocated` (`numeric(20,6)`, Allocated tokens calculated based on the custom conversion rate)
*   `claimed` (`boolean`, default `FALSE`, turns `TRUE` once claimed)
*   `claimed_at` (`timestamptz`, timestamp of claim)

### B. Table: `contests` (Active Contests)
Stores the community contests designed by admins.
*   `id` (`bigint`, Primary Key)
*   `title` (`text`, Contest name, e.g., "Fox Meme Contest")
*   `description` (`text`, Instructions and terms)
*   `reward_points` (`integer`, Point reward for approved submissions)
*   `is_active` (`boolean`, default `TRUE`)

### C. Table: `contest_submissions` (Submissions Log)
Stores links submitted by users for specific contests.
*   `id` (`bigint`, Primary Key)
*   `contest_id` (`bigint`, references `contests.id`)
*   `telegram_id` (`bigint`, references `profiles.telegram_id`)
*   `submission_link` (`text`, Twitter post URL, story screenshot, etc.)
*   `status` (`text`, can be `'pending'`, `'approved'`, `'rejected'`)

---

## 🚀 2. Snapshot & Claim System Integration

When the admin runs a snapshot, the bot captures all connected wallet addresses and allocates tokens. In your Mini App, you need to show the claimable tokens and provide a **"Claim"** button.

### A. Fetching the Claim Snapshot (Frontend)
To check if the user has an allocated token claim, query the `claim_snapshots` table using the user's `telegram_id` (retrieved from Telegram WebApp InitData).

```javascript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
  process.env.NEXT_PUBLIC_SUPABASE_URL,
  process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY
);

// Fetch Claim Allocation for user
async function getClaimAllocation(telegramId) {
  const { data, error } = await supabase
    .from('claim_snapshots')
    .select('points_snap, tokens_allocated, claimed, wallet_address')
    .eq('telegram_id', telegramId)
    .single();

  if (error && error.code !== 'PGRST116') { // PGRST116 = No rows found (which is normal if no snapshot was taken yet)
    console.error('Error fetching claim details:', error);
    return null;
  }
  return data; // returns allocation object or null
}
```

### B. Implementing the "Claim Tokens" Button (Frontend)
When the user clicks "Claim Tokens" in the Mini App, you should set `claimed = true` in the database. 

*(Optional: In production, you can also trigger a real Solana smart contract token transfer here, but marking it in the shared DB ensures that users cannot double-claim and records their claim history).*

```javascript
async function claimTokens(telegramId) {
  const { data, error } = await supabase
    .from('claim_snapshots')
    .update({
      claimed: true,
      claimed_at: new Date().toISOString()
    })
    .eq('telegram_id', telegramId)
    .select();

  if (error) {
    console.error('Failed to claim tokens:', error);
    return { success: false, error };
  }
  return { success: true, data };
}
```

---

## 🏆 3. Community Contests Integration

Admins can launch contests (like Meme Competitions) via the Telegram admin panel. Your Mini App can display these active contests and let users submit their work directly from the interface.

### A. Fetching Active Contests (Frontend)
Display a list of active contests for users to participate in.

```javascript
async function getActiveContests() {
  const { data, error } = await supabase
    .from('contests')
    .select('id, title, description, reward_points')
    .eq('is_active', true)
    .order('created_at', { ascending: false });

  if (error) {
    console.error('Error fetching contests:', error);
    return [];
  }
  return data;
}
```

### B. Checking Submission Status (Frontend)
Show whether the user has already submitted a link, and show the status (`Pending / Approved / Rejected`).

```javascript
async function getUserSubmission(telegramId, contestId) {
  const { data, error } = await supabase
    .from('contest_submissions')
    .select('id, submission_link, status')
    .eq('telegram_id', telegramId)
    .eq('contest_id', contestId)
    .single();

  if (error && error.code !== 'PGRST116') {
    console.error('Error fetching user submission status:', error);
    return null;
  }
  return data; // Returns submission details or null if not participated
}
```

### C. Submitting a Contest Link (Frontend)
Provide an input field where users can paste their link (Twitter link, story link, etc.) and submit.

```javascript
async function submitContestEntry(telegramId, contestId, link) {
  const { data, error } = await supabase
    .from('contest_submissions')
    .upsert({
      telegram_id: telegramId,
      contest_id: contestId,
      submission_link: link,
      status: 'pending' // Re-sets status to pending if updated
    }, { on_conflict: 'telegram_id,contest_id' })
    .select();

  if (error) {
    console.error('Failed to submit entry:', error);
    return { success: false, error };
  }
  return { success: true, data };
}
```

---

## 👥 4. Continuous Referral Accumulation

Referrals operate continuously and are shared in real-time.

### A. Displaying Referrals on Mini App Dashboard
You can display the user's total referrals and referral code on their profile dashboard.

```javascript
async function getUserDashboardData(telegramId) {
  const { data, error } = await supabase
    .from('profiles')
    .select('referral_code, referral_count, total_points')
    .eq('telegram_id', telegramId)
    .single();

  if (error) {
    console.error('Failed to fetch user dashboard data:', error);
    return null;
  }
  return data; // Returns { referral_code: "MOL582...", referral_count: 5, total_points: 1250 }
}
```

### B. Displaying Invited Friends List
Show a list of friends that the user has successfully invited:

```javascript
async function getInvitedFriends(telegramId) {
  const { data, error } = await supabase
    .from('profiles')
    .select('username, first_name, is_subscribed, created_at')
    .eq('referred_by', telegramId)
    .order('created_at', { ascending: false });

  if (error) {
    console.error('Failed to fetch invited friends:', error);
    return [];
  }
  return data; // Returns list of invited profiles
}
```

---

## ⚡ 5. Ideal UI/UX flow for Mini App Integration

1.  **Dashboard Screen**:
    *   Show a beautiful countdown timer until listing day (fetch `listing_date` from `settings` table).
    *   Display `total_points`, `referral_count`, and the shareable `referral_code` (which they can tap to copy).
2.  **Claim Screen** (only accessible or visible if `token_status` in `settings` is `'live'`):
    *   Fetch `claim_snapshots` record for the logged-in user.
    *   If no row exists, say: *"You didn't qualify for this snapshot. Link your wallet and stay tuned for the next one!"*
    *   If a row exists and `claimed === false`:
      Show the amount of allocated tokens (`tokens_allocated`) and a big orange **"Claim $MOLUM Tokens"** button.
    *   Once clicked, show an animation and update `claimed = true` in Supabase.
3.  **Contests Screen**:
    *   Fetch active contests. Display them with card layouts showing Title, Description, and the Point Reward.
    *   Provide an input text field: `"Paste your submission link here (Twitter/Story/Meme)"`.
    *   If they already submitted, show: `"Status: PENDING ⏳"` or `"Status: APPROVED ✅ (+500 Points)"`.
