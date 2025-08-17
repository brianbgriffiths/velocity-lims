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
let currentConfigModalEl = null;

function initializeSpecialSampleTypes() {
    console.log('Initializing special sample types from embedded template data');
    if (!Array.isArray(specialSampleTypesDataAll)) {
        specialSampleTypesDataAll = [];
    }
}

// Removed network loading; all special sample types are provided inline in template.

function loadSpecialSamplesInterface(stepSpecialSamples) {
    // Group samples by special_type; one card per type containing its enabled samples
    const anchor = document.getElementById('assayConfigCards');
    if (!anchor) return;

    // IMPORTANT: Do NOT wipe entire anchor (contains container card, add button, hidden textareas)
    // Instead remove only prior special sample type cards
    anchor.querySelectorAll('.config-card[data-sample-type-group]').forEach(card => card.remove());

    const enabledIds = (stepSpecialSamples && Array.isArray(stepSpecialSamples.enabled_ids)) ? stepSpecialSamples.enabled_ids : [];
    // Build enabled sample objects
    let enabledSamples = enabledIds.map(id => specialSampleTypesDataAll.find(s => s.ssid === id || s.stid === id)).filter(Boolean);
    // Ensure placeholder type (4) visible even if not enabled
    const placeholderSamples = specialSampleTypesDataAll.filter(s => (s.special_type === 4 || s.sstid === 4 || s.type_id === 4));
    placeholderSamples.forEach(ps => {
        const pid = ps.ssid || ps.stid;
        if (!enabledSamples.find(x => (x.ssid||x.stid) === pid)) {
            enabledSamples.push(ps); // appears but not in enabledIds (ghost)
        }
    });

    // Build map of all available special sample types so empty types still display
    const allTypeMap = {};
    specialSampleTypesDataAll.forEach(s => {
        const typeId = s.special_type || s.type_id || s.sstid || 0;
        if (!allTypeMap[typeId]) {
            allTypeMap[typeId] = s.special_type_name || s.type || `Type ${typeId}`;
        }
    });

    // Group by type id
    const groups = {};
    enabledSamples.forEach(s => {
        const typeId = s.special_type || s.type_id || s.sstid || 0;
        if (!groups[typeId]) groups[typeId] = { typeId, typeName: s.special_type_name || s.type || `Type ${typeId}`, samples: [], uniqueOnly: !!s.unique_only, enabledCount: 0 };
        groups[typeId].samples.push(s);
    });

    // Track enabled count per type separately (placeholder ghost shouldn't count if not actually enabled)
    enabledIds.forEach(id => {
        const s = specialSampleTypesDataAll.find(x => (x.ssid === id) || (x.stid === id));
        if (s) {
            const tid = s.special_type || s.type_id || s.sstid || 0;
            if (!groups[tid]) groups[tid] = { typeId: tid, typeName: s.special_type_name || s.type || `Type ${tid}`, samples: [], uniqueOnly: !!s.unique_only, enabledCount: 0 };
            groups[tid].enabledCount += 1;
            if (groups[tid].uniqueOnly === false && s.unique_only) groups[tid].uniqueOnly = true; // ensure true if any sample marks it
        }
    });

    // Determine insertion point: before the Add Special Sample button container if present
    const addButtonWrapper = anchor.querySelector('.btn-add-special-sample') ? anchor.querySelector('.btn-add-special-sample').closest('div') : null;

    // Add empty group entries for any types not yet represented
    Object.keys(allTypeMap).forEach(typeIdStr => {
        const tid = parseInt(typeIdStr);
        if (!groups[tid]) {
            // find a representative sample for unique_only flag
            const rep = specialSampleTypesDataAll.find(x => (x.special_type || x.type_id || x.sstid || 0) === tid);
            groups[tid] = { typeId: tid, typeName: allTypeMap[tid], samples: [], uniqueOnly: rep ? !!rep.unique_only : false, enabledCount: 0 };
        }
    });

    Object.values(groups).sort((a,b)=>a.typeId-b.typeId).forEach(group => {
        const cardId = `specialSampleTypeCard_${group.typeId}`;
    const addBtnHtml = `<button type="button" class="btn-add-special-sample" onclick="showSpecialSampleSelectorForType(${group.typeId})"><i class=\"fas fa-plus\"></i> Add</button>`;
    const cardHtml = `
            <div class="config-card" id="${cardId}" data-sample-type-group="${group.typeId}">
                <div class="special-samples-config-panel">
                    <div class="special-samples-config-header">
                <span>Enabled ${group.typeName}</span>
                ${addBtnHtml}
                    </div>
                    <div class="enabled-special-samples" id="specialSampleGroup_${group.typeId}">
                        ${group.samples.length ? group.samples.map((sample, idx) => specialSampleItemHTMLForGroup(sample, idx)).join('') : '<div class="no-special-samples" style="padding:6px 8px;color:var(--gray-med);font-size:11px;">No samples of this type enabled</div>'}
                    </div>
                </div>
            </div>`;
        if (addButtonWrapper) {
            addButtonWrapper.insertAdjacentHTML('beforebegin', cardHtml);
        } else {
            anchor.insertAdjacentHTML('beforeend', cardHtml);
        }
    });

    updateSpecialSamplesFromDOM();
}

