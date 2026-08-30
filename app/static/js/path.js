// Karmayogi Compass — Learning Path page.
// The roadmap is the user's actual recommended courses (biggest gap first,
// from /recommendations), and the "Target Outcome" panel is their real
// current/required score for their priority domain from /skillgap.
// No fake "locked" steps — every recommended course is real and clickable.

const KC_DOMAIN_LABELS_PT = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

async function kcLoadPath () {
  const user = kcGetUser();
  if (!user || !user.user_id) return;

  const trackEl = document.getElementById('pathTrack');
  const titleEl = document.getElementById('roadmapTitle');
  const subtitleEl = document.getElementById('roadmapSubtitle');
  const continueLink = document.getElementById('continueLink');

  let skillgap, recommendations;
  try {
    [skillgap, recommendations] = await Promise.all([
      kcAuthFetch(`/skillgap/${user.user_id}`).then((r) => (r.ok ? r.json() : null)),
      kcAuthFetch(`/recommendations/${user.user_id}`).then((r) => (r.ok ? r.json() : null)),
    ]);
  } catch (e) {
    subtitleEl.textContent = 'Could not load your recommendations. Try refreshing the page.';
    return;
  }

  const priorityLabel = skillgap && skillgap.priority_domain
    ? KC_DOMAIN_LABELS_PT[skillgap.priority_domain] || skillgap.priority_domain
    : null;
  titleEl.textContent = priorityLabel ? `Roadmap to Close the ${priorityLabel} Gap` : 'Your Learning Roadmap';

  const courses = (recommendations && recommendations.courses) || [];
  subtitleEl.textContent = courses.length
    ? `${courses.length} course${courses.length > 1 ? 's' : ''} from iGOT Karmayogi, ordered by the size of your competency gaps.`
    : 'You currently meet the requirements across all competency domains.';

  trackEl.innerHTML = '';
  courses.forEach((course, i) => {
    const step = document.createElement('div');
    step.className = 'path-step' + (i === 0 ? ' active' : '');
    step.innerHTML = `
      <div class="step-marker">${i + 1}</div>
      <div class="step-body">
        <div class="step-source">${course.source}</div>
        <div class="step-title">${course.title}</div>
        <div class="step-desc">${course.description || ''}</div>
        <a href="/course-detail?id=${encodeURIComponent(course.id)}" class="btn ${i === 0 ? 'btn-primary' : 'btn-outline'} btn-sm">
          ${i === 0 ? 'Start Course' : 'View Course'}
        </a>
      </div>
    `;
    trackEl.appendChild(step);
  });

  if (!courses.length) {
    trackEl.innerHTML = '<p class="text-sm text-soft">No courses to recommend right now — nice work.</p>';
    continueLink.style.display = 'none';
  } else {
    continueLink.href = `/course-detail?id=${encodeURIComponent(courses[0].id)}`;
  }

  const top = skillgap && skillgap.gaps && skillgap.gaps.find((g) => g.domain === skillgap.priority_domain);
  if (top) {
    document.getElementById('targetCurrent').textContent = Math.round(top.current);
    document.getElementById('targetRequired').textContent = Math.round(top.required);
    const bar = document.getElementById('targetBar');
    bar.dataset.target = String(Math.round((top.current / top.required) * 100));
    document.getElementById('targetNote').textContent =
      `${Math.round(top.gap)} points to close in your priority domain.`;
  } else {
    document.getElementById('targetCurrent').textContent = '—';
    document.getElementById('targetRequired').textContent = '—';
    document.getElementById('targetNote').textContent = 'All domains currently meet requirements.';
  }

  if (typeof initBars === 'function') initBars();
}

document.addEventListener('DOMContentLoaded', kcLoadPath);
