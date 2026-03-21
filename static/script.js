// ─── State ───────────────────────────────────────────────────────
const state = {
  files: [],
  cols: 3,
  rows: 5,
  currentStep: 1,
  downloadUrl: null,
};

// ─── DOM refs ─────────────────────────────────────────────────────
const uploadZone   = document.getElementById('uploadZone');
const fileInput    = document.getElementById('fileInput');
const previewGrid  = document.getElementById('previewGrid');
const actionRow    = document.getElementById('actionRow');
const photoCount   = document.getElementById('photoCount');
const clearBtn     = document.getElementById('clearBtn');
const nextBtn      = document.getElementById('nextBtn');
const backBtn      = document.getElementById('backBtn');
const generateBtn  = document.getElementById('generateBtn');
const restartBtn   = document.getElementById('restartBtn');
const colsInput    = document.getElementById('colsInput');
const rowsInput    = document.getElementById('rowsInput');
const cardTotal    = document.getElementById('cardTotal');
const gridPreview  = document.getElementById('gridPreview');
const downloadBtn  = document.getElementById('downloadBtn');
const resultMeta   = document.getElementById('resultMeta');

// ─── Step navigation ──────────────────────────────────────────────
function goToStep(n) {
  document.querySelectorAll('.step').forEach(s => s.classList.add('hidden'));
  document.getElementById(`step-${['upload','config','result'][n-1]}`).classList.remove('hidden');

  document.querySelectorAll('.progress-step').forEach((el, i) => {
    el.classList.remove('active', 'done');
    if (i + 1 < n)  el.classList.add('done');
    if (i + 1 === n) el.classList.add('active');
  });

  state.currentStep = n;
  if (n === 2) renderGridPreview();
}

// ─── File handling ────────────────────────────────────────────────
fileInput.addEventListener('change', e => handleFiles(Array.from(e.target.files)));

uploadZone.addEventListener('dragover', e => {
  e.preventDefault();
  uploadZone.classList.add('drag-over');
});
uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('drag-over'));
uploadZone.addEventListener('drop', e => {
  e.preventDefault();
  uploadZone.classList.remove('drag-over');
  handleFiles(Array.from(e.dataTransfer.files).filter(f => f.type.startsWith('image/')));
});

function handleFiles(newFiles) {
  newFiles.forEach(file => {
    if (!file.type.startsWith('image/')) return;
    state.files.push(file);
    addPreview(file, state.files.length - 1);
  });
  updateActionRow();
  // reset input so same file can be re-selected
  fileInput.value = '';
}

function addPreview(file, index) {
  const reader = new FileReader();
  reader.onload = e => {
    const item = document.createElement('div');
    item.className = 'preview-item';
    item.dataset.index = index;
    item.innerHTML = `
      <img src="${e.target.result}" alt="Página ${index + 1}" />
      <button class="remove-btn" title="Eliminar">✕</button>
    `;
    item.querySelector('.remove-btn').addEventListener('click', ev => {
      ev.stopPropagation();
      removeFile(parseInt(item.dataset.index));
    });
    previewGrid.appendChild(item);
  };
  reader.readAsDataURL(file);
}

function removeFile(index) {
  state.files.splice(index, 1);
  // Re-render all previews
  previewGrid.innerHTML = '';
  state.files.forEach((f, i) => addPreview(f, i));
  updateActionRow();
}

function updateActionRow() {
  const n = state.files.length;
  actionRow.style.display = n > 0 ? 'flex' : 'none';
  photoCount.textContent = `${n} página${n !== 1 ? 's' : ''} seleccionada${n !== 1 ? 's' : ''}`;
}

clearBtn.addEventListener('click', () => {
  state.files = [];
  previewGrid.innerHTML = '';
  updateActionRow();
});

nextBtn.addEventListener('click', () => {
  if (state.files.length === 0) {
    toast('Añade al menos una imagen', 'error');
    return;
  }
  goToStep(2);
});

