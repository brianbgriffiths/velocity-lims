/**
 * Special Samples Configuration Functions
 * Handles special sample types, configuration modals, and placement options
 */

// Global variables for special samples (all types provided inline by template)
// Unified global provided by template: window.specialSampleTypesData
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

function loadSpecialSamplesInterface(specialSamples) {
    console.log('Loading special samples interface with data:', specialSamples);
    
    const enabledSpecialSamplesDiv = document.getElementById('enabledSpecialSamples');
    if (!enabledSpecialSamplesDiv) {
        console.warn('Special samples container #enabledSpecialSamples not found in DOM');
        return;
    }
    
    if (!specialSamples || specialSamples.length === 0) {
        enabledSpecialSamplesDiv.innerHTML = '<div class="no-special-samples">No special samples configured for this step</div>';
        return;
    }
    
    const specialSamplesHTML = specialSamples.map((sample, index) => {
        return createSpecialSampleItemHTML(sample, index);
    }).join('');
    
    enabledSpecialSamplesDiv.innerHTML = specialSamplesHTML;
    
    // Enable drag and drop for special samples reordering
    enableSpecialSampleDragAndDrop();
}

function createSpecialSampleItemHTML(sample, index) {
    // Determine if the sample has configuration
    const sampleId = sample.stid;
    const hasConfig = specialSampleConfigs[sampleId] && Object.keys(specialSampleConfigs[sampleId]).length > 0;
    
    // Use thin gear for unconfigured, solid gear for configured
    const gearIcon = hasConfig ? 'fas fa-cog' : 'far fa-cog';
    const buttonTitle = hasConfig ? 'Sample configured - click to edit' : 'Configure special sample';
    
    return `
        <div class="special-sample-item" data-sample-id="${sampleId}" data-index="${index}" draggable="true">
            <div class="special-sample-drag-handle">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="special-sample-info">
                <div class="special-sample-name">${sample.name}</div>
                <div class="special-sample-type">${sample.type}</div>
            </div>
            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModal(${sampleId}, '${sample.name}', '${sample.type}')" title="${buttonTitle}">
                <i class="${gearIcon}"></i>
            </button>
        </div>
    `;
}

function enableSpecialSampleDragAndDrop() {
    const container = document.getElementById('enabledSpecialSamples');
    const draggables = container.querySelectorAll('.special-sample-item');
    
    draggables.forEach(draggable => {
        draggable.removeEventListener('dragstart', handleSpecialSampleDragStart);
        draggable.removeEventListener('dragend', handleSpecialSampleDragEnd);
        draggable.addEventListener('dragstart', handleSpecialSampleDragStart);
        draggable.addEventListener('dragend', handleSpecialSampleDragEnd);
    });
    
    container.removeEventListener('dragover', handleSpecialSampleDragOver);
    container.removeEventListener('drop', handleSpecialSampleDrop);
    container.addEventListener('dragover', handleSpecialSampleDragOver);
    container.addEventListener('drop', handleSpecialSampleDrop);
}

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
    const specialSampleItems = document.querySelectorAll('#enabledSpecialSamples .special-sample-item');
    const specialSamples = [];
    
    specialSampleItems.forEach((item, index) => {
        const sampleId = parseInt(item.dataset.sampleId);
        const sampleData = specialSampleTypesDataAll.find(s => s.stid === sampleId);
        if (sampleData) {
            specialSamples.push(sampleData);
        }
    });
    
    console.log('Updated special samples from DOM:', specialSamples);
    updateSpecialSampleConfigTextarea(specialSamples);
}

