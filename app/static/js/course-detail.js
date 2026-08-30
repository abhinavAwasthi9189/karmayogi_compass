// Karmayogi Compass — Course Detail page.
// Loads a real course (via ?id=<external_id>, falling back to the user's
// top recommendation if no id is given) and shows the real gap it
// addresses. No fabricated module-by-module progress table — the backend
// doesn't track per-module completion, so we don't pretend it does.

const KC_DOMAIN_LABELS_CD = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

async function kcLoadCourseDetail () {
  const user = kcGetUser();
  if (!user || !user.user_id) return;

  const params = new URLSearchParams(window.location.search);
  const courseId = params.get('id');

  let course = null;
  try {
    if (courseId) {
      const res = await kcAuthFetch(`/recommendations/course/${encodeURIComponent(courseId)}`);
      if (res.ok) course = await res.json();
    }
    if (!course) {
      const res = await kcAuthFetch(`/recommendations/${user.user_id}`);
      if (res.ok) {
        const data = await res.json();
        course = data.courses && data.courses[0];
      }
    }
  } catch (e) {
    // handled by the "no course" branch below
  }

  if (!course) {
    document.getElementById('courseTitle').textContent = 'Course not found';
    document.getElementById('courseDescription').textContent = 'This course could not be loaded.';
    document.getElementById('courseSourceBadge').style.display = 'none';
    return;
  }

  document.getElementById('courseTitle').textContent = course.title;
  document.getElementById('courseDescription').textContent = course.description || '';
  document.getElementById('courseSourceBadge').textContent = course.source;
  document.getElementById('courseDomainBadge').textContent = KC_DOMAIN_LABELS_CD[course.domain] || course.domain;
  document.getElementById('launchLink').href = course.launch_url || '#';

  // Show the real gap this course's domain addresses for this user.
  try {
    const res = await kcAuthFetch(`/skillgap/${user.user_id}`);
    if (res.ok) {
      const skillgap = await res.json();
      const match = skillgap.gaps.find((g) => g.domain === course.domain);
      const label = KC_DOMAIN_LABELS_CD[course.domain] || course.domain;
      if (match && match.gap > 0) {
        document.getElementById('whyThisCourse').textContent =
          `Recommended because it targets ${label} — your current score is ${Math.round(match.current)}/100 ` +
          `against a required ${Math.round(match.required)}/100 for your role.`;
        document.getElementById('gapAddressedRow').hidden = false;
        document.getElementById('gapAddressedPts').textContent = `${Math.round(match.gap)} pts`;
        document.getElementById('gapAddressedBar').dataset.target = String(Math.min(100, Math.round(match.gap * 2)));
      } else {
        document.getElementById('whyThisCourse').textContent =
          `You already meet the requirement for ${label}, but this course can help you go further.`;
      }
    }
  } catch (e) {
    document.getElementById('whyThisCourse').textContent = 'Could not load your gap data for this domain.';
  }

  if (typeof initBars === 'function') initBars();
}

document.addEventListener('DOMContentLoaded', kcLoadCourseDetail);
