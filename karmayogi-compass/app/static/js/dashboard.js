// Karmayogi Compass — dashboard data binding.
// Pulls live data from /api/v1 (profile, skillgap, recommendations) and
// fills in the dashboard markup, then re-runs the gauge/bar animations
// from main.js now that the real data-* attributes are in place.

const KC_DOMAIN_LABELS = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

const KC_DOMAIN_SCORE_FIELD = {
  statistical: 'statistical_score',
  technical: 'technical_score',
  digital_gov: 'digital_gov_score',
  managerial: 'managerial_score',
};

function kcSetText (id, text) {
  const el = document.getElementById(id);
  if (el) el.textContent = text;
}

async function kcLoadDashboard () {
  const user = kcGetUser();
  if (!user || !user.user_id) return;

  let profile, skillgap, recommendations;
  try {
    const [profileRes, skillgapRes, recsRes] = await Promise.all([
      kcAuthFetch('/profile/me'),
      kcAuthFetch(`/skillgap/${user.user_id}`),
      kcAuthFetch(`/recommendations/${user.user_id}`),
    ]);
    if (!profileRes.ok) throw new Error('Could not load profile');
    profile = await profileRes.json();
    skillgap = skillgapRes.ok ? await skillgapRes.json() : null;
    recommendations = recsRes.ok ? await recsRes.json() : null;
  } catch (err) {
    kcSetText('overallSubtext', 'Could not load your competency data. Try refreshing the page.');
    return;
  }

  kcRenderOverallScore(profile);
  kcRenderDomainBars(profile, skillgap);
  kcRenderBiggestGap(skillgap, profile);
  kcRenderRecommendedCourse(recommendations);

  // Re-run the gauge/bar animations now that real data-* attributes are set.
  if (typeof initGauges === 'function') initGauges();
  if (typeof initBars === 'function') initBars();
}

function kcRenderOverallScore (profile) {
  const scores = [
    profile.statistical_score,
    profile.technical_score,
    profile.digital_gov_score,
    profile.managerial_score,
  ];
  const overall = Math.round(scores.reduce((a, b) => a + b, 0) / scores.length);

  const gaugeEl = document.getElementById('overallGauge');
  if (gaugeEl) gaugeEl.dataset.value = String(overall);
  kcSetText('overallScore', String(overall));

  const badge = document.getElementById('overallBadge');
  if (badge) {
    badge.textContent = `${profile.designation} · ${profile.department}`;
    badge.className = 'badge outline';
  }
  kcSetText('overallSubtext', 'Live score across your 4 competency domains.');
}

function kcRenderDomainBars (profile, skillgap) {
  const gapByDomain = {};
  if (skillgap && skillgap.gaps) {
    skillgap.gaps.forEach((g, i) => { gapByDomain[g.domain] = { ...g, rank: i }; });
  }

  Object.keys(KC_DOMAIN_LABELS).forEach((domain) => {
    const field = KC_DOMAIN_SCORE_FIELD[domain];
    const value = Math.round(profile[field]);
    const scoreEl = document.getElementById(`score-${domain}`);
    const barEl = document.getElementById(`bar-${domain}`);
    const gapInfo = gapByDomain[domain];
    const isPriority = gapInfo && gapInfo.rank === 0 && gapInfo.gap > 0;

    if (scoreEl) {
      scoreEl.textContent = isPriority ? `${value}/100 · Critical` : `${value}/100`;
      scoreEl.className = isPriority ? 'comp-score critical' : 'comp-score';
    }
    if (barEl) {
      barEl.dataset.target = String(value);
      barEl.className = isPriority ? 'bar-fill critical' : 'bar-fill';
    }
  });
}

function kcRenderBiggestGap (skillgap, profile) {
  const domainEl = document.getElementById('gapDomain');
  const descEl = document.getElementById('gapDescription');
  const currentEl = document.getElementById('gapCurrent');
  const requiredEl = document.getElementById('gapRequired');
  const pointsEl = document.getElementById('gapPoints');
  const cardEl = document.getElementById('gapCard');

  const top = skillgap && skillgap.gaps && skillgap.gaps[0];

  if (!top || top.gap <= 0) {
    if (domainEl) domainEl.textContent = 'All requirements met';
    if (descEl) {
      descEl.textContent = `Your scores currently meet the requirement across all 4 domains for ${
        profile.designation || 'your role'
      }. Keep learning to stay ahead.`;
    }
    if (currentEl) currentEl.textContent = '—';
    if (requiredEl) requiredEl.textContent = '—';
    if (pointsEl) pointsEl.textContent = '0';
    if (cardEl) cardEl.style.borderColor = '';
    return;
  }

  const label = KC_DOMAIN_LABELS[top.domain] || top.domain;
  if (domainEl) domainEl.textContent = label;
  if (descEl) {
    descEl.textContent = `Your current score in ${label} sits ${Math.round(top.gap)} points below the requirement for a ${
      profile.designation || 'your role'
    }.`;
  }
  if (currentEl) currentEl.textContent = String(Math.round(top.current));
  if (requiredEl) requiredEl.textContent = String(Math.round(top.required));
  if (pointsEl) pointsEl.textContent = String(Math.round(top.gap));
}

function kcRenderRecommendedCourse (recommendations) {
  const titleEl = document.getElementById('courseTitle');
  const metaEl = document.getElementById('courseMeta');
  const chipEl = document.getElementById('courseDomainChip');
  const descEl = document.getElementById('courseDescription');
  const launchLink = document.getElementById('courseLaunchLink');
  const startLink = document.getElementById('courseStartLink');

  const course = recommendations && recommendations.courses && recommendations.courses[0];

  if (!course) {
    if (titleEl) titleEl.textContent = 'No recommendations right now';
    if (metaEl) metaEl.textContent = 'You\u2019re meeting your role\u2019s requirements across all domains.';
    if (chipEl) chipEl.style.display = 'none';
    if (descEl) descEl.textContent = '';
    if (launchLink) launchLink.style.display = 'none';
    if (startLink) startLink.style.display = 'none';
    return;
  }

  if (titleEl) titleEl.textContent = course.title;
  if (metaEl) metaEl.textContent = course.source;
  if (chipEl) chipEl.textContent = KC_DOMAIN_LABELS[course.domain] || course.domain;
  if (descEl) descEl.textContent = course.description || '';
  if (launchLink) launchLink.href = course.launch_url || '#';
}

document.addEventListener('DOMContentLoaded', kcLoadDashboard);