function getSpecialSamplesFromInterface() {
    // Return object with enabled sample IDs and their configurations
    const specialSamplesData = {
        enabled_ids: [],
        configurations: {}
    };
    
    const specialSampleItems = document.querySelectorAll('#enabledSpecialSamples .special-sample-item');
    specialSampleItems.forEach(item => {
        const sampleId = parseInt(item.dataset.sampleId);
        specialSamplesData.enabled_ids.push(sampleId);
        
        // Include configuration if it exists
        if (specialSampleConfigs[sampleId] && Object.keys(specialSampleConfigs[sampleId]).length > 0) {
            specialSamplesData.configurations[sampleId] = specialSampleConfigs[sampleId];
        }
    });
    
    console.log('Getting special samples data for step config:', specialSamplesData);
    return specialSamplesData;
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
    
    console.log('renderAvailableSpecialSamples called');
    console.log('specialSampleTypesDataAll:', specialSampleTypesDataAll);
    
    if (specialSampleTypesDataAll.length === 0) {
        listDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--gray-med);">No special sample types available</div>';
        return;
    }
    
    // Get currently enabled special sample IDs
    const enabledSpecialSampleIds = new Set();
    document.querySelectorAll('#enabledSpecialSamples .special-sample-item').forEach(item => {
        enabledSpecialSampleIds.add(parseInt(item.dataset.sampleId));
    });
    
    let html = '';
    specialSampleTypesDataAll.forEach(sample => {
        const sampleId = sample.stid;
        const isEnabled = enabledSpecialSampleIds.has(sampleId);
        const disabledClass = isEnabled ? 'disabled' : '';
        const title = isEnabled ? 'Special sample already added' : 'Click to add this special sample';
        
        html += `
            <div class="available-special-sample ${disabledClass}" 
                 onclick="${isEnabled ? '' : `addSpecialSample(${sampleId})`}" 
                 title="${title}">
                <div class="special-sample-info">
                    <div class="special-sample-name">${sample.name}</div>
                    <div class="special-sample-type">${sample.type}</div>
                </div>
                ${isEnabled ? '<div style="margin-left: auto; color: var(--green-med);"><i class="fas fa-check"></i></div>' : ''}
            </div>
        `;
    });
    
    listDiv.innerHTML = html;
}

function addSpecialSample(sampleId) {
    const sample = specialSampleTypesDataAll.find(s => s.stid === sampleId);
    if (!sample) {
        console.log('Special sample not found:', sampleId);
        return;
    }
    
    // Check if already enabled
    const existingItem = document.querySelector(`#enabledSpecialSamples [data-sample-id="${sampleId}"]`);
    if (existingItem) {
        console.log('Special sample already enabled:', sampleId);
        return;
    }
    
    console.log('Adding special sample:', sample);
    
    // Add to the enabled special samples display
    const enabledSpecialSamplesDiv = document.getElementById('enabledSpecialSamples');
    const noSpecialSamplesDiv = enabledSpecialSamplesDiv.querySelector('.no-special-samples');
    
    if (noSpecialSamplesDiv) {
        enabledSpecialSamplesDiv.innerHTML = '';
    }
    
    const existingItems = enabledSpecialSamplesDiv.querySelectorAll('.special-sample-item');
    const specialSampleHTML = createSpecialSampleItemHTML(sample, existingItems.length);
    enabledSpecialSamplesDiv.insertAdjacentHTML('beforeend', specialSampleHTML);
    
    // Re-enable drag and drop
    enableSpecialSampleDragAndDrop();
    
    // Update the special samples array
    updateSpecialSamplesFromDOM();
    
    // Update the available special samples display
    renderAvailableSpecialSamples();
    
    // Hide modal
    hideSpecialSampleSelector();
}

function removeSpecialSample(sampleId) {
    // Remove from DOM
    const specialSampleItem = document.querySelector(`#enabledSpecialSamples [data-sample-id="${sampleId}"]`);
    if (specialSampleItem) {
        specialSampleItem.remove();
    }
    
    // Remove configuration
    if (specialSampleConfigs[sampleId]) {
        delete specialSampleConfigs[sampleId];
        console.log(`Removed configuration for special sample ${sampleId}`);
    }
    
    // Check if no special samples remain
    const enabledSpecialSamplesDiv = document.getElementById('enabledSpecialSamples');
    const remainingItems = enabledSpecialSamplesDiv.querySelectorAll('.special-sample-item');
    if (remainingItems.length === 0) {
        enabledSpecialSamplesDiv.innerHTML = '<div class="no-special-samples">No special samples configured for this step</div>';
    }
    
    // Update the special samples array
    updateSpecialSamplesFromDOM();
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
