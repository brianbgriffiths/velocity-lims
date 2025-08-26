/**
 * Pages Configuration Functions
 * Handles page selection, configuration, drag & drop reordering
 */

// Global variables for pages
let availablePagesData = [];
let currentPageConfig = null;

function loadPagesInterface(pages) {
    console.log('Loading pages interface with data:', pages);
    
    // Debug: Check if element exists and log details
    let enabledPagesDiv = document.getElementById('enabledPages');
    console.log('enabledPages element:', enabledPagesDiv);
    console.log('All elements with enabledPages class:', document.querySelectorAll('.enabled-pages'));
    console.log('All elements with id enabledPages:', document.querySelectorAll('#enabledPages'));
    
    if (!enabledPagesDiv) {
        console.log('Pages interface container not found in DOM - creating it dynamically');
        
        // Find the config cards container and add the pages section
        const configCardsContainer = document.getElementById('configCardsContainer');
        if (configCardsContainer) {
            // Create the pages configuration section
            const pagesConfigHTML = `
                <!-- Pages Configuration -->
                <div class="pages-config-section">
                    <div class="pages-config-header">
                        <h3 class="section-title">Pages Configuration</h3>
                        <button type="button" class="btn-add-page" onclick="showPageSelector()">
                            <i class="fas fa-plus"></i> Add Page
                        </button>
                    </div>
                    <div class="pages-config-content">
                        <div class="enabled-pages" id="enabledPages">
                            <div class="no-pages">No pages configured</div>
                        </div>
                    </div>
                    <!-- Hidden textarea for data storage -->
                    <textarea id="pagesConfig" style="display: none;">[]</textarea>
                </div>
            `;
            
            // Insert after the last config card
            configCardsContainer.insertAdjacentHTML('beforeend', pagesConfigHTML);
            
            // Now try to get the element again
            enabledPagesDiv = document.getElementById('enabledPages');
            console.log('Created enabledPages element:', enabledPagesDiv);
        } else {
            console.error('Config cards container not found - cannot create pages section');
            return;
        }
    }
    
    if (!enabledPagesDiv) {
        console.error('Pages interface container still not found after creation attempt');
        return;
    }
    
    if (!pages || pages.length === 0) {
        enabledPagesDiv.innerHTML = '<div class="no-pages">No pages configured</div>';
        return;
    }
    
    const pagesHTML = pages.map((page, index) => createPageItemHTML(page, index)).join('');
    enabledPagesDiv.innerHTML = pagesHTML;
    
    // Enable drag and drop
    enablePageDragAndDrop();
    
    console.log('Pages interface loaded successfully');
}

function createPageItemHTML(page, index) {
    const config = page.config || {};
    // Internal properties (order, required) no longer displayed; only show flags meaningful to user
    const showAfterComplete = page.show_after_complete ? 'Show after complete' : '';
    
    return `
        <div class="page-item" data-page-id="${page.pcid}" data-index="${index}" draggable="true">
            <div class="page-item-info">
                <i class="fas fa-grip-vertical page-item-drag"></i>
                <div>
                    <div class="page-item-name">${page.page_name}</div>
                    <div class="page-item-details">${showAfterComplete}</div>
                </div>
            </div>
            <div class="page-item-actions">
                <!-- Explicit type="button" to prevent implicit submit inside forms causing full page refresh -->
                <button type="button" class="page-config-button" onclick="showPageConfigModal(${page.pcid}, '${page.page_name}')">
                    <i class="fas fa-cog"></i>
                </button>
            </div>
        </div>
    `;
}

function enablePageDragAndDrop() {
    const container = document.getElementById('enabledPages');
    const draggables = container.querySelectorAll('.page-item');
    
    draggables.forEach(draggable => {
        draggable.removeEventListener('dragstart', handlePageDragStart);
        draggable.removeEventListener('dragend', handlePageDragEnd);
        draggable.addEventListener('dragstart', handlePageDragStart);
        draggable.addEventListener('dragend', handlePageDragEnd);
    });
    
    container.removeEventListener('dragover', handlePageDragOver);
    container.removeEventListener('drop', handlePageDrop);
    container.addEventListener('dragover', handlePageDragOver);
    container.addEventListener('drop', handlePageDrop);
}

