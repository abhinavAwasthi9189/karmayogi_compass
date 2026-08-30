// Karmayogi Compass — Compass AI widget.
// Wires an `.ai-drawer` block to the real /api/v1/compass-ai endpoints.
// Nothing here is scripted: suggestions and answers both come from the
// backend (Gemini via LiteLLM), scoped to whatever `context` string the
// host page passes in (e.g. the current course/module title).

function kcInitCompassAI (context) {
  const drawer = document.querySelector('.ai-drawer');
  if (!drawer) return;

  const thread = drawer.querySelector('.ai-thread');
  const suggestionsEl = drawer.querySelector('.ai-suggestions');
  const input = drawer.querySelector('.ai-input input');
  const sendBtn = drawer.querySelector('.ai-send');

  appendMsg('bot', `Ask me anything about "${context}" — I'll keep answers short and grounded in this module.`);
  loadSuggestions();

  if (sendBtn && input) {
    const fire = () => {
      const text = input.value.trim();
      if (!text) return;
      input.value = '';
      handleAsk(text);
    };
    sendBtn.addEventListener('click', fire);
    input.addEventListener('keydown', (e) => { if (e.key === 'Enter') fire(); });
  }

  async function loadSuggestions () {
    if (!suggestionsEl) return;
    suggestionsEl.innerHTML = '<span class="ai-chip" style="opacity:.6;">Loading suggestions…</span>';
    try {
      const res = await kcAuthFetch('/compass-ai/suggestions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context }),
      });
      const data = res.ok ? await res.json() : { suggestions: [] };
      suggestionsEl.innerHTML = '';
      (data.suggestions || []).forEach((s) => {
        const chip = document.createElement('span');
        chip.className = 'ai-chip';
        chip.textContent = s;
        chip.addEventListener('click', () => handleAsk(s));
        suggestionsEl.appendChild(chip);
      });
    } catch (e) {
      suggestionsEl.innerHTML = '';
    }
  }

  async function handleAsk (question) {
    appendMsg('user', question);
    const pending = appendMsg('bot', 'Compass AI is thinking…');
    try {
      const res = await kcAuthFetch('/compass-ai/ask', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ context, question }),
      });
      const data = res.ok
        ? await res.json()
        : { answer: 'Something went wrong reaching Compass AI. Please try again.' };
      pending.querySelector('.msg-text').textContent = data.answer;
    } catch (e) {
      pending.querySelector('.msg-text').textContent = 'Something went wrong reaching Compass AI. Please try again.';
    }
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
