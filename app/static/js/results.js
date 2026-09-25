// Karmayogi Compass — Results page.
// Renders whatever the /quiz/submit call actually returned (handed off via
// sessionStorage by assessment.js). No fabricated before/after numbers —
// if there's no real result yet, we say so and point back to the assessment.

const KC_DOMAIN_LABELS_R = {
  statistical: 'Statistical Competencies',
  technical: 'Technical Competencies',
  digital_gov: 'Digital Governance',
  managerial: 'Behavioral & Managerial',
};

document.addEventListener('DOMContentLoaded', () => {
  const raw = sessionStorage.getItem('kc_last_result');
  if (!raw) {
    document.getElementById('noResultPanel').hidden = false;
    return;
  }

  let result;
  try {
    result = JSON.parse(raw);
  } catch (e) {
    document.getElementById('noResultPanel').hidden = false;
    return;
  }

  document.getElementById('resultPanel').hidden = false;

  document.getElementById('scorePercent').textContent = result.score;
  document.getElementById('scoreDetail').textContent =
    `${result.correct_count} of ${result.total_questions} questions correct.`;

  const breakdownEl = document.getElementById('domainBreakdown');
  breakdownEl.innerHTML = '';
  Object.entries(result.domain_breakdown || {}).forEach(([domain, stats]) => {
    const pct = Math.round((stats.accuracy || 0) * 100);
    const row = document.createElement('div');
    row.className = 'comp-row';
    row.innerHTML = `
      <div class="comp-top">
        <span class="comp-name">${KC_DOMAIN_LABELS_R[domain] || domain}</span>
        <span class="comp-score">${stats.correct}/${stats.total} · ${pct}%</span>
      </div>
      <div class="bar-track"><div class="bar-fill" data-target="${pct}" style="width:0"></div></div>
    `;
    breakdownEl.appendChild(row);
  });

  const updatedEl = document.getElementById('updatedScores');
  updatedEl.innerHTML = '';
  Object.entries(result.updated_scores || {}).forEach(([domain, score]) => {
    const row = document.createElement('div');
    row.className = 'comp-row';
    row.innerHTML = `
      <div class="comp-top">
        <span class="comp-name">${KC_DOMAIN_LABELS_R[domain] || domain}</span>
        <span class="comp-score">${Math.round(score)}/100</span>
      </div>
      <div class="bar-track"><div class="bar-fill gold" data-target="${Math.round(score)}" style="width:0"></div></div>
    `;
    updatedEl.appendChild(row);
  });

  document.getElementById('readinessIndex').textContent = result.overall_readiness_index;

  if (typeof initBars === 'function') initBars();

    const reviewCard = document.getElementById('reviewCard');
  const reviewList = document.getElementById('reviewList');
  const reviewToggle = document.getElementById('reviewToggle');
  if (result.review && result.review.length) {
    reviewCard.hidden = false;
    reviewList.innerHTML = '';
    result.review.forEach((item, idx) => {
      const block = document.createElement('div');
      block.style.borderLeft = `3px solid ${item.is_correct ? '#3E6E64' : '#B1503A'}`;
      block.style.paddingLeft = '12px';
      const optionsHtml = (item.options || []).map((o) => {
        const isYours = o.label === item.your_answer;
        const isCorrect = o.label === item.correct_option;
        let mark = '';
        if (isCorrect) mark = ' \u2713';
        else if (isYours) mark = ' \u2717';
        return `<div style="${isCorrect ? 'font-weight:600;' : ''}">${o.label}. ${o.text}${mark}</div>`;
      }).join('');
      block.innerHTML = `
        <div class="text-sm text-soft">Q${idx + 1} \u00b7 ${KC_DOMAIN_LABELS_R[item.domain] || item.domain} \u00b7 ${item.is_correct ? 'Correct' : 'Incorrect'}</div>
        <div style="margin:4px 0;"><i>${item.scenario || ''}</i></div>
        <div style="font-weight:500;">${item.question}</div>
        <div style="margin:6px 0;">${optionsHtml}</div>
        <div class="text-sm">${item.explanation}</div>
        <div class="text-sm text-soft" style="margin-top:2px;">Source: ${item.citation}</div>
      `;
      reviewList.appendChild(block);
    });
  }
  if (reviewToggle) {
    reviewToggle.addEventListener('click', () => {
    reviewList.style.display = reviewList.style.display === 'none' ? 'flex' : 'none';
    });
  }
});