function handlePageDragStart(e) {
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handlePageDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const container = document.getElementById('enabledPages');
    const afterElement = getPageDragAfterElement(container, e.clientY);
    const dragging = document.querySelector('.page-item.dragging');
    
    if (afterElement == null) {
        container.appendChild(dragging);
    } else {
        container.insertBefore(dragging, afterElement);
    }
}

function handlePageDrop(e) {
    e.preventDefault();
    updatePagesFromDOM();
}

function handlePageDragEnd(e) {
    e.target.classList.remove('dragging');
}

function getPageDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.page-item:not(.dragging)')];
    
    return draggableElements.reduce((closest, child) => {
        const box = child.getBoundingClientRect();
        const offset = y - box.top - box.height / 2;
        
        if (offset < 0 && offset > closest.offset) {
            return { offset: offset, element: child };
        } else {
            return closest;
        }
    }, { offset: Number.NEGATIVE_INFINITY }).element;
}

function updatePagesFromDOM() {
    const pageItems = document.querySelectorAll('#enabledPages .page-item');
    const pages = [];
    
    pageItems.forEach((item, index) => {
        const pageId = parseInt(item.dataset.pageId);
        const pageData = currentStepConfig.pages.find(p => p.pcid === pageId);
        if (pageData) {
            // Update the order in the config
            if (!pageData.config) pageData.config = {};
            pageData.config.order = index + 1;
            pages.push(pageData);
        }
    });
    
    currentStepConfig.pages = pages;
    updatePageConfigTextarea(getPagesFromInterface());
    console.log('Updated pages order from DOM:', pages);
}

function getPagesFromInterface() {
    const pageItems = document.querySelectorAll('#enabledPages .page-item');
    const enabled_ids = [];
    const configurations = {};
    
    pageItems.forEach((item, index) => {
        const pageId = parseInt(item.dataset.pageId);
        enabled_ids.push(pageId);
        
        // Find the current page data to get its configuration
        const pageData = currentStepConfig.pages.find(p => p.pcid === pageId);
        if (pageData && pageData.config) {
            configurations[pageId] = pageData.config;
        }
    });
    
    return {
        enabled_ids: enabled_ids,
        configurations: configurations
    };
}

function updatePageConfigTextarea(pages) {
    const pagesConfigElement = document.getElementById('pagesConfig');
    if (pagesConfigElement) {
        pagesConfigElement.value = JSON.stringify(pages, null, 2);
    }
}

function showPageSelector() {
    loadAvailablePages();
    document.getElementById('pageSelectorModal').classList.add('show');
}

function hidePageSelector() {
    document.getElementById('pageSelectorModal').classList.remove('show');
}

function loadAvailablePages() {
    const pyoptions = {
        data: {},
        csrf: csrf,
        url: '../get_available_pages',
        submit_mode: 'silent'
    };
    
    console.log('Loading available pages...');
    
    pylims_post(pyoptions).then(result => {
        console.log('Available pages loaded:', result);
        if (result.status === 'success') {
            availablePagesData = result.available_pages;
            renderAvailablePages();
        } else {
            console.error('Error loading available pages:', result.error);
            pylims_ui.error('Failed to load available pages: ' + result.error);
        }
    }).catch(error => {
        console.error('Error loading available pages:', error);
        pylims_ui.error('Failed to load available pages');
    });
}

function renderAvailablePages() {
    const container = document.getElementById('availablePagesList');
    
    if (!availablePagesData || availablePagesData.length === 0) {
        container.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--gray-med);">No pages available</div>';
        return;
    }
    
    // Get currently enabled page IDs
    const enabledPageIds = new Set();
    if (currentStepConfig && currentStepConfig.pages) {
        currentStepConfig.pages.forEach(page => {
            enabledPageIds.add(page.pcid);
        });
    }
    
    const availableHTML = availablePagesData.map(page => {
        const isEnabled = enabledPageIds.has(page.pcid);
        const showAfterComplete = page.show_after_complete ? 'Show after complete' : '';
        
        return `
            <div class="available-item ${isEnabled ? 'disabled' : ''}" onclick="${isEnabled ? '' : `addPage(${page.pcid})`}">
                <div class="available-item-info">
                    <div class="available-item-name">
                        <i class="fas fa-file-alt"></i>
                        ${page.page_name}
                    </div>
                    <div class="available-item-details">${showAfterComplete}</div>
                </div>
                ${isEnabled ? '<div class="available-item-status">Already added</div>' : ''}
            </div>
        `;
    }).join('');
    
    container.innerHTML = availableHTML;
}

