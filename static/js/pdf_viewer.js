/**
 * PDF Document Viewer using PDF.js
 * Multi-page rendering, zoom controls, and coordinate alignment for field overlays.
 */
class DocuPDFViewer {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    this.options = options;
    this.pdfDoc = null;
    this.currentScale = 1.15;
    this.totalPages = 0;
    this.pageRenderTasks = {};
    this.onPageRendered = options.onPageRendered || null;
    this.onZoomChange = options.onZoomChange || null;

    // Set worker
    if (window.pdfjsLib) {
      window.pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
    }
  }

  async loadDocument(urlOrBytes) {
    if (!window.pdfjsLib) {
      console.error("PDF.js library is not loaded.");
      return;
    }

    try {
      this.container.innerHTML = `
        <div class="flex flex-col items-center justify-center p-12 text-slate-400">
          <div class="w-8 h-8 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mb-3"></div>
          <p class="text-sm font-medium">Loading document pages...</p>
        </div>
      `;

      const loadingTask = window.pdfjsLib.getDocument(urlOrBytes);
      this.pdfDoc = await loadingTask.promise;
      this.totalPages = this.pdfDoc.numPages;
      
      this.renderAllPages();
      return this.pdfDoc;
    } catch (err) {
      console.error("Failed to load PDF:", err);
      this.container.innerHTML = `
        <div class="p-8 text-center text-red-500 bg-red-50 rounded-xl m-4 border border-red-200">
          <p class="font-semibold mb-1">Failed to load document</p>
          <p class="text-xs text-red-400">${err.message}</p>
        </div>
      `;
      throw err;
    }
  }

  async renderAllPages() {
    if (!this.pdfDoc) return;
    this.container.innerHTML = '';

    for (let pageNum = 1; pageNum <= this.totalPages; pageNum++) {
      const pageWrapper = document.createElement('div');
      pageWrapper.className = 'pdf-page-wrapper';
      pageWrapper.id = `pdf-page-${pageNum}`;
      pageWrapper.dataset.pageNumber = pageNum;

      const canvas = document.createElement('canvas');
      canvas.className = 'pdf-canvas-layer';
      canvas.id = `pdf-canvas-${pageNum}`;

      const overlay = document.createElement('div');
      overlay.className = 'pdf-overlay-layer';
      overlay.id = `pdf-overlay-${pageNum}`;
      overlay.dataset.pageNumber = pageNum;

      pageWrapper.appendChild(canvas);
      pageWrapper.appendChild(overlay);
      this.container.appendChild(pageWrapper);

      await this.renderPage(pageNum);
    }

    if (this.onPageRendered) {
      this.onPageRendered();
    }
  }

  async renderPage(pageNum) {
    const page = await this.pdfDoc.getPage(pageNum);
    const viewport = page.getViewport({ scale: this.currentScale });

    const canvas = document.getElementById(`pdf-canvas-${pageNum}`);
    const overlay = document.getElementById(`pdf-overlay-${pageNum}`);
    const wrapper = document.getElementById(`pdf-page-${pageNum}`);
    if (!canvas || !overlay || !wrapper) return;

    const ctx = canvas.getContext('2d');
    const dpr = window.devicePixelRatio || 1;

    // Set physical canvas pixel dimensions
    canvas.width = Math.floor(viewport.width * dpr);
    canvas.height = Math.floor(viewport.height * dpr);
    canvas.style.width = `${Math.floor(viewport.width)}px`;
    canvas.style.height = `${Math.floor(viewport.height)}px`;

    // Set overlay match exactly
    overlay.style.width = `${Math.floor(viewport.width)}px`;
    overlay.style.height = `${Math.floor(viewport.height)}px`;
    wrapper.style.width = `${Math.floor(viewport.width)}px`;
    wrapper.style.height = `${Math.floor(viewport.height)}px`;

    // Cancel existing render if running
    if (this.pageRenderTasks[pageNum]) {
      this.pageRenderTasks[pageNum].cancel();
    }

    const transform = dpr !== 1 ? [dpr, 0, 0, dpr, 0, 0] : null;
    const renderContext = {
      canvasContext: ctx,
      viewport: viewport,
      transform: transform
    };

    const renderTask = page.render(renderContext);
    this.pageRenderTasks[pageNum] = renderTask;

    try {
      await renderTask.promise;
    } catch (e) {
      if (e.name !== 'RenderingCancelledException') {
        console.error("Page render error:", e);
      }
    }
  }

  setZoom(scale) {
    this.currentScale = Math.max(0.5, Math.min(2.5, scale));
    if (this.onZoomChange) this.onZoomChange(this.currentScale);
    return this.renderAllPages();
  }

  zoomIn() {
    return this.setZoom(this.currentScale + 0.15);
  }

  zoomOut() {
    return this.setZoom(this.currentScale - 0.15);
  }

  fitWidth() {
    if (!this.container || !this.pdfDoc) return;
    this.pdfDoc.getPage(1).then(page => {
      const naturalViewport = page.getViewport({ scale: 1.0 });
      const availableWidth = this.container.clientWidth - 48; // padding
      if (availableWidth > 200 && naturalViewport.width > 0) {
        const fitScale = availableWidth / naturalViewport.width;
        this.setZoom(fitScale);
      }
    });
  }

  getPageDimensions(pageNum) {
    const overlay = document.getElementById(`pdf-overlay-${pageNum}`);
    if (!overlay) return null;
    return {
      width: overlay.clientWidth,
      height: overlay.clientHeight
    };
  }
}

window.DocuPDFViewer = DocuPDFViewer;
