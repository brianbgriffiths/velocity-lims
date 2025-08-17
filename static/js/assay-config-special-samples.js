/**
 * Special Samples Configuration Functions
 * Handles special sample types, configuration modals, and placement options
 */

// Global variables for special samples (all types provided inline by template)
// Modern format only: backend supplies {enabled_ids: [...], configurations: {...}}
let specialSampleTypesDataAll = window.specialSampleTypesData || [];
let specialSampleConfigs = {};
let currentConfigSampleId = null;
let currentConfigSampleType = null;

function initializeSpecialSampleTypes() {
    console.log('Initializing special sample types from embedded template data');
    if (!Array.isArray(specialSampleTypesDataAll)) {
        specialSampleTypesDataAll = [];
    }
}

// Removed network loading; all special sample types are provided inline in template.

function loadSpecialSamplesInterface(stepSpecialSamples) {
    // Render per-type cards: each sample has its own card (since user wants separation by type)
    const anchor = document.getElementById('specialSamplesCardsAnchor');
    if (!anchor) return;
    anchor.innerHTML = '';

    const enabledIds = (stepSpecialSamples && Array.isArray(stepSpecialSamples.enabled_ids)) ? stepSpecialSamples.enabled_ids : [];
    // Build list; include placeholder type id 4 always
    let samplesToRender = enabledIds.map(id => specialSampleTypesDataAll.find(s => s.ssid === id || s.stid === id)).filter(Boolean);
    const placeholderSamples = specialSampleTypesDataAll.filter(s => (s.special_type === 4 || s.sstid === 4 || s.type_id === 4));
    placeholderSamples.forEach(ps => {
        const pid = ps.ssid || ps.stid;
        if (pid && !samplesToRender.find(x => (x.ssid||x.stid) === pid)) samplesToRender.push(ps);
    });

    if (!samplesToRender.length) {
        anchor.innerHTML = '<div class="no-special-samples">No special samples configured</div>';
        return;
    }

    samplesToRender.forEach(sample => {
        const sampleId = sample.ssid || sample.stid;
        const cardId = `specialSampleCard_${sampleId}`;
        const configured = specialSampleConfigs[sampleId] && Object.keys(specialSampleConfigs[sampleId]).length > 0;
        const displayName = sample.special_name || sample.name || `Sample ${sampleId}`;
        const displayType = sample.special_type_name || sample.type || 'Type';
        const sampleTypeId = sample.special_type || sample.type_id || sample.sstid || 0;
        const gearIcon = configured ? 'fas fa-cog' : 'far fa-cog';
        const buttonTitle = configured ? 'Sample configured - click to edit' : 'Configure special sample';
        const html = `
            <div class="config-card" id="${cardId}" data-sample-id="${sampleId}" data-sample-type="${sampleTypeId}">
                <label class="form-label">${displayType}</label>
                <div class="special-samples-config-panel">
                    <div class="special-samples-config-header">
                        <span>${displayName}</span>
                        <div style="display:flex; gap:6px;">
                            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModal(${sampleId}, '${displayName.replace(/'/g, "&#39;")}', '${displayType.replace(/'/g, "&#39;")}')" title="${buttonTitle}"><i class="${gearIcon}"></i></button>
                            <button type="button" class="btn-remove-page" style="padding:4px 6px;font-size:10px;" onclick="removeSpecialSample(${sampleId})" title="Remove"><i class="fas fa-trash"></i></button>
                        </div>
                    </div>
                    <div class="enabled-special-samples" style="padding:6px 10px;">
                        <div class="special-sample-item" data-sample-id="${sampleId}" data-sample-type="${sampleTypeId}" draggable="false">
                            <div class="special-sample-info">
                                <div class="special-sample-name">${displayName}</div>
                                <div class="special-sample-type">${displayType}</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>`;
        anchor.insertAdjacentHTML('beforeend', html);
    });

    updateSpecialSamplesFromDOM();
}

function createSpecialSampleItemHTML(sample, index) {
    const sampleId = sample.ssid || sample.stid; // prefer modern ssid
    const displayName = sample.special_name || sample.name || `Sample ${sampleId}`;
    const displayType = sample.special_type_name || sample.type || 'Type';
    const hasConfig = specialSampleConfigs[sampleId] && Object.keys(specialSampleConfigs[sampleId]).length > 0;
    const gearIcon = hasConfig ? 'fas fa-cog' : 'far fa-cog';
    const buttonTitle = hasConfig ? 'Sample configured - click to edit' : 'Configure special sample';
    const sampleTypeId = sample.special_type || sample.type_id || sample.sstid || 0;
    return `
        <div class="special-sample-item" data-sample-id="${sampleId}" data-sample-type="${sampleTypeId}" data-index="${index}" draggable="true">
            <div class="special-sample-drag-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="special-sample-info">
                <div class="special-sample-name">${displayName}</div>
                <div class="special-sample-type">${displayType}</div>
            </div>
            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModal(${sampleId}, '${displayName.replace(/'/g, "&#39;")}', '${displayType.replace(/'/g, "&#39;")}')" title="${buttonTitle}"><i class="${gearIcon}"></i></button>
        </div>`;
}