function specialSampleItemHTMLForGroup(sample, index) {
    const sampleId = sample.ssid || sample.stid;
    const displayName = sample.special_name || sample.name || `Sample ${sampleId}`;
    const displayType = sample.special_type_name || sample.type || 'Type';
    const hasConfig = specialSampleConfigs[sampleId] && Object.keys(specialSampleConfigs[sampleId]).length > 0;
    const gearIcon = hasConfig ? 'fas fa-cog' : 'far fa-cog';
    const buttonTitle = hasConfig ? 'Sample configured - click to edit' : 'Configure special sample';
    const sampleTypeId = sample.special_type || sample.type_id || sample.sstid || 0;
    return `
        <div class="special-sample-item" data-sample-id="${sampleId}" data-sample-type="${sampleTypeId}" data-index="${index}" draggable="false">
            <div class="special-sample-drag-handle" style="cursor:default;">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="special-sample-info">
                <div class="special-sample-name">${displayName}</div>
                <div class="special-sample-type">${displayType}</div>
            </div>
            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModal(${sampleId}, '${displayName.replace(/'/g, "&#39;")}', '${displayType.replace(/'/g, "&#39;")}')" title="${buttonTitle}"><i class="${gearIcon}"></i></button>
        </div>`;
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

function enableSpecialSampleDragAndDrop() { /* No drag-drop for grouped view */ }

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
    const items = document.querySelectorAll('#assayConfigCards .special-sample-item');
    const samples = [];
    items.forEach(item => {
        const id = parseInt(item.dataset.sampleId);
        const sampleData = specialSampleTypesDataAll.find(s => (s.ssid === id) || (s.stid === id));
        if (sampleData) samples.push(sampleData);
    });
    updateSpecialSampleConfigTextarea(samples);
}

function getSpecialSamplesFromInterface() {
    const data = { enabled_ids: [], configurations: {} };
    document.querySelectorAll('#assayConfigCards .special-sample-item').forEach(item => {
        const id = parseInt(item.dataset.sampleId);
        // Exclude placeholder (type 4) if it was auto-added but not originally enabled? We include if present in UI.
        if (!data.enabled_ids.includes(id)) data.enabled_ids.push(id);
        if (specialSampleConfigs[id] && Object.keys(specialSampleConfigs[id]).length > 0) {
            data.configurations[id] = specialSampleConfigs[id];
        }
    });
    console.log('Getting special samples data for step config (grouped):', data);
    return data;
}

function updateSpecialSampleConfigTextarea(specialSamples) {
    let el = document.getElementById('specialSampleConfig');
    if (!el) {
        console.warn('specialSampleConfig textarea not found; creating hidden textarea dynamically');
        const anchor = document.getElementById('assayConfigCards');
        if (anchor) {
            el = document.createElement('textarea');
            el.id = 'specialSampleConfig';
            el.style.display = 'none';
            anchor.appendChild(el);
        } else {
            return; // no anchor, cannot persist
        }
    }
    el.value = JSON.stringify(specialSamples, null, 2);
}

