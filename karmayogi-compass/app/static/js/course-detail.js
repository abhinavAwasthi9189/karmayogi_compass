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
  document.getElementById('continueLearningLink').href = `/learning?id=${encodeURIComponent(course.id)}`;
  const continueToLearningLink = document.getElementById('continueToLearningLink');
  if (continueToLearningLink) continueToLearningLink.href = `/learning?id=${encodeURIComponent(course.id)}`;
  kcLoadWhatYoullLearn(course);

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

async function kcLoadWhatYoullLearn (course) {
  const el = document.getElementById('whatYoullLearn');

  // Prefer real, per-module learning outcomes from the mock dataset over an
  // AI-guessed summary -- deterministic, grounded, and actually specific.
  try {
    const res = await kcAuthFetch(`/recommendations/course/${encodeURIComponent(course.id)}/modules`);
    if (res.ok) {
      const data = await res.json();
      if (data.modules && data.modules.length) {
        el.innerHTML = `<ul>${
          data.modules.map((m) => `<li>${m.module_learning_outcome}</li>`).join('')
        }</ul>`;
        return;
      }
    }
  } catch (e) {
    // fall through to the AI-generated summary below
  }

  // No bundled module content for this course -- ask Compass AI for a short summary instead,
  // clearly grounded only in the course's own title/description.
  const context = `Course: ${course.title}. Description: ${course.description || 'No description given.'}`;
  try {
    const res = await kcAuthFetch('/compass-ai/ask', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        context,
        question: 'List 3 short, specific outcomes a MoSPI official will be able to do after finishing this course. ' +
          'Reply with exactly 3 lines, one outcome per line, each starting with "- ", and nothing else.',
      }),
    });
    const data = res.ok ? await res.json() : null;
    const points = data ? kcSplitIntoOutcomePoints(data.answer) : [];
    if (points.length) {
      el.innerHTML = `<ul>${points.map((p) => `<li>${kcEscapeHtml(p)}</li>`).join('')}</ul>`;
    } else {
      el.textContent = 'Could not generate a summary for this course right now.';
    }
  } catch (e) {
    el.textContent = 'Could not generate a summary for this course right now.';
  }
}

// Turns a freeform AI answer into clean bullet points, whether it came back
// as "- " lines, numbered lines, or a plain paragraph of sentences.
function kcSplitIntoOutcomePoints (answer) {
  if (!answer) return [];

  const lines = answer
    .split('\n')
    .map((line) => line.replace(/^\s*(?:[-*•]|\d+[.)])\s*/, '').trim())
    .filter(Boolean);

  if (lines.length > 1) return lines;

  // Single-line answer: fall back to splitting on sentence boundaries.
  return answer
    .split(/(?<=[.!?])\s+(?=[A-Z])/)
    .map((s) => s.trim())
    .filter(Boolean);
}

function kcEscapeHtml (str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

document.addEventListener('DOMContentLoaded', kcLoadCourseDetail);
