class FeedbackWidget {
    constructor() {
        this.widget = null;
        this.modal = null;
        this.isDragging = false;
        this.dragStartX = 0;
        this.dragStartY = 0;
        this.widgetStartX = 0;
        this.widgetStartY = 0;

        this.init();
    }

    init() {
        this.createWidget();
        this.setupEventListeners();
        this.loadPosition();
    }

    createWidget() {
        // Create the widget HTML
        const widgetHTML = `
            <div class="feedback-widget" id="feedbackWidget">
                <button class="feedback-button" id="feedbackButton" title="Invia Feedback">
                    💬
                </button>
            </div>

            <div class="feedback-modal" id="feedbackModal">
                <div class="feedback-content">
                    <div class="feedback-header">
                        <h3>Invia il tuo Feedback</h3>
                        <button class="feedback-close" id="feedbackClose">&times;</button>
                    </div>
                    <div class="feedback-body">
                        <div id="feedbackMessage"></div>
                        <form class="feedback-form" id="feedbackForm">
                            <div class="form-group">
                                <label for="feedbackType">Tipo di Feedback:</label>
                                <select id="feedbackType" name="ticket_type">
                                    <option value="bug">🐛 Segnalazione Bug</option>
                                    <option value="feature">✨ Richiesta Funzionalità</option>
                                    <option value="improvement">📈 Miglioramento</option>
                                    <option value="question">❓ Domanda</option>
                                    <option value="other">📝 Altro</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="feedbackPriority">Priorità:</label>
                                <select id="feedbackPriority" name="priority">
                                    <option value="low">🟢 Bassa</option>
                                    <option value="medium" selected>🟡 Media</option>
                                    <option value="high">🟠 Alta</option>
                                    <option value="urgent">🔴 Urgente</option>
                                </select>
                            </div>
                            <div class="form-group">
                                <label for="feedbackDescription">Descrizione:</label>
                                <textarea id="feedbackDescription" name="description" placeholder="Descrivi il tuo feedback in dettaglio..." required></textarea>
                            </div>
                            <input type="hidden" id="feedbackPageUrl" name="page_url">
                            <input type="hidden" id="feedbackUserAgent" name="user_agent">
                            <input type="hidden" id="feedbackBrowserInfo" name="browser_info">
                        </form>
                    </div>
                    <div class="feedback-actions">
                        <button class="feedback-btn feedback-btn-cancel" id="feedbackCancel">Annulla</button>
                        <button class="feedback-btn feedback-btn-submit" id="feedbackSubmit">Invia Feedback</button>
                    </div>
                </div>
            </div>
        `;

        // Insert the HTML into the page
        document.body.insertAdjacentHTML('beforeend', widgetHTML);

        // Get references to the elements
        this.widget = document.getElementById('feedbackWidget');
        this.modal = document.getElementById('feedbackModal');
        this.button = document.getElementById('feedbackButton');
        this.form = document.getElementById('feedbackForm');
        this.messageDiv = document.getElementById('feedbackMessage');
    }