function showSpecialSampleSelector() {
    const modal = document.getElementById('specialSampleSelectorModal');
    modal.style.display = 'flex';
    
    renderAvailableSpecialSamples();
}

function showSpecialSampleSelectorForType(typeId) {
    const modal = document.getElementById('specialSampleSelectorModal');
    if (!modal) return;
    modal.style.display = 'flex';
    renderAvailableSpecialSamples(typeId);
}

function hideSpecialSampleSelector() {
    const modal = document.getElementById('specialSampleSelectorModal');
    modal.style.display = 'none';
}

function renderAvailableSpecialSamples(filterTypeId=null) {
    const listDiv = document.getElementById('availableSpecialSamplesList');
    if (!listDiv) return;
    if (specialSampleTypesDataAll.length === 0) {
        listDiv.innerHTML = '<div style="text-align:center;padding:20px;color:var(--gray-med);">No special sample types available</div>';
        return;
    }
    const enabled = new Set();
    document.querySelectorAll('#assayConfigCards .special-sample-item').forEach(item => enabled.add(parseInt(item.dataset.sampleId)));
    let html = '';
        specialSampleTypesDataAll.forEach(sample => {
            const typeId = sample.special_type || sample.type_id || sample.sstid || 0;
            if (filterTypeId !== null && typeId !== filterTypeId) return;
            const sampleId = sample.ssid || sample.stid;
            const isEnabled = enabled.has(sampleId);
            const disabledClass = (sample.unique_only && isEnabled) ? 'disabled' : '';
            const title = (sample.unique_only && isEnabled) ? 'Special sample already added' : 'Click to add this special sample';
            html += `
                <div class=\"available-special-sample ${disabledClass}\"
                     onclick=\"${(sample.unique_only && isEnabled) ? '' : `addSpecialSample(${sampleId})`}\"
                     title=\"${title}\">
                    <div class=\"special-sample-info\">
                        <div class=\"special-sample-name\">${sample.special_name || sample.name}</div>
                        <div class=\"special-sample-type\">${sample.special_type_name || sample.type}</div>
                    </div>
                    ${isEnabled ? '<div style=\\"margin-left:auto;color:var(--green-med);\\"><i class=\\"fas fa-check\\"></i></div>' : ''}
                </div>`;
        });
    if (!html) {
        listDiv.innerHTML = '<div style="text-align:center;padding:18px;color:var(--gray-med);font-size:12px;">All samples of this type have been added</div>';
    } else {
        listDiv.innerHTML = html;
    }

}

function addSpecialSample(sampleId) {
    const sample = specialSampleTypesDataAll.find(s => s.ssid === sampleId || s.stid === sampleId);
    if (!sample) return;
    // If already in UI, skip
    if (document.querySelector(`#assayConfigCards .special-sample-item[data-sample-id="${sampleId}"]`)) return;
    // Enforce unique_only: if any sample of same type enabled, block
    if (sample.unique_only) {
        const typeId = sample.special_type || sample.type_id || sample.sstid || 0;
        const existingOfType = document.querySelector(`#assayConfigCards .special-sample-item[data-sample-type="${typeId}"]`);
        if (existingOfType) {
            pylims_ui.error('This special sample type can only be added once');
            hideSpecialSampleSelector();
            return;
        }
    }
    // Build current enabled list (excluding placeholders if any logic later)
    const current = getSpecialSamplesFromInterface().enabled_ids;
    const updated = current.concat([sampleId]);
    loadSpecialSamplesInterface({ enabled_ids: updated });
    renderAvailableSpecialSamples();
    hideSpecialSampleSelector();
}

function removeSpecialSample(sampleId) {
    // Remove item from its group list
    const item = document.querySelector(`#assayConfigCards .special-sample-item[data-sample-id="${sampleId}"]`);
    if (item) {
        const parentList = item.parentElement;
        item.remove();
        // If list becomes empty, remove entire card
        if (parentList && parentList.querySelectorAll('.special-sample-item').length === 0) {
            const card = parentList.closest('.config-card');
            if (card) card.remove();
        }
    }
    if (specialSampleConfigs[sampleId]) delete specialSampleConfigs[sampleId];
    updateSpecialSamplesFromDOM();
    renderAvailableSpecialSamples();
    if (!document.querySelector('#assayConfigCards .special-sample-item')) {
        document.getElementById('assayConfigCards').innerHTML += '<div class="no-special-samples">No special samples configured</div>';
    }
}