function enableSpecialSampleDragAndDrop() { /* No-op: per-type cards remove list reordering requirement */ }

function handleSpecialSampleDragStart(e) {
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}

function handleSpecialSampleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const container = document.getElementById('enabledSpecialSamples');
    const afterElement = getSpecialSampleDragAfterElement(container, e.clientY);
    const dragging = document.querySelector('.special-sample-item.dragging');
    
    if (afterElement == null) {
        container.appendChild(dragging);
    } else {
        container.insertBefore(dragging, afterElement);
    }
}

function handleSpecialSampleDrop(e) {
    e.preventDefault();
    updateSpecialSamplesFromDOM();
}

function handleSpecialSampleDragEnd(e) {
    e.target.classList.remove('dragging');
}

function getSpecialSampleDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.special-sample-item:not(.dragging)')];
    
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

function updateSpecialSamplesFromDOM() {
    const cards = document.querySelectorAll('#specialSamplesCardsAnchor .config-card[data-sample-id]');
    const samples = [];
    cards.forEach(card => {
        const id = parseInt(card.dataset.sampleId);
        const sampleData = specialSampleTypesDataAll.find(s => (s.ssid === id) || (s.stid === id));
        if (sampleData) samples.push(sampleData);
    });
    updateSpecialSampleConfigTextarea(samples);
}

function getSpecialSamplesFromInterface() {
    const data = { enabled_ids: [], configurations: {} };
    document.querySelectorAll('#specialSamplesCardsAnchor .config-card[data-sample-id]').forEach(card => {
        const id = parseInt(card.dataset.sampleId);
        data.enabled_ids.push(id);
        if (specialSampleConfigs[id] && Object.keys(specialSampleConfigs[id]).length > 0) {
            data.configurations[id] = specialSampleConfigs[id];
        }
    });
    console.log('Getting special samples data for step config:', data);
    return data;
}

function updateSpecialSampleConfigTextarea(specialSamples) {
    document.getElementById('specialSampleConfig').value = JSON.stringify(specialSamples, null, 2);
}

function showSpecialSampleSelector() {
    const modal = document.getElementById('specialSampleSelectorModal');
    modal.style.display = 'flex';
    
    renderAvailableSpecialSamples();
}

function hideSpecialSampleSelector() {
    const modal = document.getElementById('specialSampleSelectorModal');
    modal.style.display = 'none';
}

function renderAvailableSpecialSamples() {
    const listDiv = document.getElementById('availableSpecialSamplesList');
    if (!listDiv) return;
    if (specialSampleTypesDataAll.length === 0) {
        listDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--gray-med);">No special sample types available</div>';
        return;
    }
    const enabled = new Set();
    document.querySelectorAll('#specialSamplesCardsAnchor .config-card[data-sample-id]').forEach(card => enabled.add(parseInt(card.dataset.sampleId)));
    let html = '';
    specialSampleTypesDataAll.forEach(sample => {
        const sampleId = sample.ssid || sample.stid;
        const isEnabled = enabled.has(sampleId);
        html += `<div class="available-special-sample ${isEnabled ? 'disabled' : ''}" ${isEnabled ? '' : `onclick="addSpecialSample(${sampleId})"`} title="${isEnabled ? 'Special sample already added' : 'Click to add this special sample'}">`+
            `<div class="special-sample-info"><div class="special-sample-name">${sample.special_name || sample.name}</div><div class="special-sample-type">${sample.special_type_name || sample.type}</div></div>`+
            `${isEnabled ? '<div style=\"margin-left:auto;color:var(--green-med);\"><i class=\"fas fa-check\"></i></div>' : ''}`+
            `</div>`;
    });
    listDiv.innerHTML = html;
}

function addSpecialSample(sampleId) {
    const sample = specialSampleTypesDataAll.find(s => s.ssid === sampleId || s.stid === sampleId);
    if (!sample) return;
    const existingCard = document.querySelector(`#specialSamplesCardsAnchor .config-card[data-sample-id="${sampleId}"]`);
    if (existingCard) return; // already
    // Append card
    const currentData = { enabled_ids: getSpecialSamplesFromInterface().enabled_ids.concat([sampleId]) };
    loadSpecialSamplesInterface(currentData); // re-render all for simplicity
    renderAvailableSpecialSamples();
    hideSpecialSampleSelector();
}

