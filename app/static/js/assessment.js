// Karmayogi Compass — Assessment page.
// Real flow: upload a PDF -> POST /quiz/generate -> answer each question
// (Previous/Next actually change which question is shown) -> POST /quiz/submit
// -> hand the real result off to the results page via sessionStorage.

let kcAssessmentId = null;
let kcQuestions = [];
let kcAnswers = [];
let kcCurrentIndex = 0;

function kcEl (id) { return document.getElementById(id); }

document.addEventListener('DOMContentLoaded', () => {
  const generateBtn = kcEl('generateBtn');
  const pdfInput = kcEl('pdfInput');
  const prevBtn = kcEl('quizPrev');
  const nextBtn = kcEl('quizNext');
  const submitBtn = kcEl('quizSubmit');

  generateBtn.addEventListener('click', kcGenerateQuiz);
  prevBtn.addEventListener('click', () => kcRenderQuestion(kcCurrentIndex - 1));
  nextBtn.addEventListener('click', () => kcRenderQuestion(kcCurrentIndex + 1));
  submitBtn.addEventListener('click', kcSubmitQuiz);
});

async function kcGenerateQuiz () {
  const user = kcGetUser();
  const pdfInput = kcEl('pdfInput');
  const errorEl = kcEl('uploadError');
  const statusEl = kcEl('uploadStatus');
  const generateBtn = kcEl('generateBtn');

  errorEl.style.display = 'none';
  if (!pdfInput.files || !pdfInput.files[0]) {
    errorEl.textContent = 'Please choose a PDF file first.';
    errorEl.style.display = 'block';
    return;
  }

  generateBtn.setAttribute('disabled', 'true');
  generateBtn.textContent = 'Generating…';
  statusEl.style.display = 'block';
  statusEl.textContent = 'Reading the document and building gap-weighted questions — this can take up to a minute…';

  const formData = new FormData();
  formData.append('user_id', String(user.user_id));
  formData.append('file', pdfInput.files[0]);

  try {
    const res = await kcAuthFetch('/quiz/generate', { method: 'POST', body: formData });
    if (!res.ok) {
      throw new Error(await kcParseErrorMessage(res, 'Could not generate an assessment from that file.'));
    }
    const data = await res.json();
    kcAssessmentId = data.assessment_id;
    kcQuestions = data.questions;
    kcAnswers = new Array(kcQuestions.length).fill(null);

    kcEl('uploadPanel').hidden = true;
    kcEl('quizPanel').hidden = false;
    kcRenderQuestion(0);
  } catch (err) {
    errorEl.textContent = err.message || 'Something went wrong generating the assessment.';
    errorEl.style.display = 'block';
  } finally {
    generateBtn.removeAttribute('disabled');
    generateBtn.textContent = 'Generate Assessment';
    statusEl.style.display = 'none';
  }
}

function kcRenderQuestion (index) {
  if (index < 0 || index >= kcQuestions.length) return;
  kcCurrentIndex = index;
  const q = kcQuestions[index];

  kcEl('quizTag').textContent = `Question ${index + 1} of ${kcQuestions.length} · ${q.domain.replace('_', ' ')}`;
  kcEl('quizScenario').textContent = q.scenario || '';
  kcEl('quizQuestionText').textContent = q.question;
  kcEl('quizCitation').textContent = `◆ Source: ${q.citation}`;

  const progress = kcEl('quizProgress');
  progress.innerHTML = '';
  kcQuestions.forEach((_, i) => {
    const dot = document.createElement('i');
    if (i < index) dot.className = 'done';
    else if (i === index) dot.className = 'current';
    progress.appendChild(dot);
  });

  const optionsEl = kcEl('quizOptions');
  optionsEl.innerHTML = '';
  q.options.forEach((opt) => {
    const div = document.createElement('div');
    div.className = 'quiz-option' + (kcAnswers[index] === opt.label ? ' selected' : '');
    div.innerHTML = `<span class="opt-letter">${opt.label}</span> ${opt.text}`;
    div.addEventListener('click', () => {
      kcAnswers[index] = opt.label;
      kcRenderQuestion(index); // re-render to reflect the new selection + enable Next
    });
    optionsEl.appendChild(div);
  });

  kcEl('quizPrev').style.visibility = index === 0 ? 'hidden' : 'visible';

  const isLast = index === kcQuestions.length - 1;
  const answered = kcAnswers[index] != null;
  kcEl('quizNext').hidden = isLast;
  kcEl('quizSubmit').hidden = !isLast;
  kcEl('quizNext').disabled = !answered;
  kcEl('quizSubmit').disabled = !answered;
}

async function kcSubmitQuiz () {
  const user = kcGetUser();
  const errorEl = kcEl('submitError');
  const submitBtn = kcEl('quizSubmit');
  errorEl.style.display = 'none';

  if (kcAnswers.some((a) => a == null)) {
    errorEl.textContent = 'Please answer every question before submitting.';
    errorEl.style.display = 'block';
    return;
  }

  submitBtn.setAttribute('disabled', 'true');
  submitBtn.textContent = 'Submitting…';

  try {
    const res = await kcAuthFetch('/quiz/submit', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ assessment_id: kcAssessmentId, user_id: user.user_id, answers: kcAnswers }),
    });
    if (!res.ok) {
      throw new Error(await kcParseErrorMessage(res, 'Could not submit the assessment.'));
    }
    const result = await res.json();
    sessionStorage.setItem('kc_last_result', JSON.stringify(result));
    window.location.href = '/results';
  } catch (err) {
    errorEl.textContent = err.message || 'Something went wrong submitting the assessment.';
    errorEl.style.display = 'block';
    submitBtn.removeAttribute('disabled');
    submitBtn.textContent = 'Submit Assessment';
  }
}