function showSpecialSampleConfigModal(sampleId, sampleName, sampleType) {
    console.log('showSpecialSampleConfigModal called with:', sampleId, sampleName, sampleType);
    currentConfigSampleId = sampleId;
    currentConfigSampleType = sampleType;
    const sampleObj = specialSampleTypesDataAll.find(s => (s.ssid === sampleId) || (s.stid === sampleId));
    const typeId = sampleObj ? (sampleObj.special_type || sampleObj.type_id || sampleObj.sstid || 0) : 0;
    const specificId = `specialSampleConfigModal_type${typeId}`;
    currentConfigModalEl = document.getElementById(specificId) || document.getElementById('specialSampleConfigModal_generic');
    if (!currentConfigModalEl) return;
    currentConfigModalEl.querySelectorAll('.configSampleName').forEach(el => el.textContent = sampleName);
    const existingConfig = specialSampleConfigs[sampleId] || { count:1, createForEach:'step', autoAdd:false, placement:'user_placed', specificWell:'A1', afterSamplesCount:1 };
    const setVal = (sel, val, prop='value') => { const el = currentConfigModalEl.querySelector(sel); if (el) el[prop] = val; };
    setVal('.sampleCount', existingConfig.count);
    setVal('.createForEach', existingConfig.createForEach);
    const aa = currentConfigModalEl.querySelector('.autoAdd'); if (aa) aa.checked = existingConfig.autoAdd;
    currentConfigModalEl.querySelectorAll('.placement').forEach(r=>{ r.checked = (r.value === existingConfig.placement); });
    handlePlacementDetailDisplay(existingConfig.placement, currentConfigModalEl);
    setVal('.specificWell', existingConfig.specificWell);
    setVal('.afterSamplesCount', existingConfig.afterSamplesCount);
    currentConfigModalEl.style.display = 'flex';
    currentConfigModalEl.querySelectorAll('.placement').forEach(radio => {
        radio.addEventListener('change', () => handlePlacementDetailDisplay(radio.value, currentConfigModalEl));
    });
}

function hideSpecialSampleConfigModal() {
    if (currentConfigModalEl) currentConfigModalEl.style.display = 'none';
    currentConfigSampleId = null;
    currentConfigSampleType = null;
    currentConfigModalEl = null;
}

function saveSpecialSampleConfig() {
    if (!currentConfigSampleId || !currentConfigModalEl) return;
    const m = currentConfigModalEl;
    const count = parseInt((m.querySelector('.sampleCount')||{value:1}).value) || 1;
    const createForEach = (m.querySelector('.createForEach')||{value:'step'}).value;
    const autoAdd = (m.querySelector('.autoAdd')||{checked:false}).checked;
    const placementRadio = Array.from(m.querySelectorAll('.placement')).find(r=>r.checked);
    const placement = placementRadio ? placementRadio.value : 'user_placed';
    const specificWell = (m.querySelector('.specificWell')||{value:'A1'}).value.trim() || 'A1';
    const afterSamplesCount = parseInt((m.querySelector('.afterSamplesCount')||{value:1}).value) || 1;
    specialSampleConfigs[currentConfigSampleId] = { count, createForEach, autoAdd, placement, specificWell, afterSamplesCount };
    console.log(`Saved configuration for sample ID ${currentConfigSampleId}:`, specialSampleConfigs[currentConfigSampleId]);
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

function handlePlacementDetailDisplay(placement, modalEl) {
    const specific = modalEl.querySelector('.specificWellDetail');
    const after = modalEl.querySelector('.afterSamplesDetail');
    if (specific) specific.style.display = (placement === 'specific_well') ? 'flex' : 'none';
    if (after) after.style.display = (placement === 'after_samples') ? 'flex' : 'none';
}
