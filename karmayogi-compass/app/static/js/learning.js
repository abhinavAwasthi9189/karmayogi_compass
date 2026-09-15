// Karmayogi Compass — Learning page.
// Loads a real course (via ?id=<external_id>, or the user's top
// recommendation if none is given) and, when the mock dataset has module
// content for it, renders an actual module reader. Compass AI is grounded
// in the FULL study material of whichever module is currently open, not
// just a one-line course description, so its answers are actually
// substantive instead of "the context doesn't specify that."

const KC_DOMAIN_LABELS_L = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

let kcCompassAI = null;
let kcModules = [];
let kcActiveModuleNo = null;

async function kcLoadLearning () {
  const user = kcGetUser();
  if (!user || !user.user_id) return;

  const params = new URLSearchParams(window.location.search);
  const requestedId = params.get('id');

  const titleEl = document.getElementById('courseTitle');
  const descEl = document.getElementById('courseDescription');
  const badgeEl = document.getElementById('courseDomainBadge');
  const sourceEl = document.getElementById('courseSourceLine');
  const toAssessmentLink = document.getElementById('toAssessmentLink');

  let course = null;
  try {
    if (requestedId) {
      const res = await kcAuthFetch(`/recommendations/course/${encodeURIComponent(requestedId)}`);
      if (res.ok) course = await res.json();
    } else {
      // No specific course requested -- ask the backend for the best course to
      // open by default (prefers a real mock-content course for the user's
      // biggest gap domain, falling back to their top overall recommendation).
      const res = await kcAuthFetch(`/recommendations/${user.user_id}/learning-course`);
      if (res.ok) course = await res.json();
    }
  } catch (e) {
    // fall through to the "no course" state below
  }

  if (!course) {
    titleEl.textContent = 'No course assigned right now';
    descEl.textContent = 'You\u2019re meeting your role\u2019s requirements across all competency domains, so there\u2019s no gap-driven course to show here.';
    badgeEl.style.display = 'none';
    sourceEl.textContent = '';
    if (toAssessmentLink) toAssessmentLink.style.display = 'none';
    kcCompassAI = kcInitCompassAI('General MoSPI official statistics training', 'general MoSPI training');
    return;
  }

  titleEl.textContent = course.title;
  descEl.textContent = course.description || 'No description available for this course yet.';
  badgeEl.textContent = KC_DOMAIN_LABELS_L[course.domain] || course.domain;
  sourceEl.textContent = `Source: ${course.source}`;

  // Load real module content for this course from the mock dataset, if any exists.
  try {
    const res = await kcAuthFetch(`/recommendations/course/${encodeURIComponent(course.id)}/modules`);
    if (res.ok) {
      const data = await res.json();
      kcModules = data.modules || [];
    }
  } catch (e) {
    kcModules = [];
  }

  if (kcModules.length) {
    renderModuleList();
    document.getElementById('moduleViewerCard').hidden = false;
    selectModule(kcModules[0].module_no); // also initializes Compass AI with real content
  } else {
    // No module content bundled for this course -- fall back to the course description as context.
    const context = `Course: "${course.title}" (${KC_DOMAIN_LABELS_L[course.domain] || course.domain}). ${course.description || ''}`.trim();
    kcCompassAI = kcInitCompassAI(context, course.title);
  }
}

function renderModuleList () {
  const listEl = document.getElementById('moduleList');
  listEl.innerHTML = '';
  kcModules.forEach((m) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'module-item';
    btn.dataset.moduleNo = String(m.module_no);
    btn.innerHTML = `<span class="m-no">${String(m.module_no).padStart(2, '0')}</span>${m.module_title}`;
    btn.addEventListener('click', () => selectModule(m.module_no));
    listEl.appendChild(btn);
  });
}

function selectModule (moduleNo) {
  const mod = kcModules.find((m) => m.module_no === moduleNo);
  if (!mod) return;
  kcActiveModuleNo = moduleNo;

  document.querySelectorAll('.module-item').forEach((el) => {
    el.classList.toggle('active', Number(el.dataset.moduleNo) === moduleNo);
  });

  document.getElementById('moduleContent').innerHTML = `
    <h4>${mod.module_title}</h4>
    <p>${mod.study_material}</p>
    <div class="outcome">Learning outcome: ${mod.module_learning_outcome}</div>
  `;

  const context = `Module: "${mod.module_title}". Study material: ${mod.study_material} Learning outcome: ${mod.module_learning_outcome}`;
  if (!kcCompassAI) {
    kcCompassAI = kcInitCompassAI(context, mod.module_title);
  } else {
    kcCompassAI.setContext(context, mod.module_title);
  }
}

document.addEventListener('DOMContentLoaded', kcLoadLearning);