// ─── Config ───────────────────────────────────────────────────────
document.querySelectorAll('.stepper-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    const target = document.getElementById(btn.dataset.target);
    const delta  = parseInt(btn.dataset.delta);
    const min    = parseInt(target.min);
    const max    = parseInt(target.max);
    const newVal = Math.min(max, Math.max(min, parseInt(target.value) + delta));
    target.value = newVal;
    onConfigChange();
  });
});

colsInput.addEventListener('input', onConfigChange);
rowsInput.addEventListener('input', onConfigChange);

function onConfigChange() {
  state.cols = Math.max(1, Math.min(6, parseInt(colsInput.value) || 1));
  state.rows = Math.max(1, Math.min(8, parseInt(rowsInput.value) || 1));
  colsInput.value = state.cols;
  rowsInput.value = state.rows;
  cardTotal.textContent = state.cols * state.rows;
  renderGridPreview();
}

function renderGridPreview() {
  gridPreview.innerHTML = '';
  gridPreview.style.gridTemplateColumns = `repeat(${state.cols}, 1fr)`;
  const total = state.cols * state.rows;
  for (let i = 0; i < total; i++) {
    const cell = document.createElement('div');
    cell.className = 'grid-cell';
    gridPreview.appendChild(cell);
  }
  // Animate cells with class q/a alternating for visual
  gridPreview.querySelectorAll('.grid-cell').forEach((c, i) => {
    setTimeout(() => c.classList.add(i % 2 === 0 ? 'q' : 'a'), i * 12);
  });
}

backBtn.addEventListener('click', () => goToStep(1));

// ─── Generate ─────────────────────────────────────────────────────
generateBtn.addEventListener('click', async () => {
  if (state.files.length === 0) {
    toast('No hay imágenes para procesar', 'error');
    return;
  }

  setGenerating(true);

  const formData = new FormData();
  state.files.forEach((file, i) => formData.append('images', file, `page_${i + 1}.jpg`));
  formData.append('cols', state.cols);
  formData.append('rows', state.rows);

  try {
    const response = await fetch('generate', {
      method: 'POST',
      body: formData,
    });

    if (!response.ok) {
      const err = await response.json().catch(() => ({ error: 'Error del servidor' }));
      throw new Error(err.error || `Error ${response.status}`);
    }

    const blob = await response.blob();
    const url  = URL.createObjectURL(blob);
    state.downloadUrl = url;

    downloadBtn.href = url;
    resultMeta.textContent = `${state.files.length} página(s) · ${state.cols}×${state.rows} tarjetas/hoja`;

    goToStep(3);
    toast('¡PDF generado con éxito!', 'success');

  } catch (err) {
    toast(`Error: ${err.message}`, 'error');
    console.error(err);
  } finally {
    setGenerating(false);
  }
});

function setGenerating(loading) {
  generateBtn.disabled = loading;
  generateBtn.querySelector('.btn-text').style.display  = loading ? 'none' : '';
  generateBtn.querySelector('.btn-loader').style.display = loading ? 'flex' : 'none';
}

// ─── Restart ──────────────────────────────────────────────────────
restartBtn.addEventListener('click', () => {
  state.files = [];
  state.cols  = 3;
  state.rows  = 5;
  state.downloadUrl = null;
  previewGrid.innerHTML = '';
  colsInput.value = 3;
  rowsInput.value = 5;
  cardTotal.textContent = 15;
  updateActionRow();
  goToStep(1);
  if (state.downloadUrl) URL.revokeObjectURL(state.downloadUrl);
});

// ─── Toast ────────────────────────────────────────────────────────
function toast(msg, type = 'info') {
  const container = document.getElementById('toastContainer');
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    el.style.transition = 'opacity 0.3s';
    setTimeout(() => el.remove(), 300);
  }, 3500);
}

// ─── Init ─────────────────────────────────────────────────────────
goToStep(1);
