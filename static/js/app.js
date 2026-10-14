/**
 * DocuSign Pro - Enterprise Application Controller
 * Dashboard First, Studio, Self-Signing, Multi-Party Workflow & Certified Audit Trail
 * STRICT COMPLIANCE: ESIGN Act & UETA Identity Protection
 */
class DocuSignApp {
  constructor() {
    // Read initial tab from URL param or default to dashboard
    const urlParams = new URLSearchParams(window.location.search);
    this.currentTab = urlParams.get('tab') || 'dashboard'; // 'dashboard' is primary
    this.currentDocument = null;
    this.workflowMode = 'self-sign';
    this.pdfViewer = null;
    this.fieldBuilder = null;
    this.token = localStorage.getItem('docusign_token');
    this.currentUser = null;
    
    // Envelopes cache & filters
    this.allEnvelopes = [];
    this.statusFilter = 'all'; // 'all' | 'completed' | 'waiting'
    this.searchQuery = '';

    // Multi-party signers default
    this.signers = [
      { id: 'signer_1', name: 'Alice Smith', email: 'alice@corp.com', role: 'Disclosing Party', color: '#2563eb' },
      { id: 'signer_2', name: 'Bob Jones', email: 'bob@partner.com', role: 'Receiving Party', color: '#059669' }
    ];
    this.selectedSignerId = 'self';

    this.init();
  }

  async init() {
    // 1. Verify User Authentication
    const authed = await this.checkAuthentication();
    if (!authed) return;

    this.initPdfViewer();
    this.initFieldBuilder();
    this.bindEvents();
    
    // Switch to initial tab (Dashboard first)
    this.switchTab(this.currentTab);
    
    // Load envelopes data and populate metrics
    await this.loadEnvelopesList();

    // If user specifically requested studio tab directly, load default template
    if (this.currentTab === 'studio' && !this.currentDocument) {
      await this.loadSample('nda');
    }
  }