function addPage(pageId) {
    console.log('Adding page:', pageId);
    
    // Find the page data
    const pageData = availablePagesData.find(page => page.pcid === pageId);
    if (!pageData) {
        console.error('Page not found:', pageId);
        return;
    }
    
    // Initialize pages array if it doesn't exist
    if (!currentStepConfig.pages) {
        currentStepConfig.pages = [];
    }
    
    // Check if page is already added
    const existingPage = currentStepConfig.pages.find(page => page.pcid === pageId);
    if (existingPage) {
        console.log('Page already added:', pageId);
        return;
    }
    
    // Add page with default configuration
    const newPage = {
        pcid: pageData.pcid,
        page_name: pageData.page_name,
        show_after_complete: pageData.show_after_complete,
        config: {
            order: currentStepConfig.pages.length + 1,
            required: false,
            show_when: 'always'
        }
    };
    
    currentStepConfig.pages.push(newPage);
    
    // Update interface
    loadPagesInterface(currentStepConfig.pages);
    updatePageConfigTextarea(getPagesFromInterface());
    
    // Update available pages list
    renderAvailablePages();
    
    console.log('Page added successfully:', newPage);
    hidePageSelector();
}

function removePage(pageId) {
    console.log('Removing page:', pageId);
    
    if (!currentStepConfig.pages) {
        return;
    }
    
    // Remove page from array
    currentStepConfig.pages = currentStepConfig.pages.filter(page => page.pcid !== pageId);
    
    // Update interface
    loadPagesInterface(currentStepConfig.pages);
    updatePageConfigTextarea(getPagesFromInterface());
    
    console.log('Page removed successfully');
}

function showPageConfigModal(pageId, pageName, evt) {
    // Defensive: if called with an event (e.g. inline onclick passing event implicitly in some browsers), prevent default.
    if (evt && typeof evt.preventDefault === 'function') {
        evt.preventDefault();
        evt.stopPropagation();
    }
    console.log('Showing page config modal for:', pageId, pageName);
    
    // Find the page data
    const pageData = currentStepConfig.pages.find(page => page.pcid === pageId);
    if (!pageData) {
        console.error('Page not found:', pageId);
        return;
    }
    
    currentPageConfig = pageData;
    
    // Update modal title
    document.getElementById('configPageName').textContent = pageName;
    
    // Load current configuration
    const config = pageData.config || {};
    
    // Removed order/required inputs from UI; maintain internal values if present
    document.getElementById('pageShowAfterComplete').checked = pageData.show_after_complete || false;
    document.getElementById('pageCondition').value = config.show_when || 'always';

    // Ensure nested config objects exist for new panels
    ensurePageOptionStructures(currentPageConfig);
    // Render panels
    renderStepDataItems();
    
    // Show modal
    document.getElementById('pageConfigModal').classList.add('show');
}

function hidePageConfigModal() {
    document.getElementById('pageConfigModal').classList.remove('show');
    currentPageConfig = null;
}

function savePageConfig() {
    if (!currentPageConfig) {
        console.error('No page config to save');
        return;
    }
    
    // Get form values
    // Order and required are internal; order maintained via array index; required deprecated
    const showAfterComplete = document.getElementById('pageShowAfterComplete').checked;
    const showWhen = document.getElementById('pageCondition').value;
    
    // Update page configuration
    if (!currentPageConfig.config) {
        currentPageConfig.config = {};
    }
    
    // Preserve existing order if already set; otherwise set based on current collection
    if (typeof currentPageConfig.config.order !== 'number') {
        const idx = currentStepConfig.pages.findIndex(p => p.pcid === currentPageConfig.pcid);
        currentPageConfig.config.order = idx >= 0 ? idx + 1 : currentStepConfig.pages.length;
    }
    // required flag no longer user-facing; retain previous value if it existed
    currentPageConfig.config.show_when = showWhen;
    currentPageConfig.show_after_complete = showAfterComplete;
    
    // Update interface
    loadPagesInterface(currentStepConfig.pages);
    updatePageConfigTextarea(getPagesFromInterface());
    
    console.log('Page configuration saved:', currentPageConfig);
    hidePageConfigModal();
}

