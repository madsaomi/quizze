const $ = id => document.getElementById(id);
let testId, test, index = 0, answers = {}, transition, active = false, submitting = false;
let starting = false, checking = false, solved = false, attempt = 0;
function closeModal() { $('app-modal').close(); }
$('modal-cancel').onclick = closeModal;
$('modal-confirm').onclick = () => {
  closeModal(); active = false; clearTimeout(transition); screen('catalog');
};
function screen(id) {
  for (const name of ['catalog', 'quiz', 'result']) $(name).hidden = name !== id;
  $('global-message').textContent = '';
  window.scrollTo({top:0, behavior:'instant'});
}
async function api(url, body) {
  let res;
  try {
    res = await fetch(url, {signal:AbortSignal.timeout(15000), ...(body === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)})});
  } catch {
    throw Error('Серверга уланиб бўлмади. Қайта уриниб кўринг.');
  }
  let data;
  try { data = await res.json(); } catch { throw Error('Сервердан нотўғри жавоб келди.'); }
  if (!res.ok) throw Error(data.error || 'Сўровни бажариб бўлмади');
  return data;
}
async function start(id) {
  if (starting || submitting || active) return;
  starting = true;
  $('retry').disabled = true;
  try {
    test = await api(`/api/tests/${encodeURIComponent(id)}`);
    testId = id; index = 0; answers = {}; active = true; submitting = false;
    attempt++; checking = false; solved = false; $('next').hidden = true; $('next').disabled = false; $('exit').disabled = false; $('quiz-title').textContent = test.title;
    screen('quiz'); showQuestion();
  } catch (e) { $('global-message').textContent = e.message; }
  finally { starting = false; $('retry').disabled = false; }
}
function showQuestion() {
  clearTimeout(transition);
  const q = test.questions[index];
  $('counter').textContent = `${index + 1}-савол / ${test.questions.length} та`;
  $('progress-fill').style.width = `${index / test.questions.length * 100}%`;
  document.querySelector('.progress').setAttribute('aria-valuenow', Math.round(index / test.questions.length * 100));
  $('question-text').textContent = q.text;
  $('options').replaceChildren();
  for (const [key, text] of Object.entries(q.options)) {
    const label = document.createElement('label'); label.className = 'option';
    const input = document.createElement('input'); input.type = 'radio'; input.name = 'answer'; input.value = key;
    const letter = document.createElement('span'); letter.className = 'option-letter'; letter.textContent = key;
    const content = document.createElement('span'); content.textContent = text;
    content.className = 'option-text';
    input.onchange = () => checkChoice(input, label);
    label.append(input, letter, content); $('options').append(label);
  }
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    $('question-text').animate([{opacity:0,transform:'translateY(5px)'},{opacity:1,transform:'translateY(0)'}], {duration:180,easing:'ease-out'});
    $('options').animate([{opacity:0},{opacity:1}], {duration:220});
  }
  $('quiz-message').textContent = '';
  solved = false;
  $('quiz-message').classList.remove('success');
  $('question-text').focus();
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
      solved = true;
      label.classList.add('answer-correct');
      $('quiz-message').classList.add('success');
      $('quiz-message').textContent = 'Тўғри!';
      transition = setTimeout(() => {
        if (!active || attempt !== currentAttempt) return;
        if ($('app-modal').open) closeModal();
        index++;
        if (index < test.questions.length) showQuestion(); else finish();
      }, 1100);
    } else {
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
  clearTimeout(transition); active = false; submitting = true;
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
  } catch (e) {
    $('quiz-message').textContent = `${e.message}. Қайта юбориш мумкин.`;
    $('next').hidden = false; $('next').disabled = false; $('exit').disabled = false; $('next').textContent = 'Қайта юбориш';
  } finally { submitting = false; }
}
$('next').onclick = finish;
$('exit').onclick = () => $('app-modal').showModal();
$('retry').onclick = () => start(testId);
$('home').onclick = () => screen('catalog');
window.addEventListener('beforeunload', e => { if (active || submitting) { e.preventDefault(); e.returnValue = ''; } });
async function loadCatalog() {
  try {
    for (const entry of await api('/api/tests')) {
      const card = document.createElement('article'); card.className = 'test-card';
      const icon = document.createElement('span'); icon.className = 'subject-icon'; icon.setAttribute('aria-hidden','true'); icon.textContent = '✎';
      const content = document.createElement('div'); content.className = 'test-content';
      const title = document.createElement('h2'); title.textContent = entry.title;
      const meta = document.createElement('p'); meta.className = 'muted'; meta.textContent = `${entry.count} та савол · вақт чекланмаган`;
      const button = document.createElement('button'); button.className = 'primary'; button.textContent = 'Бошлаш';
      button.onclick = async () => { button.disabled = true; await start(entry.id); button.disabled = false; };
      content.append(title, meta); card.append(icon, content, button); $('test-list').append(card);
    }
  } catch(e) { $('global-message').textContent = `Тестларни юклаб бўлмади: ${e.message}`; }
}
loadCatalog();
