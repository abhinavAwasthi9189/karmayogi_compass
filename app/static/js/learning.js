// Karmayogi Compass — Learning page.
// Shows the real course iGOT/recommendations picked for this user (their
// top competency gap) and points Compass AI at it, instead of a hardcoded
// "Module 3 — GROUP BY" demo shown to every account.

const KC_DOMAIN_LABELS_L = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

async function kcLoadLearning () {
  const user = kcGetUser();
  if (!user || !user.user_id) return;

  const titleEl = document.getElementById('courseTitle');
  const descEl = document.getElementById('courseDescription');
  const badgeEl = document.getElementById('courseDomainBadge');
  const sourceEl = document.getElementById('courseSourceLine');
  const awareEl = document.getElementById('aiAwareOf');
  const pageTitleEl = document.getElementById('pageTitle');
  const toAssessmentLink = document.getElementById('toAssessmentLink');

  let course = null;
  try {
    const res = await kcAuthFetch(`/recommendations/${user.user_id}`);
    if (res.ok) {
      const data = await res.json();
      course = data.courses && data.courses[0];
    }
  } catch (e) {
    // fall through to the "no course" state below
  }

  let contextString;
  if (course) {
    if (titleEl) titleEl.textContent = course.title;
    if (descEl) descEl.textContent = course.description || 'No description available for this course yet.';
    if (badgeEl) badgeEl.textContent = KC_DOMAIN_LABELS_L[course.domain] || course.domain;
    if (sourceEl) sourceEl.textContent = `Source: ${course.source}`;
    if (pageTitleEl) pageTitleEl.textContent = course.title;
    contextString = `${course.title} — ${course.description || ''}`.trim();
  } else {
    if (titleEl) titleEl.textContent = 'No course assigned right now';
    if (descEl) descEl.textContent = 'You\u2019re meeting your role\u2019s requirements across all competency domains, so there\u2019s no gap-driven course to show here.';
    if (badgeEl) badgeEl.style.display = 'none';
    if (sourceEl) sourceEl.textContent = '';
    if (toAssessmentLink) toAssessmentLink.style.display = 'none';
    contextString = 'General MoSPI official statistics training';
  }

  if (awareEl) awareEl.textContent = `Aware of: ${course ? course.title : 'general MoSPI training'}`;
  if (typeof kcInitCompassAI === 'function') kcInitCompassAI(contextString);
}

document.addEventListener('DOMContentLoaded', kcLoadLearning);