  async checkAuthentication() {
    if (!this.token) {
      window.location.replace('/login');
      return false;
    }

    try {
      const res = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) {
        throw new Error("Session invalid");
      }
      this.currentUser = await res.json();
      this.updateUserHeader();
      return true;
    } catch (e) {
      localStorage.removeItem('docusign_token');
      localStorage.removeItem('docusign_user');
      window.location.replace('/login');
      return false;
    }
  }

  updateUserHeader() {
    if (!this.currentUser) return;
    const name = this.currentUser.name || 'Verified User';
    const email = this.currentUser.email || '';
    const role = this.currentUser.role || 'Account Owner';
    const initial = name.charAt(0).toUpperCase();

    // Top Navigation Profile
    const nameEl = document.getElementById('user-name-display');
    const emailEl = document.getElementById('user-email-display');
    const avatarEl = document.getElementById('user-avatar');
    if (nameEl) nameEl.innerText = name;
    if (emailEl) emailEl.innerText = email;
    if (avatarEl) avatarEl.innerText = initial;

    // Dashboard Hero & Greeting
    const dashNameEl = document.getElementById('dash-user-name');
    const dashEmailEl = document.getElementById('dash-user-email');
    const dashRoleEl = document.getElementById('dash-user-role');
    const dashAvatarEl = document.getElementById('dash-avatar');
    const greetingHeading = document.getElementById('dash-greeting-heading');
    const footerLegalName = document.getElementById('legal-footer-name');
    const dateEl = document.getElementById('dash-current-date');

    const now = new Date();
    const hours = now.getHours();
    let timeGreeting = "Welcome to Your Dashboard";
    if (hours < 12) timeGreeting = "Good Morning";
    else if (hours < 18) timeGreeting = "Good Afternoon";
    else timeGreeting = "Good Evening";

    if (dashNameEl) dashNameEl.innerText = name;
    if (dashEmailEl) dashEmailEl.innerText = email;
    if (dashRoleEl) dashRoleEl.innerText = role;
    if (dashAvatarEl) dashAvatarEl.innerText = initial;
    if (greetingHeading) {
      greetingHeading.innerHTML = `${timeGreeting}, <span class="text-blue-400 font-extrabold">${name}</span>`;
    }
    if (footerLegalName) footerLegalName.innerText = `${name} (${email})`;
    if (dateEl) {
      dateEl.innerText = now.toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric', year: 'numeric' });
    }

    // KYC Document badge display
    const topKycBadge = document.getElementById('top-kyc-badge');
    const dashKycPill = document.getElementById('dash-kyc-pill');
    const docType = (this.currentUser.kyc_doc_type || 'aadhaar').toUpperCase();
    const docId = this.currentUser.kyc_doc_id || 'UIDAI Verified';

    let kycLabel = `🛡️ Aadhaar (${docId}) Verified`;
    if (docType.includes('PAN')) kycLabel = `🛡️ PAN (${docId}) Verified`;
    else if (docType.includes('EMAIL')) kycLabel = `🛡️ Email (${email}) Verified`;

    if (topKycBadge) topKycBadge.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ${kycLabel}`;
    if (dashKycPill) dashKycPill.innerHTML = `<span class="w-1.5 h-1.5 rounded-full bg-emerald-400"></span> ${kycLabel}`;

    // Signature Tier / Premium badge display
    const isPremium = this.currentUser.is_premium || (this.currentUser.premium_credits > 0);
    const topPremiumBadge = document.getElementById('top-premium-badge');
    const dashTierPill = document.getElementById('dash-tier-pill');
    const capEl = document.getElementById('dash-signature-capability');
    const upgradeBtn = document.getElementById('dash-btn-upgrade-license');

    if (isPremium) {
      if (topPremiumBadge) topPremiumBadge.innerHTML = `<span class="text-[9px] bg-amber-500/20 text-amber-300 border border-amber-500/30 px-1.5 py-0.2 rounded font-bold">⭐ Premium VIP</span>`;
      if (dashTierPill) {
        dashTierPill.className = "inline-flex items-center gap-1 text-[10px] font-bold bg-amber-500/10 text-amber-300 border border-amber-500/30 px-2.5 py-0.5 rounded-full";
        dashTierPill.innerHTML = `⭐ Premium Member (Draw & Upload Unlocked)`;
      }
      if (capEl) {
        capEl.innerHTML = `<span class="text-emerald-400 font-semibold">✓ Custom Draw & Upload Unlocked</span> &bull; <span class="text-slate-400">Unlimited Legal Execution</span>`;
      }
      if (upgradeBtn) {
        upgradeBtn.innerHTML = `<span>⭐ Premium Active</span>`;
        upgradeBtn.className = "px-4 py-2.5 bg-slate-900 border border-amber-500/40 text-amber-300 font-bold text-xs rounded-xl flex items-center gap-1.5 cursor-default";
      }
    } else {
      if (topPremiumBadge) topPremiumBadge.innerHTML = `<button onclick="window.openSignaturePaymentModal()" class="text-[9px] bg-amber-500/20 text-amber-300 hover:bg-amber-500 hover:text-black border border-amber-500/30 px-1.5 py-0.2 rounded font-bold transition-all">⚡ Upgrade (₹50)</button>`;
      if (dashTierPill) {
        dashTierPill.className = "inline-flex items-center gap-1 text-[10px] font-bold bg-blue-500/10 text-blue-300 border border-blue-500/30 px-2.5 py-0.5 rounded-full";
        dashTierPill.innerHTML = `Standard Plan (Type Free)`;
      }
      if (capEl) {
        capEl.innerHTML = `<span class="text-blue-400 font-semibold">Type: Free for All</span> &bull; <span class="text-amber-400">Draw/Upload: ₹50 / signature</span>`;
      }
      if (upgradeBtn) {
        upgradeBtn.innerHTML = `<span>⚡ Unlock Draw/Upload (₹50)</span>`;
      }
    }

    // Pre-populate signer 1 if matching
    if (email === 'alice@corp.com' || email === 'sowmay@example.com') {
      this.signers[0].name = name;
      this.signers[0].email = email;
    }
  }

  initPdfViewer() {
    this.pdfViewer = new DocuPDFViewer('pdf-container', {
      onPageRendered: () => {
        if (this.fieldBuilder) {
          this.fieldBuilder.renderAllFields();
        }
      },
      onZoomChange: (scale) => {
        const zoomText = document.getElementById('zoom-level-text');
        if (zoomText) zoomText.innerText = `${Math.round(scale * 100)}%`;
      }
    });
  }

  initFieldBuilder() {
    this.fieldBuilder = new FieldBuilder({
      mode: 'self-sign',
      currentSignerId: 'self',
      currentUser: this.currentUser,
      activeSigners: this.signers,
      onFieldChange: () => {
        this.updateFieldCounts();
      }
    });
  }

  bindEvents() {
    // Navigation Tabs
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = e.currentTarget.dataset.tab;
        this.switchTab(tab);
      });
    });

    // Back to Dashboard button in Studio
    document.getElementById('btn-back-to-dashboard')?.addEventListener('click', () => {
      this.switchTab('dashboard');
    });

    // Dashboard Quick Action: Self-Sign
    document.getElementById('dash-btn-quick-self-sign')?.addEventListener('click', async () => {
      this.setWorkflowMode('self-sign');
      this.switchTab('studio');
      if (!this.currentDocument) {
        await this.loadSample('nda');
      }
    });

    // Dashboard Quick Action: Multi-Party
    document.getElementById('dash-btn-quick-multi-party')?.addEventListener('click', async () => {
      this.setWorkflowMode('multi-party');
      this.switchTab('studio');
      if (!this.currentDocument) {
        await this.loadSample('nda');
      }
    });

    // Template Launchpad Buttons
    document.querySelectorAll('.template-launch-btn').forEach(btn => {
      btn.addEventListener('click', async (e) => {
        const sampleId = e.currentTarget.dataset.sample;
        const mode = e.currentTarget.dataset.mode || 'self-sign';
        this.setWorkflowMode(mode);
        this.switchTab('studio');
        await this.loadSample(sampleId);
      });
    });

    // File Uploads (Top Bar & Dashboard Hero)
    const handleFile = (file) => {
      if (file) {
        this.handleFileUpload(file);
        this.switchTab('studio');
      }
    };

    document.getElementById('pdf-file-upload-top')?.addEventListener('change', (e) => handleFile(e.target.files[0]));
    document.getElementById('pdf-file-upload-dash')?.addEventListener('change', (e) => handleFile(e.target.files[0]));

    // Search and Status Filters
    const searchInput = document.getElementById('envelope-search-input');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value.toLowerCase().trim();
        this.renderEnvelopesTable();
      });
    }

    document.querySelectorAll('.filter-status-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        this.statusFilter = e.currentTarget.dataset.filter;
        document.querySelectorAll('.filter-status-btn').forEach(b => {
          if (b.dataset.filter === this.statusFilter) {
            b.className = "filter-status-btn px-2.5 py-1 rounded-lg font-bold bg-blue-600 text-white";
          } else {
            b.className = "filter-status-btn px-2.5 py-1 rounded-lg font-semibold text-slate-400 hover:text-slate-200";
          }
        });
        this.renderEnvelopesTable();
      });
    });

    // Workflow mode switcher in Studio
    const modeToggle = document.getElementById('workflow-mode-select');
    if (modeToggle) {
      modeToggle.addEventListener('change', (e) => {
        this.setWorkflowMode(e.target.value);
      });
    }

    // Zoom buttons in Studio
    document.getElementById('btn-zoom-in')?.addEventListener('click', () => this.pdfViewer.zoomIn());
    document.getElementById('btn-zoom-out')?.addEventListener('click', () => this.pdfViewer.zoomOut());
    document.getElementById('btn-fit-width')?.addEventListener('click', () => this.pdfViewer.fitWidth());

    // Field toolbox buttons
    document.querySelectorAll('.field-tool-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const type = e.currentTarget.dataset.type;
        this.fieldBuilder.addField(
          type,
          1,
          0.25 + Math.random() * 0.2,
          0.3 + Math.random() * 0.3,
          this.workflowMode === 'multi-party' ? this.selectedSignerId : 'self'
        );
      });
    });

    // Signer selector in Studio toolbar
    const signerSelect = document.getElementById('active-signer-select');
    if (signerSelect) {
      signerSelect.addEventListener('change', (e) => {
        this.selectedSignerId = e.target.value;
        this.fieldBuilder.currentSignerId = this.selectedSignerId;
      });
    }

    // Add new signer in multi-party mode
    document.getElementById('btn-add-signer')?.addEventListener('click', () => {
      this.addNewSigner();
    });

    // Seal Document button (Self Sign)
    document.getElementById('btn-seal-download')?.addEventListener('click', () => {
      this.executeSelfSign();
    });

    // Send Envelope button (Multi party)
    document.getElementById('btn-send-envelope')?.addEventListener('click', () => {
      this.createMultiPartyEnvelope();
    });

    // Refresh envelopes
    document.getElementById('btn-refresh-envelopes')?.addEventListener('click', () => {
      this.loadEnvelopesList();
    });

    // Logout / Switch User
    document.getElementById('btn-logout')?.addEventListener('click', async () => {
      try {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${this.token}` }
        });
      } catch (e) {}
      localStorage.removeItem('docusign_token');
      localStorage.removeItem('docusign_user');
      window.location.replace('/login');
    });

    // Privacy & Security Terms Modal
    const termsModal = document.getElementById('privacyTermsModal');
    document.getElementById('btn-terms-modal-open')?.addEventListener('click', () => {
      termsModal?.classList.remove('hidden');
      termsModal?.classList.add('flex');
    });
    document.getElementById('btn-close-terms-modal')?.addEventListener('click', () => {
      termsModal?.classList.add('hidden');
      termsModal?.classList.remove('flex');
    });
    document.getElementById('btn-ack-terms')?.addEventListener('click', () => {
      termsModal?.classList.add('hidden');
      termsModal?.classList.remove('flex');
    });

    // Modal "Go to Dashboard" button listeners
    document.getElementById('btn-modal-go-dashboard')?.addEventListener('click', () => {
      document.getElementById('sealedSuccessModal')?.classList.add('hidden');
      document.getElementById('sealedSuccessModal')?.classList.remove('flex');
      this.switchTab('dashboard');
    });

    document.getElementById('btn-env-modal-dashboard')?.addEventListener('click', () => {
      document.getElementById('envelopeLinksModal')?.classList.add('hidden');
      document.getElementById('envelopeLinksModal')?.classList.remove('flex');
      this.switchTab('dashboard');
    });

    this.bindPaymentEvents();
  }

  bindPaymentEvents() {
    window.openSignaturePaymentModal = () => {
      const modal = document.getElementById('signaturePaymentModal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }
    };

    document.getElementById('btn-close-payment-modal')?.addEventListener('click', () => {
      const modal = document.getElementById('signaturePaymentModal');
      if (modal) {
        modal.classList.add('hidden');
        modal.classList.remove('flex');
      }
    });

    document.getElementById('dash-btn-upgrade-license')?.addEventListener('click', () => {
      window.openSignaturePaymentModal();
    });

    // Payment method tabs switching (UPI, Card, NetBanking)
    document.querySelectorAll('.pay-method-tab').forEach(tab => {
      tab.addEventListener('click', (e) => {
        const method = e.currentTarget.dataset.method;
        document.querySelectorAll('.pay-method-tab').forEach(t => {
          t.className = "pay-method-tab p-2.5 rounded-xl border border-slate-800 bg-slate-950 text-slate-400 font-medium hover:text-slate-200 text-center";
        });
        e.currentTarget.className = "pay-method-tab p-2.5 rounded-xl border border-blue-500 bg-blue-500/20 text-blue-300 font-bold text-center";

        ['upi', 'card', 'netbanking'].forEach(m => {
          const pane = document.getElementById(`pay-pane-${m}`);
          if (pane) {
            if (m === method) pane.classList.remove('hidden');
            else pane.classList.add('hidden');
          }
        });
      });
    });

    // Quick UPI options
    document.querySelectorAll('.quick-upi-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const input = document.getElementById('upi-id-input');
        if (input) input.value = e.currentTarget.innerText.includes('GPay') ? 'user@okhdfcbank' : 'user@paytm';
      });
    });

    // Confirm Payment of ₹50
    document.getElementById('btn-confirm-sig-payment')?.addEventListener('click', async () => {
      const btn = document.getElementById('btn-confirm-sig-payment');
      btn.disabled = true;
      btn.innerHTML = `<span>Processing ₹50 Payment...</span>`;

      try {
        const res = await fetch('/api/payments/pay-signature', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({
            amount: 50,
            currency: 'INR',
            payment_method: 'upi',
            upi_id: document.getElementById('upi-id-input')?.value || 'user@upi'
          })
        });

        if (!res.ok) throw new Error((await res.json()).detail || "Payment failed");
        const data = await res.json();

        // Update local user state
        this.currentUser.is_premium = true;
        this.currentUser.premium_credits = (this.currentUser.premium_credits || 0) + 1;
        localStorage.setItem('docusign_user', JSON.stringify(this.currentUser));

        // Update Header & Dashboard Badges
        this.updateUserHeader();

        // Update Signature Pad overlays
        if (window.signatureManager) {
          window.signatureManager.updatePremiumBadges();
        }

        // Close payment modal
        const modal = document.getElementById('signaturePaymentModal');
        if (modal) {
          modal.classList.add('hidden');
          modal.classList.remove('flex');
        }

        alert("🎉 Payment of ₹50 Successful! Hand-Drawn and Custom Image Upload signatures are now unlocked for your session.");
      } catch (err) {
        alert("Payment Notice: " + err.message);
      } finally {
        btn.disabled = false;
        btn.innerHTML = `<span>Pay ₹50 Securely</span>`;
      }
    });
  }

  switchTab(tab) {
    this.currentTab = tab;
    
    // Update navigation tab button styles
    document.querySelectorAll('.nav-tab-btn').forEach(btn => {
      if (btn.dataset.tab === tab) {
        btn.classList.add('border-blue-500', 'text-blue-400', 'bg-blue-500/10');
        btn.classList.remove('border-transparent', 'text-slate-400');
      } else {
        btn.classList.remove('border-blue-500', 'text-blue-400', 'bg-blue-500/10');
        btn.classList.add('border-transparent', 'text-slate-400');
      }
    });

    const studioView = document.getElementById('view-studio');
    const dashboardView = document.getElementById('view-dashboard');

    if (tab === 'studio') {
      dashboardView?.classList.add('hidden');
      studioView?.classList.remove('hidden');
      // If no document is currently loaded in studio, load default sample
      if (!this.currentDocument) {
        this.loadSample('nda');
      }
    } else {
      studioView?.classList.add('hidden');
      dashboardView?.classList.remove('hidden');
      this.loadEnvelopesList();
    }

    // Keep URL parameter synchronized
    try {
      const url = new URL(window.location);
      url.searchParams.set('tab', tab);
      window.history.replaceState({}, '', url);
    } catch (e) {}
  }

  setWorkflowMode(mode) {
    this.workflowMode = mode;
    const modeSelect = document.getElementById('workflow-mode-select');
    if (modeSelect) modeSelect.value = mode;

    const multiPartyPanel = document.getElementById('multiparty-signers-panel');
    const sealBtn = document.getElementById('btn-seal-download');
    const sendBtn = document.getElementById('btn-send-envelope');

    if (mode === 'multi-party') {
      multiPartyPanel?.classList.remove('hidden');
      sealBtn?.classList.add('hidden');
      sendBtn?.classList.remove('hidden');

      this.selectedSignerId = this.signers[0].id;
      this.fieldBuilder.setMode('envelope-builder', this.selectedSignerId, this.signers, this.currentUser);
      this.renderSignersList();
    } else {
      multiPartyPanel?.classList.add('hidden');
      sealBtn?.classList.remove('hidden');
      sendBtn?.classList.add('hidden');

      this.selectedSignerId = 'self';
      this.fieldBuilder.setMode('self-sign', 'self', [], this.currentUser);
    }
  }

  renderSignersList() {
    const listEl = document.getElementById('signers-list-container');
    const selectEl = document.getElementById('active-signer-select');
    if (!listEl || !selectEl) return;

    listEl.innerHTML = this.signers.map(s => `
      <div class="p-3 bg-slate-900 border border-slate-800 rounded-xl mb-2 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-3 h-3 rounded-full shrink-0" style="background-color: ${s.color}"></span>
          <div class="overflow-hidden">
            <p class="text-xs font-semibold text-slate-200 truncate">${s.name}</p>
            <p class="text-[10px] text-slate-400 font-mono truncate">${s.email}</p>
          </div>
        </div>
        <span class="text-[10px] px-2 py-0.5 rounded-full bg-slate-800 font-medium text-slate-400 shrink-0">${s.role}</span>
      </div>
    `).join('');

    selectEl.innerHTML = this.signers.map(s => `
      <option value="${s.id}">${s.name} (${s.role})</option>
    `).join('');
    selectEl.value = this.selectedSignerId;
  }

  addNewSigner() {
    const name = prompt("Enter Signer Full Legal Name:", "Jane Doe");
    if (!name) return;
    const email = prompt("Enter Signer Email Address:", "jane.doe@example.com");
    if (!email) return;

    const colors = ["#2563eb", "#059669", "#7c3aed", "#d97706", "#dc2626", "#0891b2"];
    const newSigner = {
      id: 'signer_' + (this.signers.length + 1),
      name: name.trim(),
      email: email.trim().toLowerCase(),
      role: `Signer ${this.signers.length + 1}`,
      color: colors[this.signers.length % colors.length]
    };
    this.signers.push(newSigner);
    this.selectedSignerId = newSigner.id;
    this.renderSignersList();
    this.fieldBuilder.activeSigners = this.signers;
    this.fieldBuilder.currentSignerId = this.selectedSignerId;
  }

  async handleFileUpload(file) {
    if (!file) return;
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await fetch('/api/documents/upload', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` },
        body: formData
      });
      if (!res.ok) throw new Error((await res.json()).detail || "Upload failed");
      const data = await res.json();
      this.currentDocument = data;
      this.updateDocHeader(data.filename, data.page_count);
      await this.pdfViewer.loadDocument(`/api/documents/${data.document_id}/pdf`);
      this.fieldBuilder.setFields([]);
    } catch (e) {
      alert("Error uploading document: " + e.message);
    }
  }

  async loadSample(sampleId) {
    try {
      const res = await fetch(`/api/documents/samples/${sampleId}/load`, {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) throw new Error("Failed to load sample template");
      const data = await res.json();
      this.currentDocument = data;
      this.updateDocHeader(data.filename, data.page_count);
      await this.pdfViewer.loadDocument(`/api/documents/${data.document_id}/pdf`);
      this.fieldBuilder.setFields([]);
    } catch (e) {
      console.error(e);
    }
  }

  updateDocHeader(title, pageCount) {
    const titleEl = document.getElementById('current-doc-title');
    const pageEl = document.getElementById('current-doc-pages');
    if (titleEl) titleEl.innerText = title;
    if (pageEl) pageEl.innerText = `${pageCount || 1} Page(s)`;
  }

  updateFieldCounts() {
    const fields = this.fieldBuilder.getFields();
    const countEl = document.getElementById('field-count-badge');
    if (countEl) countEl.innerText = `${fields.length} Field(s) Placed`;
  }

  async executeSelfSign() {
    if (!this.currentDocument) {
      alert("Please upload or select a document first.");
      return;
    }

    const fields = this.fieldBuilder.getFields();
    if (fields.length === 0) {
      alert("Please place at least one signature or annotation field before sealing.");
      return;
    }

    const btn = document.getElementById('btn-seal-download');
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin inline-block mr-2">🌀</span> Sealing Document...`;

    try {
      const res = await fetch('/api/signatures/self-sign', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          document_id: this.currentDocument.document_id,
          title: this.currentDocument.filename.replace('.pdf', ''),
          signer_name: this.currentUser ? this.currentUser.name : "Verified Signer",
          signer_email: this.currentUser ? this.currentUser.email : "signer@local",
          fields: fields
        })
      });

      if (!res.ok) throw new Error((await res.json()).detail || "Failed to seal document");
      const result = await res.json();

      this.showSealedSuccessModal(result);
      await this.loadEnvelopesList();
    } catch (e) {
      alert("Security/Execution Notice: " + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>🔒 Seal & Download PDF</span>`;
    }
  }

  async createMultiPartyEnvelope() {
    if (!this.currentDocument) {
      alert("Please upload or select a document first.");
      return;
    }

    const fields = this.fieldBuilder.getFields();
    if (fields.length === 0) {
      alert("Please place signature fields for your recipients before sending.");
      return;
    }

    const btn = document.getElementById('btn-send-envelope');
    btn.disabled = true;
    btn.innerHTML = `<span class="animate-spin inline-block mr-2">🌀</span> Creating Envelope...`;

    try {
      const res = await fetch('/api/envelopes/create', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${this.token}`
        },
        body: JSON.stringify({
          document_id: this.currentDocument.document_id,
          title: this.currentDocument.filename.replace('.pdf', ''),
          signers: this.signers,
          fields: fields
        })
      });

      if (!res.ok) throw new Error((await res.json()).detail || "Failed to create envelope");
      const result = await res.json();

      this.showEnvelopeCreatedModal(result);
      await this.loadEnvelopesList();
    } catch (e) {
      alert("Error creating envelope: " + e.message);
    } finally {
      btn.disabled = false;
      btn.innerHTML = `<span>🚀 Send Envelope</span>`;
    }
  }

  showSealedSuccessModal(data) {
    const modal = document.getElementById('sealedSuccessModal');
    if (!modal) return;

    const shaEl = document.getElementById('sealed-sha256-display');
    if (shaEl) shaEl.innerText = data.sha256;
    
    const dlBtn = document.getElementById('btn-modal-download');
    if (dlBtn) dlBtn.href = data.download_url;

    modal.classList.remove('hidden');
    modal.classList.add('flex');

    document.getElementById('btn-close-sealed-modal')?.addEventListener('click', () => {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    });
  }

  showEnvelopeCreatedModal(data) {
    const modal = document.getElementById('envelopeLinksModal');
    if (!modal) return;

    const linksContainer = document.getElementById('envelope-links-list');
    if (linksContainer) {
      linksContainer.innerHTML = data.signing_links.map(l => `
        <div class="p-3.5 bg-slate-50 border border-slate-200 rounded-xl">
          <div class="flex items-center justify-between mb-2">
            <div class="flex items-center gap-2">
              <span class="w-3 h-3 rounded-full" style="background-color: ${l.color}"></span>
              <span class="font-bold text-slate-800 text-xs">${l.name} (${l.role})</span>
            </div>
            <span class="text-[11px] text-slate-500 font-mono">${l.email}</span>
          </div>
          <div class="flex items-center gap-2">
            <input type="text" readonly value="${l.signing_url}" class="flex-1 bg-white border border-slate-200 text-xs px-3 py-1.5 rounded-lg text-slate-600 font-mono focus:outline-none" />
            <button class="px-3 py-1.5 bg-blue-600 hover:bg-blue-700 text-white text-xs font-bold rounded-lg copy-link-btn" data-url="${l.signing_url}">
              Copy
            </button>
            <a href="${l.signing_url}" target="_blank" class="px-3 py-1.5 bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold rounded-lg">
              Open
            </a>
          </div>
        </div>
      `).join('');

      linksContainer.querySelectorAll('.copy-link-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
          navigator.clipboard.writeText(e.currentTarget.dataset.url);
          e.currentTarget.innerText = "Copied!";
          setTimeout(() => e.currentTarget.innerText = "Copy", 1500);
        });
      });
    }

    modal.classList.remove('hidden');
    modal.classList.add('flex');

    document.getElementById('btn-close-envelope-modal')?.addEventListener('click', () => {
      modal.classList.add('hidden');
      modal.classList.remove('flex');
    });
  }

  async loadEnvelopesList() {
    try {
      const res = await fetch('/api/envelopes', {
        headers: { 'Authorization': `Bearer ${this.token}` }
      });
      if (!res.ok) return;
      this.allEnvelopes = await res.json();

      // Update Analytics & KPI stats
      this.updateDashboardMetrics();

      // Render table
      this.renderEnvelopesTable();
    } catch (e) {
      console.error("Failed to load envelopes:", e);
    }
  }

  updateDashboardMetrics() {
    const total = this.allEnvelopes.length;
    const completed = this.allEnvelopes.filter(e => e.status === 'completed').length;
    const pending = total - completed;

    const totalEl = document.getElementById('stat-total-docs');
    const pendingEl = document.getElementById('stat-pending-docs');
    const completedEl = document.getElementById('stat-completed-docs');

    if (totalEl) totalEl.innerText = total;
    if (pendingEl) pendingEl.innerText = pending;
    if (completedEl) completedEl.innerText = completed;
  }

  renderEnvelopesTable() {
    const container = document.getElementById('envelopes-table-body');
    if (!container) return;

    let filtered = this.allEnvelopes;

    // Filter by status tab
    if (this.statusFilter === 'completed') {
      filtered = filtered.filter(e => e.status === 'completed');
    } else if (this.statusFilter === 'waiting') {
      filtered = filtered.filter(e => e.status !== 'completed');
    }

    // Filter by search query
    if (this.searchQuery) {
      filtered = filtered.filter(e => {
        const titleMatch = (e.title || '').toLowerCase().includes(this.searchQuery);
        const idMatch = (e.id || '').toLowerCase().includes(this.searchQuery);
        const signersMatch = (e.signers || []).some(s => 
          (s.name || '').toLowerCase().includes(this.searchQuery) ||
          (s.email || '').toLowerCase().includes(this.searchQuery)
        );
        return titleMatch || idMatch || signersMatch;
      });
    }

    if (filtered.length === 0) {
      container.innerHTML = `
        <tr>
          <td colspan="5" class="py-12 text-center text-slate-400">
            <div class="w-12 h-12 rounded-2xl bg-slate-900 border border-slate-800 flex items-center justify-center mx-auto mb-3 text-2xl">
              📂
            </div>
            <p class="text-sm font-bold text-slate-300">No documents found</p>
            <p class="text-xs text-slate-500 mt-1">Upload a PDF or launch one of the standard templates above.</p>
          </td>
        </tr>
      `;
      return;
    }

    container.innerHTML = filtered.map(env => {
      const isCompleted = env.status === 'completed';
      
      // Status badge styling
      let statusBadge = '';
      if (isCompleted) {
        statusBadge = `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
          <span class="w-2 h-2 rounded-full bg-emerald-400"></span> SEALED
        </span>`;
      } else if (env.status === 'waiting') {
        statusBadge = `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
          <span class="w-2 h-2 rounded-full bg-amber-400 animate-pulse"></span> WAITING
        </span>`;
      } else {
        statusBadge = `<span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
          <span class="w-2 h-2 rounded-full bg-blue-400"></span> IN PROGRESS
        </span>`;
      }

      // Signer tags
      const signersHtml = (env.signers || []).map(s => {
        const isSigned = s.status === 'SIGNED';
        return `
          <span class="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded-full border ${isSigned ? 'bg-emerald-500/10 text-emerald-300 border-emerald-500/30' : 'bg-slate-900 text-slate-400 border-slate-800'}">
            <span class="w-1.5 h-1.5 rounded-full" style="background-color: ${s.color || '#2563eb'}"></span>
            <span>${isSigned ? '✓' : '⏳'}</span>
            <span class="font-medium">${s.name}</span>
          </span>
        `;
      }).join(' ');

      const formattedDate = new Date(env.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric'
      });

      return `
        <tr class="hover:bg-slate-900/40 transition-colors">
          <td class="py-4 px-6">
            <div class="flex items-center gap-3">
              <span class="w-9 h-9 rounded-xl bg-slate-900 border border-slate-800 flex items-center justify-center text-base shrink-0">
                ${isCompleted ? '📜' : '📝'}
              </span>
              <div>
                <p class="font-bold text-sm text-slate-100">${env.title || env.original_filename}</p>
                <p class="text-[10px] text-slate-500 font-mono mt-0.5">ID: ${env.id.substring(0, 16)}...</p>
              </div>
            </div>
          </td>
          <td class="py-4 px-4 whitespace-nowrap">
            ${statusBadge}
          </td>
          <td class="py-4 px-4">
            <div class="flex flex-wrap gap-1.5 max-w-xs">
              ${signersHtml || '<span class="text-xs text-slate-500">Self Signed</span>'}
            </div>
          </td>
          <td class="py-4 px-4 text-xs text-slate-400 whitespace-nowrap">
            ${formattedDate}
          </td>
          <td class="py-4 px-6 text-right whitespace-nowrap">
            <div class="inline-flex items-center gap-2">
              <a href="/api/envelopes/${env.id}/download" target="_blank" class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-xl shadow transition-all ${isCompleted ? 'bg-blue-600 hover:bg-blue-500 text-white' : 'bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700'}">
                <span>${isCompleted ? '📥 Download' : '📄 Draft'}</span>
              </a>
            </div>
          </td>
        </tr>
      `;
    }).join('');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.docuSignApp = new DocuSignApp();
});
