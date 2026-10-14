/**
 * Signer Experience Workflow (/sign/{token})
 * Guided signing ceremony, field navigation, electronic disclosure, and submission.
 * STRICT PRIVACY & SECURITY: Verifies that only the designated signer can execute their fields.
 */
document.addEventListener('DOMContentLoaded', async () => {
  const pathParts = window.location.pathname.split('/');
  const token = pathParts[pathParts.length - 1] || pathParts[pathParts.length - 2];
  const userToken = localStorage.getItem('docusign_token') || '';

  if (!token || token === 'sign' || token === 'sign.html') {
    document.getElementById('loading-overlay').innerHTML = `
      <div class="p-8 text-center text-red-600 bg-white rounded-2xl shadow-xl max-w-md">
        <p class="text-xl font-bold mb-2">Invalid Signing Link</p>
        <p class="text-sm text-slate-500">No active signing token found in the URL.</p>
      </div>
    `;
    return;
  }

  let sessionData = null;
  let pdfViewer = null;
  let fieldBuilder = null;

  try {
    const res = await fetch(`/api/signing/${token}`, {
      headers: userToken ? { 'Authorization': `Bearer ${userToken}` } : {}
    });
    if (!res.ok) {
      throw new Error((await res.json()).detail || "Unable to load signing session");
    }
    sessionData = await res.json();
  } catch (err) {
    document.getElementById('loading-overlay').innerHTML = `
      <div class="p-8 text-center text-red-600 bg-white rounded-2xl shadow-xl max-w-md">
        <p class="text-xl font-bold mb-2">Signing Link Expired or Invalid</p>
        <p class="text-sm text-slate-500">${err.message}</p>
      </div>
    `;
    return;
  }

  const signer = sessionData.current_signer;
  document.getElementById('signer-name-display').innerText = signer.name;
  document.getElementById('signer-email-display').innerText = signer.email;
  document.getElementById('doc-title-display').innerText = sessionData.title;

  // Check Identity Mismatch Security Rule
  let isMismatch = false;
  if (!sessionData.identity_verified && sessionData.identity_mismatch) {
    isMismatch = true;
    const mm = sessionData.identity_mismatch;
    const banner = document.getElementById('identity-mismatch-banner');
    const textEl = document.getElementById('identity-mismatch-text');
    if (banner && textEl) {
      textEl.innerHTML = `You are authenticated as <b>${mm.logged_in_name}</b> (${mm.logged_in_email}), but this envelope is exclusively for <b>${mm.expected_name}</b> (${mm.expected_email}). Under Privacy and Security terms, you are restricted from signing on behalf of another party.`;
      banner.classList.remove('hidden');
    }
  }

  // Initialize PDF viewer
  pdfViewer = new DocuPDFViewer('pdf-container', {
    onPageRendered: () => {
      if (fieldBuilder) {
        fieldBuilder.renderAllFields();
        if (!isMismatch) updateSignerFlags();
      }
    }
  });

  // Initialize Field Builder locked to the designated signer
  fieldBuilder = new FieldBuilder({
    mode: 'signer',
    currentSignerId: signer.id,
    currentUser: { name: signer.name, email: signer.email },
    activeSigners: sessionData.all_signers,
    onFieldChange: () => {
      if (!isMismatch) {
        updateSignerFlags();
        checkCompletionState();
      }
    }
  });

  fieldBuilder.setFields(sessionData.fields);
  await pdfViewer.loadDocument(sessionData.document_pdf_url);

  // Hide loading screen
  document.getElementById('loading-overlay').classList.add('hidden');

  // Zoom controls
  document.getElementById('btn-zoom-in').addEventListener('click', () => pdfViewer.zoomIn());
  document.getElementById('btn-zoom-out').addEventListener('click', () => pdfViewer.zoomOut());
  document.getElementById('btn-fit-width').addEventListener('click', () => pdfViewer.fitWidth());

  function updateSignerFlags() {
    document.querySelectorAll('.sign-flag-indicator').forEach(el => el.remove());
    if (isMismatch) return;

    const myFields = fieldBuilder.getFields().filter(f => f.assigned_to === signer.id && !f.value);
    
    myFields.forEach((f, idx) => {
      const fieldEl = document.getElementById(`field-${f.id}`);
      if (fieldEl) {
        const flag = document.createElement('div');
        flag.className = 'sign-flag-indicator';
        flag.innerHTML = `<span>✍️ SIGN</span>`;
        fieldEl.appendChild(flag);
      }
    });

    const pendingCount = myFields.length;
    const progressText = document.getElementById('pending-fields-count');
    if (progressText) {
      progressText.innerText = pendingCount === 0 ? "All fields filled!" : `${pendingCount} required field(s) left`;
    }
  }

  function checkCompletionState() {
    if (isMismatch) return;
    const myFields = fieldBuilder.getFields().filter(f => f.assigned_to === signer.id && f.required);
    const allFilled = myFields.length > 0 && myFields.every(f => f.value && f.value.trim() !== "");
    const consentChecked = document.getElementById('legal-consent-checkbox')?.checked;

    const finishBtn = document.getElementById('btn-finish-signing');
    if (finishBtn) {
      if (allFilled && consentChecked) {
        finishBtn.disabled = false;
        finishBtn.className = "px-6 py-2.5 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white font-bold rounded-xl shadow-lg shadow-emerald-500/30 transition-all flex items-center gap-2 animate-pulse";
      } else {
        finishBtn.disabled = true;
        finishBtn.className = "px-6 py-2.5 bg-slate-800 text-slate-500 font-semibold rounded-xl cursor-not-allowed transition-all flex items-center gap-2";
      }
    }
  }

  document.getElementById('btn-next-field')?.addEventListener('click', () => {
    if (isMismatch) {
      alert("Signing disabled: You are logged in under a different identity than the designated recipient.");
      return;
    }
    const myFields = fieldBuilder.getFields().filter(f => f.assigned_to === signer.id && !f.value);
    if (myFields.length > 0) {
      const nextField = myFields[0];
      const el = document.getElementById(`field-${nextField.id}`);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
        el.classList.add('ring-4', 'ring-amber-400');
        setTimeout(() => el.classList.remove('ring-4', 'ring-amber-400'), 1500);
      }
    } else {
      alert("All fields are filled! Accept the legal consent disclosure and click Finish Signing.");
    }
  });

  document.getElementById('legal-consent-checkbox')?.addEventListener('change', checkCompletionState);

  // Submit Signing
  document.getElementById('btn-finish-signing')?.addEventListener('click', async () => {
    if (isMismatch) {
      alert("Security Violation: You are not authorized to sign this document.");
      return;
    }

    const btn = document.getElementById('btn-finish-signing');
    btn.disabled = true;
    btn.innerText = "Submitting & Sealing...";

    try {
      const res = await fetch(`/api/signing/${token}/submit`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(userToken ? { 'Authorization': `Bearer ${userToken}` } : {})
        },
        body: JSON.stringify({
          token: token,
          signer_name: signer.name,
          fields: fieldBuilder.getFields()
        })
      });

      if (!res.ok) {
        throw new Error((await res.json()).detail || "Failed to submit signature.");
      }

      const result = await res.json();
      
      const modal = document.getElementById('completionModal');
      if (modal) {
        modal.classList.remove('hidden');
        modal.classList.add('flex');
      }

      if (result.download_url) {
        const dlBtn = document.getElementById('btn-download-completed');
        if (dlBtn) {
          dlBtn.href = result.download_url;
          dlBtn.classList.remove('hidden');
        }
      }
    } catch (e) {
      alert("Security / Submission error: " + e.message);
      btn.disabled = false;
      btn.innerText = "Finish Signing";
    }
  });

  window.signerViewApp = {
    isPremium: sessionData.is_premium || false,
    token: token
  };

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

  document.getElementById('btn-confirm-signer-payment')?.addEventListener('click', async () => {
    const btn = document.getElementById('btn-confirm-signer-payment');
    btn.disabled = true;
    btn.innerText = "Processing ₹50 Payment...";

    try {
      const res = await fetch(`/api/payments/pay-signer-token/${token}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          amount: 50,
          currency: 'INR',
          payment_method: 'upi',
          upi_id: document.getElementById('signer-upi-input')?.value || 'signer@upi'
        })
      });

      if (!res.ok) throw new Error((await res.json()).detail || "Payment failed");
      window.signerViewApp.isPremium = true;
      if (window.signatureManager) {
        window.signatureManager.updatePremiumBadges();
      }

      document.getElementById('signaturePaymentModal')?.classList.add('hidden');
      document.getElementById('signaturePaymentModal')?.classList.remove('flex');
      alert("🎉 Payment of ₹50 Successful! Custom Draw & Upload signatures are now unlocked for this document.");
    } catch (e) {
      alert("Payment error: " + e.message);
    } finally {
      btn.disabled = false;
      btn.innerText = "Pay ₹50 Securely";
    }
  });

  if (!isMismatch) {
    checkCompletionState();
    updateSignerFlags();
  }
});
