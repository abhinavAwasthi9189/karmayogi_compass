// Karmayogi Compass — shared front-end behavior
// Pure vanilla JS. No frameworks. Safe to progressively replace with
// Flask/Jinja-rendered data later — every dynamic value here is read
// from a data-* attribute so the templating layer just needs to set those.

document.addEventListener('DOMContentLoaded', () => {
  initGauges();
  initBars();
  initQuiz();
  initAiChips();
  initSimRunner();
});

/* ---------- Circular score gauges ---------- */
function initGauges () {
  document.querySelectorAll('.gauge').forEach((el) => {
    const value = parseFloat(el.dataset.value || '0');
    const max = parseFloat(el.dataset.max || '100');
    const r = 54;
    const circumference = 2 * Math.PI * r;
    const pct = Math.max(0, Math.min(1, value / max));
    const offset = circumference * (1 - pct);
    const valueCircle = el.querySelector('.gauge-value');
    if (valueCircle) {
      valueCircle.style.strokeDasharray = `${circumference}`;
      valueCircle.style.strokeDashoffset = `${circumference}`;
      // color by threshold
      if (pct < 0.5) valueCircle.style.stroke = 'var(--red)';
      else if (pct < 0.75) valueCircle.style.stroke = 'var(--gold)';
      else valueCircle.style.stroke = 'var(--green)';
      requestAnimationFrame(() => {
        valueCircle.style.strokeDashoffset = `${offset}`;
      });
    }
  });
}

/* ---------- Competency bars ---------- */
function initBars () {
  document.querySelectorAll('.bar-fill[data-target]').forEach((el) => {
    const target = el.dataset.target;
    requestAnimationFrame(() => { el.style.width = target + '%'; });
  });
}

/* ---------- Adaptive quiz (Screen 7) ---------- */
function initQuiz () {
  const options = document.querySelectorAll('.quiz-option');
  const nextBtn = document.getElementById('quizNext');
  options.forEach((opt) => {
    opt.addEventListener('click', () => {
      const group = opt.closest('.quiz-options');
      group.querySelectorAll('.quiz-option').forEach((o) => o.classList.remove('selected'));
      opt.classList.add('selected');
      if (nextBtn) nextBtn.removeAttribute('disabled');
    });
  });
}

/* ---------- Compass AI quick-prompt chips (Screen 6) ---------- */
function initAiChips () {
  const chips = document.querySelectorAll('.ai-chip');
  const thread = document.querySelector('.ai-thread');
  const input = document.querySelector('.ai-input input');
  if (!thread) return;

  chips.forEach((chip) => {
    chip.addEventListener('click', () => sendAiPrompt(chip.textContent.trim()));
  });

  const sendBtn = document.querySelector('.ai-send');
  if (sendBtn && input) {
    const fire = () => {
      const text = input.value.trim();
      if (!text) return;
      sendAiPrompt(text);
      input.value = '';
    };
    sendBtn.addEventListener('click', fire);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') fire(); });
  }

  function sendAiPrompt (text) {
    appendMsg('user', text);
    const typing = appendMsg('bot', 'Compass AI is thinking…');
    setTimeout(() => {
      typing.querySelector('.msg-text').textContent =
        'Here\u2019s the relevant explanation from your current module, matched to your SQL gap area.';
      const src = document.createElement('span');
      src.className = 'src';
      src.textContent = 'Source: Applied SQL for Survey Data Management — Module 3, Pg 14';
      typing.appendChild(src);
      thread.scrollTop = thread.scrollHeight;
    }, 700);
  }

  function appendMsg (role, text) {
    const div = document.createElement('div');
    div.className = `ai-msg ${role}`;
    const span = document.createElement('span');
    span.className = 'msg-text';
    span.textContent = text;
    div.appendChild(span);
    thread.appendChild(div);
    thread.scrollTop = thread.scrollHeight;
    return div;
  }
}

/* ---------- Work-simulation "run" button (Screen 7) ---------- */
function initSimRunner () {
  const btn = document.getElementById('runSim');
  const out = document.getElementById('simOutput');
  if (!btn || !out) return;
  btn.addEventListener('click', () => {
    btn.textContent = 'Running…';
    btn.setAttribute('disabled', 'true');
    setTimeout(() => {
      out.hidden = false;
      btn.textContent = 'Run simulation';
      btn.removeAttribute('disabled');
    }, 900);
  });
}
