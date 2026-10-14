/**
 * Signature Pad Modal Manager
 * Supports: Authenticated Typing (Free for all users), Smooth Hand-Drawing (Premium / ₹50), Image Upload (Premium / ₹50)
 * STRICT SECURITY: Legal identity is bound exclusively to verified authenticated user's name.
 */
class SignatureManager {
  constructor() {
    this.currentMode = 'type'; // 'type' is the default for all users
    this.penColor = '#1e3a8a'; // classic ink navy
    this.strokeWidth = 2.5;
    this.isDrawing = false;
    this.points = [];
    this.strokeHistory = [];
    this.onSaveCallback = null;
    this.selectedFont = 'Caveat';
    this.uploadedImageSrc = null;
    this.verifiedLegalName = 'Signer';

    this.initElements();
    this.attachEventListeners();
  }

  initElements() {
    this.modal = document.getElementById('signatureModal');
    this.canvas = document.getElementById('sig-canvas');
    if (this.canvas) {
      this.ctx = this.canvas.getContext('2d');
    }
    this.typeInput = document.getElementById('sig-type-input');
    this.uploadInput = document.getElementById('sig-upload-input');
    this.previewImg = document.getElementById('sig-upload-preview');
    this.legalNameBadge = document.getElementById('modal-legal-name');
  }

  checkPremiumStatus() {
    // Check if app user is premium or has credits
    const user = window.docuSignApp?.currentUser;
    if (user && (user.is_premium || user.premium_credits > 0)) {
      return true;
    }
    // Check if recipient ceremony signer is premium
    if (window.signerViewApp?.isPremium) {
      return true;
    }
    return false;
  }

  open(options = {}) {
    this.onSaveCallback = options.onSave || null;
    this.verifiedLegalName = options.initialName || (window.docuSignApp?.currentUser?.name) || 'Signer';
    
    if (this.modal) {
      this.modal.classList.remove('hidden');
      this.modal.classList.add('flex');
    }

    if (this.legalNameBadge) {
      this.legalNameBadge.innerText = this.verifiedLegalName;
    }

    if (this.typeInput) {
      this.typeInput.value = this.verifiedLegalName;
      this.typeInput.readOnly = true; // Lock according to security terms
      this.renderTypedSignatureList(this.verifiedLegalName);
    }

    // Default to 'type' mode for all users
    this.setMode('type');
    this.updatePremiumBadges();
  }

  close() {
    if (this.modal) {
      this.modal.classList.add('hidden');
      this.modal.classList.remove('flex');
    }
  }

  updatePremiumBadges() {
    const isPrem = this.checkPremiumStatus();
    const drawBadge = document.getElementById('draw-tab-badge');
    const uploadBadge = document.getElementById('upload-tab-badge');

    if (drawBadge) {
      drawBadge.innerHTML = isPrem ? `<span class="text-[9px] text-emerald-600 font-bold ml-1">✓ Unlocked</span>` : `<span class="text-[9px] text-amber-600 font-bold ml-1">🔒 ₹50</span>`;
    }
    if (uploadBadge) {
      uploadBadge.innerHTML = isPrem ? `<span class="text-[9px] text-emerald-600 font-bold ml-1">✓ Unlocked</span>` : `<span class="text-[9px] text-amber-600 font-bold ml-1">🔒 ₹50</span>`;
    }

    // Update draw lock overlay
    const drawLock = document.getElementById('draw-premium-lock');
    const drawCanvasBox = document.getElementById('draw-canvas-box');
    if (drawLock && drawCanvasBox) {
      if (isPrem) {
        drawLock.classList.add('hidden');
        drawCanvasBox.classList.remove('hidden');
      } else {
        drawLock.classList.remove('hidden');
        drawCanvasBox.classList.add('hidden');
      }
    }

    // Update upload lock overlay
    const uploadLock = document.getElementById('upload-premium-lock');
    const uploadBox = document.getElementById('upload-content-box');
    if (uploadLock && uploadBox) {
      if (isPrem) {
        uploadLock.classList.add('hidden');
        uploadBox.classList.remove('hidden');
      } else {
        uploadLock.classList.remove('hidden');
        uploadBox.classList.add('hidden');
      }
    }
  }

