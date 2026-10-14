/**
 * Field Builder & Overlay Manager
 * Handles placing, moving, resizing, styling, and interacting with document fields.
 * STRICT SECURITY: Enforces that users can ONLY sign fields designated to their legal identity.
 */
class FieldBuilder {
  constructor(options = {}) {
    this.fields = [];
    this.selectedFieldId = null;
    this.mode = options.mode || 'self-sign'; // 'self-sign' | 'envelope-builder' | 'signer'
    this.currentSignerId = options.currentSignerId || 'self';
    this.currentUser = options.currentUser || null;
    this.activeSigners = options.activeSigners || []; // list of { id, name, email, color }
    this.onFieldChange = options.onFieldChange || null;
    this.activeDrag = null;
    this.activeResize = null;

    this.attachGlobalEvents();
  }

  setMode(mode, currentSignerId = 'self', activeSigners = [], currentUser = null) {
    this.mode = mode;
    this.currentSignerId = currentSignerId;
    this.activeSigners = activeSigners;
    if (currentUser) this.currentUser = currentUser;
    this.renderAllFields();
  }

  setCurrentUser(user) {
    this.currentUser = user;
    this.renderAllFields();
  }

  setFields(fields) {
    this.fields = fields || [];
    this.renderAllFields();
  }

  getFields() {
    return this.fields;
  }

  addField(type, page = 1, rel_x = 0.15, rel_y = 0.25, assigned_to = null) {
    const fieldId = 'f_' + Math.random().toString(36).substring(2, 9);
    
    let rel_width = 0.25;
    let rel_height = 0.05;

    if (type === 'checkbox') {
      rel_width = 0.035;
      rel_height = 0.025;
    } else if (type === 'initials') {
      rel_width = 0.12;
      rel_height = 0.045;
    } else if (type === 'date') {
      rel_width = 0.18;
      rel_height = 0.04;
    }

    const assignedId = assigned_to || this.currentSignerId;
    const signerInfo = this.getSignerInfo(assignedId);

    const newField = {
      id: fieldId,
      type: type,
      page: page,
      rel_x: Math.max(0.01, Math.min(0.8, rel_x)),
      rel_y: Math.max(0.01, Math.min(0.9, rel_y)),
      rel_width: rel_width,
      rel_height: rel_height,
      assigned_to: assignedId,
      assigned_name: signerInfo.name,
      assigned_email: signerInfo.email || null,
      required: true,
      value: type === 'date' ? new Date().toISOString().split('T')[0] : (type === 'checkbox' ? 'false' : null),
      label: type.charAt(0).toUpperCase() + type.slice(1)
    };

    this.fields.push(newField);
    this.renderField(newField);
    this.selectedFieldId = fieldId;

    if (this.onFieldChange) this.onFieldChange(this.fields);
    return newField;
  }

  removeField(fieldId) {
    this.fields = this.fields.filter(f => f.id !== fieldId);
    const el = document.getElementById(`field-${fieldId}`);
    if (el) el.remove();
    if (this.onFieldChange) this.onFieldChange(this.fields);
  }

  getSignerInfo(signerId) {
    if (signerId === 'self') {
      const uName = this.currentUser ? this.currentUser.name : 'You (Self)';
      const uEmail = this.currentUser ? this.currentUser.email : 'self@signer.local';
      return { name: uName, email: uEmail, color: '#2563eb' };
    }
    const found = this.activeSigners.find(s => s.id === signerId);
    return found || { name: 'Signer', email: 'signer@example.com', color: '#2563eb' };
  }

  renderAllFields() {
    document.querySelectorAll('.doc-field-box').forEach(el => el.remove());
    for (const f of this.fields) {
      this.renderField(f);
    }
  }

