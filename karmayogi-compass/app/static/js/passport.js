// Karmayogi Compass — Passport page.
// Renders the real /skillgap/{user_id} table (Required vs. Current vs. Gap
// per domain) and asks Compass AI for one short, real summary of the
// user's actual priority gap — no fabricated "48% previous assessment /
// 72% course logs" sub-metrics, since the backend doesn't track those.

const KC_DOMAIN_LABELS_P = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

async function kcLoadPassport () {
  const user = kcGetUser();
  if (!user || !user.user_id) return;

  const tbody = document.getElementById('gapTableBody');
  const designationLine = document.getElementById('designationLine');

  let skillgap;
  try {
    const res = await kcAuthFetch(`/skillgap/${user.user_id}`);
    if (!res.ok) throw new Error('Could not load skill-gap data');
    skillgap = await res.json();
  } catch (e) {
    tbody.innerHTML = '<tr><td colspan="5" class="text-sm" style="color:var(--red); padding:16px;">Could not load your skill-gap data. Try refreshing.</td></tr>';
    return;
  }

  designationLine.textContent = `Requirements shown are for your designation: ${skillgap.designation}.`;

  tbody.innerHTML = '';
  skillgap.gaps.forEach((g) => {
    const label = KC_DOMAIN_LABELS_P[g.domain] || g.domain;
    let statusBadge;
    if (g.gap <= 0) statusBadge = '<span class="badge green">✓ Met Requirement</span>';
    else if (g.domain === skillgap.priority_domain) statusBadge = '<span class="badge red">Priority Gap</span>';
    else statusBadge = '<span class="badge outline">In Progress</span>';

    const tr = document.createElement('tr');
    if (g.domain === skillgap.priority_domain) tr.className = 'row-selected';
    tr.innerHTML = `
      <td>${g.domain === skillgap.priority_domain ? `<b>${label}</b>` : label}</td>
      <td class="cell-metric">${Math.round(g.required)}</td>
      <td class="cell-metric">${Math.round(g.current)}</td>
      <td class="cell-metric">${Math.round(g.gap)}</td>
      <td>${statusBadge}</td>
    `;
    tbody.appendChild(tr);
  });

  if (skillgap.priority_domain) {
    const top = skillgap.gaps.find((g) => g.domain === skillgap.priority_domain);
    document.getElementById('gapSummaryCard').hidden = false;
    document.getElementById('summaryDomain').textContent = KC_DOMAIN_LABELS_P[skillgap.priority_domain] || skillgap.priority_domain;
    kcLoadAiSummary(skillgap.designation, top);
  }
}

async function kcLoadAiSummary (designation, gap) {
  const summaryEl = document.getElementById('aiGapSummary');
  const context = `Competency passport for a ${designation}. Priority gap: ${gap.domain} — ` +
    `current score ${Math.round(gap.current)}/100, required ${Math.round(gap.required)}/100, ` +
    `gap of ${Math.round(gap.gap)} points.`;
  try {
    const res = await kcAuthFetch('/compass-ai/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        context,
        question: 'In one short sentence, summarize this gap and what closing it would mean for this official\'s readiness.',
      }),
    });
    const data = res.ok ? await res.json() : null;
    summaryEl.textContent = data ? data.answer : 'Compass AI summary unavailable right now.';
  } catch (e) {
    summaryEl.textContent = 'Compass AI summary unavailable right now.';
  }
}

document.addEventListener('DOMContentLoaded', kcLoadPassport);