    setupEventListeners() {
        const button = document.getElementById('feedbackButton');
        const modal = document.getElementById('feedbackModal');
        const closeBtn = document.getElementById('feedbackClose');
        const cancelBtn = document.getElementById('feedbackCancel');
        const submitBtn = document.getElementById('feedbackSubmit');

        // Button click to open modal (only if not dragging)
        button.addEventListener('click', (e) => {
            if (!this.isDragging) {
                this.openModal();
            }
        });

        // Close modal events
        closeBtn.addEventListener('click', () => this.closeModal());
        cancelBtn.addEventListener('click', () => this.closeModal());
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                this.closeModal();
            }
        });

        // Submit form
        submitBtn.addEventListener('click', (e) => {
            e.preventDefault();
            this.submitFeedback();
        });

        // Form submission
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            this.submitFeedback();
        });

        // Drag functionality
        this.setupDragFunctionality();

        // Keyboard shortcut (Escape to close)
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && modal.classList.contains('show')) {
                this.closeModal();
            }
        });
    }

    setupDragFunctionality() {
        const button = this.button;

        // Mouse events
        button.addEventListener('mousedown', this.startDrag.bind(this));
        document.addEventListener('mousemove', this.drag.bind(this));
        document.addEventListener('mouseup', this.endDrag.bind(this));

        // Touch events for mobile
        button.addEventListener('touchstart', this.startDrag.bind(this), { passive: false });
        document.addEventListener('touchmove', this.drag.bind(this), { passive: false });
        document.addEventListener('touchend', this.endDrag.bind(this));
    }

    startDrag(e) {
        e.preventDefault();
        this.isDragging = true;
        this.button.classList.add('dragging');

        const clientX = e.clientX || (e.touches && e.touches[0].clientX);
        const clientY = e.clientY || (e.touches && e.touches[0].clientY);

        this.dragStartX = clientX;
        this.dragStartY = clientY;

        const rect = this.widget.getBoundingClientRect();
        this.widgetStartX = rect.left;
        this.widgetStartY = rect.top;

        // Prevent text selection during drag
        document.body.style.userSelect = 'none';
    }

    drag(e) {
        if (!this.isDragging) return;

        e.preventDefault();

        const clientX = e.clientX || (e.touches && e.touches[0].clientX);
        const clientY = e.clientY || (e.touches && e.touches[0].clientY);

        const deltaX = clientX - this.dragStartX;
        const deltaY = clientY - this.dragStartY;

        let newX = this.widgetStartX + deltaX;
        let newY = this.widgetStartY + deltaY;

        // Constrain to viewport
        const maxX = window.innerWidth - this.widget.offsetWidth;
        const maxY = window.innerHeight - this.widget.offsetHeight;

        newX = Math.max(0, Math.min(newX, maxX));
        newY = Math.max(0, Math.min(newY, maxY));

        this.widget.style.left = newX + 'px';
        this.widget.style.top = newY + 'px';
        this.widget.style.right = 'auto';
        this.widget.style.bottom = 'auto';
    }

    endDrag(e) {
        if (!this.isDragging) return;

        this.isDragging = false;
        this.button.classList.remove('dragging');
        document.body.style.userSelect = '';

        // Save position
        this.savePosition();

        // Small delay to prevent click event after drag
        setTimeout(() => {
            this.isDragging = false;
        }, 100);
    }

    savePosition() {
        const rect = this.widget.getBoundingClientRect();
        const position = {
            left: rect.left,
            top: rect.top,
            right: 'auto',
            bottom: 'auto'
        };
        localStorage.setItem('feedbackWidgetPosition', JSON.stringify(position));
    }

    loadPosition() {
        const savedPosition = localStorage.getItem('feedbackWidgetPosition');
        if (savedPosition) {
            try {
                const position = JSON.parse(savedPosition);

                // Check if position is still valid (within viewport)
                if (position.left >= 0 && position.top >= 0 &&
                    position.left <= window.innerWidth - 60 &&
                    position.top <= window.innerHeight - 60) {

                    this.widget.style.left = position.left + 'px';
                    this.widget.style.top = position.top + 'px';
                    this.widget.style.right = 'auto';
                    this.widget.style.bottom = 'auto';
                }
            } catch (e) {
                // Invalid saved position, use default
            }
        }
    }

    openModal() {
        this.modal.classList.add('show');
        document.body.style.overflow = 'hidden';

        // Fill in technical information
        document.getElementById('feedbackPageUrl').value = window.location.href;
        document.getElementById('feedbackUserAgent').value = navigator.userAgent;

        const browserInfo = {
            url: window.location.href,
            timestamp: new Date().toISOString(),
            screen: {
                width: screen.width,
                height: screen.height,
                availWidth: screen.availWidth,
                availHeight: screen.availHeight
            },
            viewport: {
                width: window.innerWidth,
                height: window.innerHeight
            },
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform
        };

        document.getElementById('feedbackBrowserInfo').value = JSON.stringify(browserInfo);

        // Focus on description field
        setTimeout(() => {
            document.getElementById('feedbackDescription').focus();
        }, 300);
    }

    closeModal() {
        this.modal.classList.remove('show');
        document.body.style.overflow = '';
        this.clearMessage();
        this.form.reset();
    }

    async submitFeedback() {
        const submitBtn = document.getElementById('feedbackSubmit');
        const formData = new FormData(this.form);

        // Convert FormData to object
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }

        // Validate required fields
        if (!data.description || data.description.trim() === '') {
            this.showMessage('Per favore, inserisci una descrizione del feedback.', 'error');
            return;
        }

        // Show loading state
        submitBtn.disabled = true;
        submitBtn.textContent = 'Invio in corso...';

        try {
            // Get CSRF token if available
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                            document.querySelector('meta[name=csrf-token]')?.getAttribute('content');

            const headers = {
                'Content-Type': 'application/json',
            };

            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            const response = await fetch('/tickets/api/feedback/', {
                method: 'POST',
                headers: headers,
                credentials: 'same-origin',
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (response.ok && result.success) {
                this.showMessage(result.message, 'success');
                setTimeout(() => {
                    this.closeModal();
                }, 2000);
            } else {
                this.showMessage(result.message || 'Si è verificato un errore durante l\'invio del feedback.', 'error');
            }
        } catch (error) {
            console.error('Errore nell\'invio del feedback:', error);
            this.showMessage('Si è verificato un errore di connessione. Riprova più tardi.', 'error');
        } finally {
            // Reset button state
            submitBtn.disabled = false;
            submitBtn.textContent = 'Invia Feedback';
        }
    }

    showMessage(message, type = 'info') {
        this.messageDiv.innerHTML = `<div class="feedback-message ${type}">${message}</div>`;
        this.messageDiv.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

    clearMessage() {
        this.messageDiv.innerHTML = '';
    }
}

// Initialize the feedback widget when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Only initialize if the widget doesn't already exist
    if (!document.getElementById('feedbackWidget')) {
        new FeedbackWidget();
    }
});

// Also handle cases where the script is loaded after DOM is ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function() {
        if (!document.getElementById('feedbackWidget')) {
            new FeedbackWidget();
        }
    });
} else {
    // DOM is already loaded
    if (!document.getElementById('feedbackWidget')) {
        new FeedbackWidget();
    }
}