// ---------------------- Page Option Panels (Step Data) ----------------------
function ensurePageOptionStructures(page) {
    if (!page.config) page.config = {};
    if (!page.config.step_data) page.config.step_data = { enabled_ids: [], configurations: {} };
    // sample_data & step_scripts panels will be added later
}

function renderStepDataItems() {
    const container = document.getElementById('stepDataItems');
    if (!currentPageConfig || !container) return;
    const sd = currentPageConfig.config.step_data;
    if (!sd.enabled_ids || sd.enabled_ids.length === 0) {
        container.innerHTML = '<div class="step-data-empty">No step data selected</div>';
        return;
    }
    const html = sd.enabled_ids.map(id => {
        const cfg = sd.configurations[id] || {}; // future detailed config
        const label = cfg.label || ('Data #' + id);
        const hasCfg = Object.keys(cfg).length > 0;
        const icon = hasCfg ? 'fas fa-cog' : 'far fa-cog';
        return `
            <div class="step-data-item" data-step-data-id="${id}">
                <div class="step-data-item-main">
                    <div class="step-data-item-name">${label}</div>
                </div>
                <div class="step-data-item-actions">
                    <button type="button" class="step-data-config-btn" title="Configure" onclick="configureStepData(${id})"><i class="${icon}"></i></button>
                    <button type="button" class="step-data-remove-btn" title="Remove" onclick="removeStepData(${id})"><i class="fas fa-times"></i></button>
                </div>
            </div>`;
    }).join('');
    container.innerHTML = html;
}

function showAddStepDataPrompt() {
    if (!currentPageConfig) return;
    // Gather inputs via simple prompts (placeholder UI; replace with proper modal later)
    const key = prompt('Enter unique key (snake_case) for step data:');
    if (!key) return;
    const displayText = prompt('Display label (shown to users):', key) || key;
    const valueTypeStr = prompt('Value type ID (sdtid from step_data_types):', '1');
    if (!valueTypeStr) return;
    const valueType = parseInt(valueTypeStr.trim());
    if (Number.isNaN(valueType)) return alert('Invalid value type');
    const valueDefault = prompt('Default value (optional):', '') || null;
    const requiredFlag = confirm('Mark as required? OK = Yes, Cancel = No');
    const stepType = currentStepConfig.step_type || currentStepConfig.step_type_id || 0;
    const payload = {
        step_type: stepType,
        key: key,
        display_text: displayText,
        value_type: valueType,
        value_default: valueDefault,
        required: requiredFlag,
        read_only: false,
        display_group: 0
    };
    const pyoptions = {
        data: payload,
        csrf: csrf,
        url: '../upsert_step_data_config',
        submit_mode: 'silent'
    };
    pylims_post(pyoptions).then(result => {
        if (result.status === 'success') {
            const sd = currentPageConfig.config.step_data;
            const newId = result.sdcid;
            if (!sd.enabled_ids.includes(newId)) sd.enabled_ids.push(newId);
            sd.configurations[newId] = {
                label: result.display_text,
                key: result.key,
                value_type: result.value_type,
                sdcid: result.sdcid,
                required: payload.required
            };
            renderStepDataItems();
            updatePageConfigTextarea(getPagesFromInterface());
        } else {
            pylims_ui.error('Failed: ' + (result.error || 'Unknown error'));
        }
    }).catch(err => {
        console.error('Error upserting step data config', err);
        pylims_ui.error('Error creating step data config');
    });
}

function configureStepData(id) {
    if (!currentPageConfig) return;
    const sd = currentPageConfig.config.step_data;
    const existing = sd.configurations[id] || {};
    const newLabel = prompt('Set a label for this step data item', existing.label || 'Data #' + id);
    if (newLabel !== null) {
        sd.configurations[id] = { ...existing, label: newLabel };
        renderStepDataItems();
        updatePageConfigTextarea(getPagesFromInterface());
    }
}

function removeStepData(id) {
    if (!currentPageConfig) return;
    const sd = currentPageConfig.config.step_data;
    sd.enabled_ids = sd.enabled_ids.filter(x => x !== id);
    delete sd.configurations[id];
    renderStepDataItems();
    updatePageConfigTextarea(getPagesFromInterface());
}

function removeCurrentPage() {
    if (!currentPageConfig) {
        console.error('No page to remove');
        return;
    }
    
    const pageId = currentPageConfig.pcid;
    hidePageConfigModal();
    removePage(pageId);
}