function removeSpecialSample(sampleId) {
    const card = document.getElementById(`specialSampleCard_${sampleId}`);
    if (card) card.remove();
    if (specialSampleConfigs[sampleId]) delete specialSampleConfigs[sampleId];
    updateSpecialSamplesFromDOM();
    renderAvailableSpecialSamples();
    if (!document.querySelector('#specialSamplesCardsAnchor .config-card')) {
        document.getElementById('specialSamplesCardsAnchor').innerHTML = '<div class="no-special-samples">No special samples configured</div>';
    }
}

function showSpecialSampleConfigModal(sampleId, sampleName, sampleType) {
    console.log('showSpecialSampleConfigModal called with:', sampleId, sampleName, sampleType);
    
    currentConfigSampleId = sampleId;
    currentConfigSampleType = sampleType;
    
    // Update modal title
    document.getElementById('configSampleName').textContent = sampleName;
    
    // Load existing configuration if available
    const existingConfig = specialSampleConfigs[sampleId] || {
        count: 1,
        createForEach: 'step',
        autoAdd: false,
        placement: 'user_placed',
        specificWell: 'A1',
        afterSamplesCount: 1
    };
    
    // Populate form fields
    document.getElementById('sampleCount').value = existingConfig.count;
    document.getElementById('createForEach').value = existingConfig.createForEach;
    document.getElementById('autoAdd').checked = existingConfig.autoAdd;
    
    // Handle placement radio buttons
    document.querySelector(`input[name="placement"][value="${existingConfig.placement}"]`).checked = true;
    updatePlacementDetails(existingConfig.placement);
    
    document.getElementById('specificWell').value = existingConfig.specificWell;
    document.getElementById('afterSamplesCount').value = existingConfig.afterSamplesCount;
    
    // Show modal
    document.getElementById('specialSampleConfigModal').style.display = 'flex';
}

function hideSpecialSampleConfigModal() {
    document.getElementById('specialSampleConfigModal').style.display = 'none';
    currentConfigSampleId = null;
    currentConfigSampleType = null;
}

function saveSpecialSampleConfig() {
    if (!currentConfigSampleId) return;
    
    const count = parseInt(document.getElementById('sampleCount').value) || 1;
    const createForEach = document.getElementById('createForEach').value;
    const autoAdd = document.getElementById('autoAdd').checked;
    const placement = document.querySelector('input[name="placement"]:checked').value;
    const specificWell = document.getElementById('specificWell').value.trim() || 'A1';
    const afterSamplesCount = parseInt(document.getElementById('afterSamplesCount').value) || 1;
    
    // Save configuration
    specialSampleConfigs[currentConfigSampleId] = {
        count: count,
        createForEach: createForEach,
        autoAdd: autoAdd,
        placement: placement,
        specificWell: specificWell,
        afterSamplesCount: afterSamplesCount
    };
    
    console.log(`Saved configuration for sample ID ${currentConfigSampleId}:`, specialSampleConfigs[currentConfigSampleId]);
    
    // Update visual indicator (add a small dot or change styling to show it's configured)
    const sampleItem = document.querySelector(`[data-sample-id="${currentConfigSampleId}"]`);
    if (sampleItem) {
        const configButton = sampleItem.querySelector('.special-sample-config-button');
        if (configButton) {
            configButton.style.backgroundColor = 'var(--green-med)';
            configButton.title = 'Sample configured - click to edit';
        }
    }
    
    hideSpecialSampleConfigModal();
    pylims_ui.success('Special sample configuration saved');
}

function removeCurrentSpecialSample() {
    if (!currentConfigSampleId || !currentConfigSampleType) return;
    
    // Remove the special sample
    removeSpecialSample(currentConfigSampleId, currentConfigSampleType);
    
    // Hide the modal
    hideSpecialSampleConfigModal();
}

function updatePlacementDetails(placement) {
    // Hide all detail sections first
    document.getElementById('specificWellDetail').style.display = 'none';
    document.getElementById('afterSamplesDetail').style.display = 'none';
    
    // Show relevant detail section
    if (placement === 'specific_well') {
        document.getElementById('specificWellDetail').style.display = 'flex';
    } else if (placement === 'after_samples') {
        document.getElementById('afterSamplesDetail').style.display = 'flex';
    }
}

// Add event listeners for placement radio buttons when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[name="placement"]').forEach(radio => {
        radio.addEventListener('change', function() {
            updatePlacementDetails(this.value);
        });
    });
});
