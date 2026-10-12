const $ = id => document.getElementById(id);
let testId, test, index = 0, answers = {}, transition, active = false, submitting = false;
let starting = false, checking = false, solved = false, attempt = 0;
let pages = new Map();
let loadingQuestion = null, pendingResult = false;
const PAGE_SIZE = 20;
const SAVE_KEY = 'quiz-progress-v1';
let rejected = [];
function saveProgress(position = index, wrong = rejected) {
  try { localStorage.setItem(SAVE_KEY, JSON.stringify({id:testId, index:position, answers, wrong})); }
  catch { /* Training still works when browser storage is unavailable. */ }
}
function clearProgress() { try { localStorage.removeItem(SAVE_KEY); } catch {} }
function readProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(SAVE_KEY));
    if (saved && typeof saved.id === 'string' && Number.isInteger(saved.index) && saved.index >= 0
        && saved.answers && typeof saved.answers === 'object' && !Array.isArray(saved.answers)
        && Object.entries(saved.answers).every(([id, answer]) => /^[1-9]\d*$/.test(id) && /^[ABCD]$/.test(answer))
        && Array.isArray(saved.wrong) && saved.wrong.every(answer => /^[ABCD]$/.test(answer))) return saved;
  } catch {}
  clearProgress(); return null;
}
function closeModal() { $('app-modal').close(); }
$('modal-cancel').onclick = closeModal;
$('modal-confirm').onclick = () => {
  closeModal(); active = false; pendingResult = false; clearProgress(); clearTimeout(transition); screen('catalog');
};
function screen(id) {
  for (const name of ['catalog', 'quiz', 'result']) $(name).hidden = name !== id;
  $('global-message').textContent = '';
  window.scrollTo({top:0, behavior:'instant'});
}
async function api(url, body) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 15000);
  try {
  let res;
  try {
    res = await fetch(url, {signal:controller.signal, ...(body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})});
  } catch {
    throw Error('Серверга уланиб бўлмади. Қайта уриниб кўринг.');
  }
  let data;
  try { data = await res.json(); } catch { throw Error('Сервердан нотўғри жавоб келди.'); }
  if (!res.ok) throw Error(data.error || 'Сўровни бажариб бўлмади');
  return data;
  } finally { clearTimeout(timeout); }
}
async function start(id, saved = null) {
  if (starting || submitting || active) return;
  starting = true;
  $('retry').disabled = true;
  try {
    const firstPage = await api(`/api/tests/${encodeURIComponent(id)}?limit=${PAGE_SIZE}`);
    test = {title:firstPage.title, questions:new Array(firstPage.total)};
    firstPage.questions.forEach((question, offset) => { test.questions[offset] = question; });
    pages = new Map();
    testId = id; index = 0; answers = {}; active = true; submitting = false;
    rejected = [];
    if (saved && saved.index <= firstPage.total) {
      index = saved.index; answers = saved.answers; rejected = saved.wrong;
    }
    attempt++; checking = false; solved = false; pendingResult = false; $('next').hidden = true; $('next').disabled = false; $('exit').disabled = false; $('quiz-title').textContent = test.title;
    screen('quiz');
    if (index === test.questions.length) await finish();
    else { saveProgress(); await showQuestion(); }
  } catch (e) { $('global-message').textContent = e.message; }
  finally { starting = false; $('retry').disabled = false; }
}
async function fetchPage(position, currentAttempt = attempt) {
  const offset = Math.floor(position / PAGE_SIZE) * PAGE_SIZE;
  if (test.questions[position]) return;
  if (!pages.has(offset)) {
    const id = testId;
    const pending = api(`/api/tests/${encodeURIComponent(id)}?offset=${offset}&limit=${PAGE_SIZE}`)
      .then(page => {
        if (attempt === currentAttempt && active) page.questions.forEach((q, i) => { test.questions[offset + i] = q; });
      }).catch(error => { if (attempt === currentAttempt) pages.delete(offset); throw error; });
    pages.set(offset, pending);
  }
  await pages.get(offset);
}
function prefetch() {
  const position = (Math.floor(index / PAGE_SIZE) + 1) * PAGE_SIZE;
  if (position < test.questions.length) fetchPage(position).catch(() => {});
}
async function showQuestion() {
  if (loadingQuestion === attempt) return;
  const renderAttempt = attempt;
  loadingQuestion = renderAttempt;
  $('next').disabled = true;
  try {
  clearTimeout(transition);
  const currentAttempt = attempt;
  if (!test.questions[index]) {
    $('options').replaceChildren();
    $('quiz-message').textContent = 'Савол юкланмоқда…';
    try { await fetchPage(index, currentAttempt); }
    catch(error) {
      if (active && attempt === currentAttempt) {
        $('quiz-message').textContent = error.message;
        $('next').hidden = false; $('next').textContent = 'Қайта юклаш';
      }
      return;
    }
  }
  if (!active || attempt !== currentAttempt) return;
  $('next').hidden = true;
  prefetch();
  const q = test.questions[index];
  $('counter').textContent = `${index + 1}-савол / ${test.questions.length} та`;
  $('progress-fill').style.width = `${index / test.questions.length * 100}%`;
  document.querySelector('.progress').setAttribute('aria-valuenow', Math.round(index / test.questions.length * 100));
  $('question-text').textContent = q.text;
  $('options').replaceChildren();
  const choices = Object.entries(q.options);
  for (let i = choices.length - 1; i > 0; i--) {
    const j = crypto.getRandomValues(new Uint32Array(1))[0] % (i + 1);
    [choices[i], choices[j]] = [choices[j], choices[i]];
  }
  for (const [position, [key, text]] of choices.entries()) {
    const label = document.createElement('label'); label.className = 'option';
    const input = document.createElement('input'); input.type = 'radio'; input.name = 'answer'; input.value = key;
    const letter = document.createElement('span'); letter.className = 'option-letter'; letter.textContent = 'ABCD'[position];
    const content = document.createElement('span'); content.textContent = text;
    content.className = 'option-text';
    input.onchange = () => checkChoice(input, label);
    if (rejected.includes(key)) { label.classList.add('answer-wrong'); input.disabled = true; }
    label.append(input, letter, content); $('options').append(label);
  }
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    $('question-text').animate([{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}], {duration:180,easing:'ease-out'});
    $('options').animate([{opacity:0},{opacity:1}], {duration:220});
  }
  $('quiz-message').textContent = rejected.length ? 'Нотўғри. Бошқа жавобни танла.' : '';
  solved = false;
  $('quiz-message').classList.remove('success');
  $('question-text').focus();
  } finally {
    if (loadingQuestion === renderAttempt) { loadingQuestion = null; $('next').disabled = false; }
  }
}
async function checkChoice(input, label) {
  if (!active || checking || solved) return;
  checking = true;
  const currentAttempt = attempt;
  const question = test.questions[index];
  const inputs = [...document.querySelectorAll('input[name="answer"]')];
  inputs.forEach(item => { item.disabled = true; });
  $('quiz-message').classList.remove('success');
  $('quiz-message').textContent = 'Текширилмоқда…';
  try {
    const result = await api(`/api/tests/${encodeURIComponent(testId)}/check`, {question_id:question.id, answer:input.value});
    if (!active || attempt !== currentAttempt) return;
    if (!(question.id in answers)) answers[question.id] = input.value;
    if (result.correct) {
      saveProgress(index + 1, []);
      solved = true;
      label.classList.add('answer-correct');
      $('quiz-message').classList.add('success');
      $('quiz-message').textContent = 'Тўғри!';
      const advance = () => {
        if (!active || attempt !== currentAttempt) return;
        if ($('app-modal').open) { transition = setTimeout(advance, 200); return; }
        index++;
        rejected = [];
        if (index < test.questions.length) showQuestion(); else finish();
      };
      transition = setTimeout(advance, 1100);
    } else {
      rejected.push(input.value); saveProgress();
      label.classList.add('answer-wrong');
      input.checked = false;
      $('quiz-message').textContent = 'Нотўғри. Бошқа жавобни танла.';
    }
  } catch (error) {
    if (active && attempt === currentAttempt) {
      input.checked = false;
      $('quiz-message').textContent = error.message;
    }
  } finally {
    if (attempt === currentAttempt) {
      checking = false;
      if (active && !solved) inputs.forEach(item => { item.disabled = item.closest('.option').classList.contains('answer-wrong'); });
    }
  }
}
async function finish() {
  if (submitting) return;
  clearTimeout(transition); active = false; submitting = true; pendingResult = true;
  if ($('app-modal').open) closeModal();
  $('next').disabled = true; $('next').textContent = 'Жавоблар текширилмоқда…';
  $('exit').disabled = true;
  try {
    const result = await api(`/api/tests/${encodeURIComponent(testId)}/submit`, {answers});
    $('percent').textContent = `${result.percent}%`;
    if ($('result-subject')) $('result-subject').textContent = test.title;
    if ($('result-meter-fill')) $('result-meter-fill').style.width = `${result.percent}%`;
    $('score-line').textContent = `${result.total} та саволдан ${result.score} тасига биринчи уринишда тўғри жавоб бердинг.`;
    $('correct-count').textContent = result.score;
    $('wrong-count').textContent = result.details.filter(q => q.selected && !q.correct).length;
    $('skipped-count').textContent = result.total;
    document.querySelector('.review').open = false;
    $('review-list').replaceChildren();
    for (const q of result.details) {
      const block = document.createElement('div'); block.className = 'review-item';
      const title = document.createElement('strong'); title.className = q.correct ? 'correct' : 'incorrect';
      title.textContent = `${q.correct ? '✓' : '×'} ${q.id}. ${q.text}`;
      const chosen = document.createElement('p'); chosen.textContent = `Биринчи жавобинг: ${q.selected ? q.options[q.selected] : 'Жавоб берилмаган'}`;
      block.append(title, chosen);
      if (!q.correct) { const right = document.createElement('p'); right.textContent = `Тўғри жавоб: ${q.options[q.correct_answer]}`; block.append(right); }
      $('review-list').append(block);
    }
    screen('result');
    pendingResult = false;
    clearProgress();
  } catch (e) {
    $('quiz-message').textContent = `${e.message}. Қайта юбориш мумкин.`;
    $('next').hidden = false; $('next').disabled = false; $('exit').disabled = false; $('next').textContent = 'Қайта юбориш';
  } finally { submitting = false; }
}
$('next').onclick = () => active ? showQuestion() : finish();
$('exit').onclick = () => $('app-modal').showModal();
$('retry').onclick = () => start(testId);
$('home').onclick = () => screen('catalog');
window.addEventListener('beforeunload', e => { if (active || submitting || pendingResult) { e.preventDefault(); e.returnValue = ''; } });
async function loadCatalog() {
  $('catalog-retry').hidden = true;
  $('global-message').textContent = '';
  try {
    const entries = await api('/api/tests');
    $('test-list').replaceChildren();
    for (const entry of entries) {
      const card = document.createElement('article'); card.className = 'test-card';
      const icon = document.createElement('span'); icon.className = 'subject-icon'; icon.setAttribute('aria-hidden','true');
      const image = document.createElement('img'); image.src = `/static/icons/${encodeURIComponent(entry.id)}.svg`; image.alt = ''; image.width = 27; image.height = 27; icon.append(image);
      const content = document.createElement('div'); content.className = 'test-content';
      const title = document.createElement('h2'); title.textContent = entry.title;
      const meta = document.createElement('p'); meta.className = 'muted'; meta.textContent = `${entry.count} та савол · вақт чекланмаган`;
      const button = document.createElement('button'); button.className = 'primary'; button.textContent = 'Бошлаш';
      button.onclick = async () => { button.disabled = true; await start(entry.id); button.disabled = false; };
      content.append(title, meta); card.append(icon, content, button); $('test-list').append(card);
    }
    const saved = readProgress();
    if (saved && entries.some(entry => entry.id === saved.id && saved.index <= entry.count)) await start(saved.id, saved);
    else if (saved) clearProgress();
  } catch(e) {
    $('global-message').textContent = `Тестларни юклаб бўлмади: ${e.message}`;
    $('catalog-retry').hidden = false;
  }
}
$('catalog-retry').onclick = loadCatalog;
loadCatalog();