  renderField(field) {
    const overlay = document.getElementById(`pdf-overlay-${field.page}`);
    if (!overlay) return;

    let el = document.getElementById(`field-${field.id}`);
    if (!el) {
      el = document.createElement('div');
      el.id = `field-${field.id}`;
      overlay.appendChild(el);
    }

    const signerInfo = this.getSignerInfo(field.assigned_to);
    const overlayWidth = overlay.clientWidth;
    const overlayHeight = overlay.clientHeight;

    const left = field.rel_x * overlayWidth;
    const top = field.rel_y * overlayHeight;
    const width = field.rel_width * overlayWidth;
    const height = field.rel_height * overlayHeight;

    const isLockedForCurrentUser = (this.mode === 'envelope-builder' || this.mode === 'signer') &&
      field.assigned_to !== 'self' && field.assigned_to !== this.currentSignerId;

    el.className = `doc-field-box ${field.value ? 'signed' : ''} ${this.selectedFieldId === field.id ? 'selected' : ''} ${isLockedForCurrentUser ? 'opacity-85' : ''}`;
    el.style.left = `${left}px`;
    el.style.top = `${top}px`;
    el.style.width = `${Math.max(24, width)}px`;
    el.style.height = `${Math.max(20, height)}px`;
    el.style.borderColor = signerInfo.color;

    // Content
    let contentHtml = '';
    if (field.value) {
      if (field.type === 'signature' || field.type === 'initials') {
        if (field.value.startsWith('data:image')) {
          contentHtml = `<img src="${field.value}" class="max-h-full max-w-full object-contain pointer-events-none" />`;
        } else {
          contentHtml = `<span class="text-blue-700 font-semibold italic text-sm pointer-events-none">${field.value}</span>`;
        }
      } else if (field.type === 'checkbox') {
        const isChecked = field.value === 'true' || field.value === 'checked';
        contentHtml = `<div class="w-full h-full flex items-center justify-center font-bold text-blue-600 text-sm">${isChecked ? '✓' : ''}</div>`;
      } else {
        contentHtml = `<span class="text-slate-800 text-xs font-medium px-1 truncate pointer-events-none">${field.value}</span>`;
      }
    } else {
      const iconMap = {
        signature: '✍️ Signature',
        initials: '🔏 Initials',
        date: '📅 Date',
        text: '📝 Text',
        checkbox: '☑'
      };
      contentHtml = `
        <div class="flex items-center gap-1 text-[11px] font-semibold text-slate-700 pointer-events-none">
          <span>${iconMap[field.type] || field.type}</span>
        </div>
      `;
    }

    // Controls
    let controlsHtml = '';
    if (this.mode !== 'signer') {
      controlsHtml += `<div class="field-delete-btn" title="Remove Field" data-id="${field.id}">&times;</div>`;
      controlsHtml += `<div class="field-resize-handle" data-id="${field.id}"></div>`;
    }

    // Signer badge if multi-party
    let badgeHtml = '';
    if (this.mode === 'envelope-builder' && field.assigned_to) {
      badgeHtml = `
        <div class="absolute -top-3 left-1 px-1.5 py-0.2 text-[9px] font-bold text-white rounded flex items-center gap-1 pointer-events-none shadow" style="background-color: ${signerInfo.color}">
          ${isLockedForCurrentUser ? '🔒 ' : ''}${signerInfo.name}
        </div>
      `;
    }

    el.innerHTML = `${badgeHtml}${contentHtml}${controlsHtml}`;
    this.bindFieldEvents(el, field);
  }