  setMode(mode) {
    this.currentMode = mode;
    this.updatePremiumBadges();

    ['type', 'draw', 'upload'].forEach(m => {
      const tabBtn = document.getElementById(`tab-btn-${m}`);
      const pane = document.getElementById(`tab-pane-${m}`);
      if (tabBtn && pane) {
        if (m === mode) {
          tabBtn.className = "flex-1 py-3 text-center text-xs font-bold border-b-2 border-blue-600 text-blue-600";
          pane.classList.remove('hidden');
        } else {
          tabBtn.className = "flex-1 py-3 text-center text-xs font-medium text-slate-500 hover:text-slate-700 border-b-2 border-transparent";
          pane.classList.add('hidden');
        }
      }
    });

    if (mode === 'draw' && this.checkPremiumStatus()) {
      setTimeout(() => this.resizeCanvas(), 50);
    }
  }

  resizeCanvas() {
    if (!this.canvas) return;
    const rect = this.canvas.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.redrawCanvas();
  }

  resetCanvas() {
    this.points = [];
    this.strokeHistory = [];
    if (!this.canvas || !this.ctx) return;
    const dpr = window.devicePixelRatio || 1;
    this.ctx.clearRect(0, 0, this.canvas.width / dpr, this.canvas.height / dpr);
  }

  undoStroke() {
    if (this.strokeHistory.length > 0) {
      this.strokeHistory.pop();
      this.redrawCanvas();
    }
  }

  redrawCanvas() {
    const dpr = window.devicePixelRatio || 1;
    this.ctx.clearRect(0, 0, this.canvas.width / dpr, this.canvas.height / dpr);

    for (const stroke of this.strokeHistory) {
      this.ctx.beginPath();
      this.ctx.strokeStyle = stroke.color;
      this.ctx.lineWidth = stroke.width;
      this.ctx.lineCap = 'round';
      this.ctx.lineJoin = 'round';

      const pts = stroke.points;
      if (pts.length < 2) continue;

      this.ctx.moveTo(pts[0].x, pts[0].y);
      for (let i = 1; i < pts.length - 1; i++) {
        const xc = (pts[i].x + pts[i + 1].x) / 2;
        const yc = (pts[i].y + pts[i + 1].y) / 2;
        this.ctx.quadraticCurveTo(pts[i].x, pts[i].y, xc, yc);
      }
      this.ctx.lineTo(pts[pts.length - 1].x, pts[pts.length - 1].y);
      this.ctx.stroke();
    }
  }

