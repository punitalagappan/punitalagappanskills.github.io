// ============================================
// PunitAlagappan Kasi - Portfolio Admin & UI
// ============================================

// Admin password (CHANGE THIS before deploying)
const PASS = 'punit2026';

// ===== ADMIN PANEL =====
function openA() {
  document.getElementById('ap').classList.add('o');
  document.getElementById('ao').classList.add('o');
}

function closeA() {
  document.getElementById('ap').classList.remove('o');
  document.getElementById('ao').classList.remove('o');
}

function tryL() {
  if (document.getElementById('pw').value === PASS) {
    document.getElementById('lv').style.display = 'none';
    document.getElementById('av').style.display = 'block';
    renderL();
  } else {
    alert('Wrong password');
  }
}

// ===== EXTRA PROJECTS (added via admin) =====
let EP = JSON.parse(localStorage.getItem('pk_ep2') || '[]');

function sv() {
  localStorage.setItem('pk_ep2', JSON.stringify(EP));
}

function addP() {
  const m1 = document.getElementById('eM1').value.split('|');
  const m2 = document.getElementById('eM2').value.split('|');

  EP.push({
    type: document.getElementById('eT').value,
    title: document.getElementById('eTi').value,
    desc: document.getElementById('eD').value,
    m1v: (m1[0] || '').trim(),
    m1l: (m1[1] || '').trim(),
    m2v: (m2[0] || '').trim(),
    m2l: (m2[1] || '').trim(),
    dl: document.getElementById('eDl').value
  });

  sv();
  renderL();
  renderExtra();

  // Clear form
  document.getElementById('eT').value = '';
  document.getElementById('eTi').value = '';
  document.getElementById('eD').value = '';
  document.getElementById('eM1').value = '';
  document.getElementById('eM2').value = '';
  document.getElementById('eDl').value = '';

  alert('Project added!');
}

function renderL() {
  document.getElementById('pL').innerHTML =
    '<div class="as-t" style="margin-top:10px">Added Projects</div>' +
    EP.map((p, i) =>
      `<div class="ap-i">
        <span>${p.title.substring(0, 28)}${p.title.length > 28 ? '...' : ''}</span>
        <button class="ab-d2" onclick="delP(${i})">X</button>
      </div>`
    ).join('') +
    (EP.length === 0 ? '<p style="font-size:.72rem;color:var(--t3)">No extra projects added yet. Your built-in projects are already on the page.</p>' : '');
}

function delP(i) {
  if (confirm('Delete this project?')) {
    EP.splice(i, 1);
    sv();
    renderL();
    renderExtra();
  }
}

function renderExtra() {
  const c = document.getElementById('extraProj');
  if (!c || EP.length === 0) {
    if (c) c.innerHTML = '';
    return;
  }

  c.innerHTML =
    '<div class="cat-label" style="padding-left:clamp(16px,5vw,72px);padding-right:clamp(16px,5vw,72px)">Additional Projects</div>' +
    '<div class="pg">' +
    EP.map(p =>
      `<div class="pi">
        <div class="pi-t">${p.type}</div>
        <div class="pi-ti">${p.title}</div>
        ${p.m1v ? `<div class="pi-km">
          <div><div class="pi-kv">${p.m1v}</div><div class="pi-kl">${p.m1l}</div></div>
          ${p.m2v ? `<div><div class="pi-kv">${p.m2v}</div><div class="pi-kl">${p.m2l}</div></div>` : ''}
        </div>` : ''}
        <div class="pi-d">${p.desc}</div>
        ${p.dl ? `<a href="${p.dl}" class="dl" download>Download</a>` : ''}
      </div>`
    ).join('') +
    '</div>';
}

// ===== NAV SCROLL EFFECT =====
window.addEventListener('scroll', function() {
  document.getElementById('nv').classList.toggle('s', window.scrollY > 30);
});

// ===== SCROLL REVEAL ANIMATION =====
const observer = new IntersectionObserver(function(entries) {
  entries.forEach(function(entry) {
    if (entry.isIntersecting) {
      entry.target.classList.add('v');
      observer.unobserve(entry.target);
    }
  });
}, { threshold: 0.06 });

document.querySelectorAll('.rv').forEach(function(el) {
  observer.observe(el);
});

// ===== MOBILE NAV =====
function toggleMobileNav() {
  document.querySelector('.mn').classList.toggle('op');
}

// ===== INIT =====
renderExtra();