  bindFieldEvents(el, field) {
    const deleteBtn = el.querySelector('.field-delete-btn');
    if (deleteBtn) {
      deleteBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeField(field.id);
      });
    }

    const resizeHandle = el.querySelector('.field-resize-handle');
    if (resizeHandle) {
      resizeHandle.addEventListener('mousedown', (e) => {
        e.stopPropagation();
        this.startResize(e, field);
      });
    }

    el.addEventListener('mousedown', (e) => {
      if (e.target.classList.contains('field-delete-btn') || e.target.classList.contains('field-resize-handle')) {
        return;
      }
      this.selectedFieldId = field.id;
      this.renderAllFields();

      if (this.mode !== 'signer') {
        this.startDrag(e, field);
      }
    });

    el.addEventListener('click', (e) => {
      e.stopPropagation();
      this.handleFieldClick(field);
    });
  }

  showSecurityViolationModal(targetSignerName) {
    const modal = document.getElementById('securityViolationModal');
    if (!modal) {
      alert(`Security Violation: You can only sign fields designated for your name. This field belongs to ${targetSignerName}.`);
      return;
    }
    const currentName = this.currentUser ? this.currentUser.name : 'Your Current Identity';
    document.getElementById('violation-current-user').innerText = currentName;
    document.getElementById('violation-target-signer').innerText = targetSignerName;
    modal.classList.remove('hidden');
    modal.classList.add('flex');

    document.getElementById('btn-close-violation')?.addEventListener('click', () => {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    });
  }

  handleFieldClick(field) {
    const targetSignerInfo = this.getSignerInfo(field.assigned_to);

    // STRICT ACCESS & PRIVACY RULE:
    // If field is assigned to another signer, reject signing attempt!
    if (this.mode === 'envelope-builder') {
      if (field.assigned_to !== this.currentSignerId && field.assigned_to !== 'self') {
        this.showSecurityViolationModal(targetSignerInfo.name);
        return;
      }
    } else if (this.mode === 'signer') {
      if (field.assigned_to !== this.currentSignerId) {
        this.showSecurityViolationModal(targetSignerInfo.name);
        return;
      }
    }

    const userLegalName = this.currentUser ? this.currentUser.name : 'Signer';

    if (field.type === 'signature' || field.type === 'initials') {
      window.signatureManager.open({
        initialName: userLegalName,
        onSave: (dataUrl, verifiedName) => {
          field.value = dataUrl;
          field.signed_by_name = verifiedName;
          field.signed_by_email = this.currentUser ? this.currentUser.email : null;
          field.signed_at = new Date().toISOString();
          this.renderField(field);
          if (this.onFieldChange) this.onFieldChange(this.fields);
        }
      });
    } else if (field.type === 'date') {
      const cur = field.value || new Date().toISOString().split('T')[0];
      const newDate = prompt("Confirm date (YYYY-MM-DD):", cur);
      if (newDate !== null) {
        field.value = newDate.trim();
        this.renderField(field);
        if (this.onFieldChange) this.onFieldChange(this.fields);
      }
    } else if (field.type === 'text') {
      const cur = field.value || (field.label === 'Name' ? userLegalName : '');
      const newText = prompt(`Enter text (${field.label || 'Value'}):`, cur);
      if (newText !== null) {
        field.value = newText;
        this.renderField(field);
        if (this.onFieldChange) this.onFieldChange(this.fields);
      }
    } else if (field.type === 'checkbox') {
      const isChecked = field.value === 'true' || field.value === 'checked';
      field.value = isChecked ? 'false' : 'true';
      this.renderField(field);
      if (this.onFieldChange) this.onFieldChange(this.fields);
    }
  }

  startDrag(e, field) {
    const overlay = document.getElementById(`pdf-overlay-${field.page}`);
    if (!overlay) return;

    const startX = e.clientX;
    const startY = e.clientY;
    const startLeft = field.rel_x * overlay.clientWidth;
    const startTop = field.rel_y * overlay.clientHeight;

    this.activeDrag = { field, overlay, startX, startY, startLeft, startTop };
  }

  startResize(e, field) {
    const overlay = document.getElementById(`pdf-overlay-${field.page}`);
    if (!overlay) return;

    this.activeResize = {
      field,
      overlay,
      startX: e.clientX,
      startY: e.clientY,
      startWidth: field.rel_width * overlay.clientWidth,
      startHeight: field.rel_height * overlay.clientHeight
    };
  }

  attachGlobalEvents() {
    window.addEventListener('mousemove', (e) => {
      if (this.activeDrag) {
        const { field, overlay, startX, startY, startLeft, startTop } = this.activeDrag;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        const overlayWidth = overlay.clientWidth;
        const overlayHeight = overlay.clientHeight;
        const fieldWidth = field.rel_width * overlayWidth;
        const fieldHeight = field.rel_height * overlayHeight;

        let newLeft = Math.max(0, Math.min(overlayWidth - fieldWidth, startLeft + dx));
        let newTop = Math.max(0, Math.min(overlayHeight - fieldHeight, startTop + dy));

        field.rel_x = newLeft / overlayWidth;
        field.rel_y = newTop / overlayHeight;

        const el = document.getElementById(`field-${field.id}`);
        if (el) {
          el.style.left = `${newLeft}px`;
          el.style.top = `${newTop}px`;
        }
      } else if (this.activeResize) {
        const { field, overlay, startX, startY, startWidth, startHeight } = this.activeResize;
        const dx = e.clientX - startX;
        const dy = e.clientY - startY;

        const overlayWidth = overlay.clientWidth;
        const overlayHeight = overlay.clientHeight;

        let newWidth = Math.max(30, Math.min(overlayWidth * 0.9, startWidth + dx));
        let newHeight = Math.max(20, Math.min(overlayHeight * 0.5, startHeight + dy));

        field.rel_width = newWidth / overlayWidth;
        field.rel_height = newHeight / overlayHeight;

        const el = document.getElementById(`field-${field.id}`);
        if (el) {
          el.style.width = `${newWidth}px`;
          el.style.height = `${newHeight}px`;
        }
      }
    });

    window.addEventListener('mouseup', () => {
      if (this.activeDrag || this.activeResize) {
        this.activeDrag = null;
        this.activeResize = null;
        if (this.onFieldChange) this.onFieldChange(this.fields);
      }
    });
  }
}

window.FieldBuilder = FieldBuilder;