  attachEventListeners() {
    if (!this.canvas) return;

    const getPos = (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const clientX = e.touches ? e.touches[0].clientX : e.clientX;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      return {
        x: clientX - rect.left,
        y: clientY - rect.top
      };
    };

    const startDraw = (e) => {
      if (!this.checkPremiumStatus()) return;
      e.preventDefault();
      this.isDrawing = true;
      const pos = getPos(e);
      this.points = [pos];
    };

    const moveDraw = (e) => {
      if (!this.isDrawing) return;
      e.preventDefault();
      const pos = getPos(e);
      this.points.push(pos);

      if (this.points.length > 2) {
        this.ctx.beginPath();
        this.ctx.strokeStyle = this.penColor;
        this.ctx.lineWidth = this.strokeWidth;
        this.ctx.lineCap = 'round';
        this.ctx.lineJoin = 'round';

        const p1 = this.points[this.points.length - 2];
        const p2 = this.points[this.points.length - 1];
        const xc = (p1.x + p2.x) / 2;
        const yc = (p1.y + p2.y) / 2;

        this.ctx.moveTo(p1.x, p1.y);
        this.ctx.quadraticCurveTo(p1.x, p1.y, xc, yc);
        this.ctx.stroke();
      }
    };

    const stopDraw = (e) => {
      if (!this.isDrawing) return;
      this.isDrawing = false;
      if (this.points.length > 0) {
        this.strokeHistory.push({
          color: this.penColor,
          width: this.strokeWidth,
          points: [...this.points]
        });
      }
      this.points = [];
      this.redrawCanvas();
    };

    this.canvas.addEventListener('mousedown', startDraw);
    window.addEventListener('mousemove', moveDraw);
    window.addEventListener('mouseup', stopDraw);

    this.canvas.addEventListener('touchstart', startDraw, { passive: false });
    window.addEventListener('touchmove', moveDraw, { passive: false });
    window.addEventListener('touchend', stopDraw);

    document.querySelectorAll('.pen-color-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.penColor = e.currentTarget.dataset.color;
        document.querySelectorAll('.pen-color-btn').forEach(b => b.classList.remove('ring-2', 'ring-offset-2', 'ring-blue-600'));
        e.currentTarget.classList.add('ring-2', 'ring-offset-2', 'ring-blue-600');
        this.renderTypedSignatureList(this.verifiedLegalName);
      });
    });

    const clearBtn = document.getElementById('sig-clear-btn');
    if (clearBtn) clearBtn.addEventListener('click', () => this.resetCanvas());

    const undoBtn = document.getElementById('sig-undo-btn');
    if (undoBtn) undoBtn.addEventListener('click', () => this.undoStroke());

    if (this.uploadInput) {
      this.uploadInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (file) {
          const reader = new FileReader();
          reader.onload = (loadEvt) => {
            this.uploadedImageSrc = loadEvt.target.result;
            if (this.previewImg) {
              this.previewImg.src = this.uploadedImageSrc;
              this.previewImg.classList.remove('hidden');
            }
          };
          reader.readAsDataURL(file);
        }
      });
    }

    const saveBtn = document.getElementById('sig-adopt-btn');
    if (saveBtn) {
      saveBtn.addEventListener('click', () => this.saveAndApply());
    }

    const cancelBtn = document.getElementById('sig-cancel-btn');
    if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());

    const closeX = document.getElementById('sig-close-x');
    if (closeX) closeX.addEventListener('click', () => this.close());

    // Bind all "Pay ₹50 to Unlock" buttons
    document.querySelectorAll('.btn-open-signature-payment').forEach(btn => {
      btn.addEventListener('click', () => {
        window.openSignaturePaymentModal();
      });
    });
  }

  renderTypedSignatureList(text) {
    const container = document.getElementById('typed-font-list');
    if (!container) return;
    const displayText = text.trim() || this.verifiedLegalName;
    const fonts = [
      { name: 'Caveat', font: 'Caveat, cursive' },
      { name: 'Dancing Script', font: 'Dancing Script, cursive' },
      { name: 'Satisfy', font: 'Satisfy, cursive' },
      { name: 'Pacifico', font: 'Pacifico, cursive' },
      { name: 'Great Vibes', font: 'Great Vibes, cursive' }
    ];

    container.innerHTML = fonts.map(f => `
      <div class="font-preview-item p-3.5 border rounded-xl flex items-center justify-between cursor-pointer ${this.selectedFont === f.name ? 'active' : 'border-slate-200'}" data-font="${f.name}">
        <div>
          <p class="text-2xl text-slate-800" style="font-family: ${f.font}; color: ${this.penColor};">${displayText}</p>
          <span class="text-[10px] text-slate-400 font-medium">${f.name}</span>
        </div>
        <div class="w-5 h-5 rounded-full border-2 flex items-center justify-center ${this.selectedFont === f.name ? 'border-blue-600 bg-blue-600 text-white' : 'border-slate-300'}">
          ${this.selectedFont === f.name ? '✓' : ''}
        </div>
      </div>
    `).join('');

    container.querySelectorAll('.font-preview-item').forEach(item => {
      item.addEventListener('click', () => {
        this.selectedFont = item.dataset.font;
        this.renderTypedSignatureList(this.verifiedLegalName);
      });
    });
  }

  generateTypedSignatureDataUrl(text, fontName) {
    const c = document.createElement('canvas');
    c.width = 600;
    c.height = 180;
    const ctx = c.getContext('2d');
    ctx.clearRect(0, 0, c.width, c.height);

    ctx.font = `64px "${fontName}", cursive`;
    ctx.fillStyle = this.penColor;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, c.width / 2, c.height / 2);

    return c.toDataURL('image/png');
  }

  saveAndApply() {
    let resultDataUrl = null;
    const legalName = this.verifiedLegalName;

    if (this.currentMode === 'type') {
      resultDataUrl = this.generateTypedSignatureDataUrl(legalName, this.selectedFont);
    } else if (this.currentMode === 'draw') {
      if (!this.checkPremiumStatus()) {
        window.openSignaturePaymentModal();
        return;
      }
      if (this.strokeHistory.length === 0) {
        alert("Please draw your signature before adopting.");
        return;
      }
      resultDataUrl = this.canvas.toDataURL('image/png');
    } else if (this.currentMode === 'upload') {
      if (!this.checkPremiumStatus()) {
        window.openSignaturePaymentModal();
        return;
      }
      if (!this.uploadedImageSrc) {
        alert("Please upload a signature image first.");
        return;
      }
      resultDataUrl = this.uploadedImageSrc;
    }

    if (this.onSaveCallback && resultDataUrl) {
      // Signature is strictly bound to verified legal name
      this.onSaveCallback(resultDataUrl, legalName);
    }

    this.close();
  }
}

window.signatureManager = new SignatureManager();
