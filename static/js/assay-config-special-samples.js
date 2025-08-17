/**
 * Special Samples Configuration Functions
 * Handles special sample types, configuration modals, and placement options
 */

// Global variables for special samples (all types provided inline by template)
// Modern format only: backend supplies {enabled_ids: [...], configurations: {...}}
let specialSampleTypesDataAll = window.specialSampleTypesData || [];
let specialSampleConfigs = {}; // legacy id-keyed (kept for backward compatibility / migration)
let specialSampleEnabledIds = []; // ordered list permitting duplicates
let specialSampleInstanceConfigs = []; // index-keyed configs matching enabled_ids
let currentConfigSampleId = null;
let currentConfigSampleType = null;
let currentConfigModalEl = null;
let currentConfigInstanceIndex = null;

function initializeSpecialSampleTypes() {
    console.log('Initializing special sample types from embedded template data');
    if (!Array.isArray(specialSampleTypesDataAll)) {
        specialSampleTypesDataAll = [];
    }
}

// Removed network loading; all special sample types are provided inline in template.

function loadSpecialSamplesInterface(stepSpecialSamples) {
    console.log('[SpecialSamples] loadSpecialSamplesInterface called with', stepSpecialSamples);
    // Group samples by special_type; one card per type containing its enabled samples
    const anchor = document.getElementById('assayConfigCards');
    if (!anchor) return;

    // IMPORTANT: Do NOT wipe entire anchor (contains container card, add button, hidden textareas)
    // Instead remove only prior special sample type cards
    anchor.querySelectorAll('.config-card[data-sample-type-group]').forEach(card => card.remove());

    const enabledIds = (stepSpecialSamples && Array.isArray(stepSpecialSamples.enabled_ids)) ? stepSpecialSamples.enabled_ids.slice() : [];
    specialSampleEnabledIds = enabledIds.slice();
    // Build instance list with index (preserving duplicate order)
    const enabledInstances = enabledIds.map((id, idx) => {
        const base = specialSampleTypesDataAll.find(s => s.ssid === id || s.stid === id);
        if (!base) return null;
        return { ...base, __instanceIndex: idx };
    }).filter(Boolean);
    // Migrate configurations (index vs id keyed)
    specialSampleInstanceConfigs = [];
    if (stepSpecialSamples && stepSpecialSamples.configurations) {
        Object.keys(stepSpecialSamples.configurations).forEach(key => {
            const cfg = stepSpecialSamples.configurations[key];
            if (cfg && typeof cfg === 'object') {
                if (!isNaN(parseInt(key))) {
                    specialSampleInstanceConfigs[parseInt(key)] = cfg; // already index keyed
                }
            }
        });
        // If no index keys found, treat as legacy id-keyed
        if (specialSampleInstanceConfigs.length === 0) {
            enabledIds.forEach((id, idx) => {
                if (stepSpecialSamples.configurations[id]) {
                    specialSampleInstanceConfigs[idx] = stepSpecialSamples.configurations[id];
                }
            });
        }
    }
    // Placeholder type (4) visibility handled via empty group card; no ghost sample insertion needed.

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
    enabledInstances.forEach(s => {
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
    // Locate a stable wrapper for insertion (the parent config cards container itself if no specific reference)
    let addButtonWrapper = null;
    const firstAddBtn = anchor.querySelector('.btn-add-special-sample');
    if (firstAddBtn) {
        // Use the parent config-card of the first add button so new type cards appear before it for consistency
        const parentCard = firstAddBtn.closest('.config-card');
        if (parentCard) addButtonWrapper = parentCard; 
    }
    console.log('[SpecialSamples] insertion reference card:', addButtonWrapper ? addButtonWrapper.id : 'none');

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
                        ${group.samples.length ? group.samples.map(sample => specialSampleItemHTMLForGroup(sample)).join('') : '<div class="no-special-samples" style="padding:6px 8px;color:var(--gray-med);font-size:11px;">No samples of this type enabled</div>'}
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

function specialSampleItemHTMLForGroup(sample) {
    const sampleId = sample.ssid || sample.stid;
    const instanceIndex = sample.__instanceIndex;
    const displayName = sample.special_name || sample.name || `Sample ${sampleId}`;
    const sampleTypeId = sample.special_type || sample.type_id || sample.sstid || 0;
    const baseTypeName = sample.special_type_name || sample.type || 'Type';
    let placementSummary = '';
    const cfg = specialSampleInstanceConfigs[instanceIndex] || specialSampleConfigs[sampleId];
    if (cfg) {
        if (cfg.placement === 'specific_well') placementSummary = `Well ${cfg.specificWell || 'A1'}`;
        else if (cfg.placement === 'after_samples') placementSummary = `After +${cfg.afterSamplesCount || 1}`;
        else if (cfg.placement === 'script_placed') placementSummary = 'Script placed';
    }
    const displayType = (sampleTypeId === 4 && placementSummary) ? placementSummary : baseTypeName;
    const hasConfig = !!(cfg && Object.keys(cfg).length > 0);
    const gearIcon = hasConfig ? 'fas fa-cog' : 'far fa-cog';
    const buttonTitle = hasConfig ? 'Sample configured - click to edit' : 'Configure special sample';
    return `
        <div class="special-sample-item" data-sample-id="${sampleId}" data-sample-type="${sampleTypeId}" data-instance-index="${instanceIndex}" draggable="false">
            <div class="special-sample-drag-handle" style="cursor:default;">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="special-sample-info">
                <div class="special-sample-name">${displayName}</div>
                <div class="special-sample-type">${displayType}</div>
            </div>
            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModalByInstance(${instanceIndex})" title="${buttonTitle}"><i class="${gearIcon}"></i></button>
        </div>`;
}

function createSpecialSampleItemHTML(sample, index) {
    const sampleId = sample.ssid || sample.stid; // prefer modern ssid
    const displayName = sample.special_name || sample.name || `Sample ${sampleId}`;
    const sampleTypeId = sample.special_type || sample.type_id || sample.sstid || 0;
    const baseTypeName = sample.special_type_name || sample.type || 'Type';
    let placementSummary = '';
    const cfg = specialSampleInstanceConfigs[index] || specialSampleConfigs[sampleId];
    if (cfg) {
        if (cfg.placement === 'specific_well') placementSummary = `Well ${cfg.specificWell || 'A1'}`;
        else if (cfg.placement === 'after_samples') placementSummary = `After +${cfg.afterSamplesCount || 1}`;
        else if (cfg.placement === 'script_placed') placementSummary = 'Script placed';
    }
    const displayType = (sampleTypeId === 4 && placementSummary) ? placementSummary : baseTypeName;
    const hasConfig = !!(cfg && Object.keys(cfg).length > 0);
    const gearIcon = hasConfig ? 'fas fa-cog' : 'far fa-cog';
    const buttonTitle = hasConfig ? 'Sample configured - click to edit' : 'Configure special sample';
    return `
        <div class="special-sample-item" data-sample-id="${sampleId}" data-sample-type="${sampleTypeId}" data-instance-index="${index}" draggable="true">
            <div class="special-sample-drag-handle"><i class="fas fa-grip-vertical"></i></div>
            <div class="special-sample-info">
                <div class="special-sample-name">${displayName}</div>
                <div class="special-sample-type">${displayType}</div>
            </div>
            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModalByInstance(${index})" title="${buttonTitle}"><i class="${gearIcon}"></i></button>
        </div>`;
}

function enableSpecialSampleDragAndDrop() { /* No drag-drop for grouped view */ }

function handleSpecialSampleDragStart(e) {
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
}
    function showSpecialSampleConfigModalByInstance(instanceIndex) {
        const item = document.querySelector(`.special-sample-item[data-instance-index="${instanceIndex}"]`);
        if (!item) return;
        const sampleId = parseInt(item.dataset.sampleId);
        currentConfigInstanceIndex = instanceIndex;
        currentConfigSampleId = sampleId;
        const sampleObj = specialSampleTypesDataAll.find(s => (s.ssid === sampleId) || (s.stid === sampleId));
        const typeId = sampleObj ? (sampleObj.special_type || sampleObj.type_id || sampleObj.sstid || 0) : 0;
        const specificId = `specialSampleConfigModal_type${typeId}`;
        currentConfigModalEl = document.getElementById(specificId) || document.getElementById('specialSampleConfigModal_generic');
        if (!currentConfigModalEl) return;
        const sampleName = item.querySelector('.special-sample-name')?.textContent || sampleObj?.special_name || sampleObj?.name || 'Special Sample';
        currentConfigModalEl.querySelectorAll('.configSampleName').forEach(el => el.textContent = sampleName);
        const existingConfig = specialSampleInstanceConfigs[instanceIndex] || { count:1, createForEach:'step', autoAdd:false, placement:'user_placed', specificWell:'A1', afterSamplesCount:1 };
        const setVal = (sel, val, prop='value') => { const el = currentConfigModalEl.querySelector(sel); if (el && val !== undefined) el[prop] = val; };
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
    // Build from current global arrays (already preserve order & duplicates)
    const data = { enabled_ids: specialSampleEnabledIds.slice(), configurations: {} };
    specialSampleInstanceConfigs.forEach((cfg, idx) => {
        if (cfg && Object.keys(cfg).length > 0) data.configurations[idx] = cfg;
    });
    console.log('Getting special samples data for step config (index-keyed):', data);
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
    function hideSpecialSampleConfigModal() {
        if (currentConfigModalEl) currentConfigModalEl.style.display = 'none';
        currentConfigSampleId = null;
        currentConfigSampleType = null;
        currentConfigInstanceIndex = null;
        currentConfigModalEl = null;
    }
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
    // Update header label
    const labelEl = document.getElementById('specialSampleTypeLabel');
    if (labelEl) {
        const rep = specialSampleTypesDataAll.find(s => (s.special_type || s.type_id || s.sstid || 0) === typeId);
        labelEl.textContent = rep ? (rep.special_type_name || rep.type || 'Special Sample') : 'Special Sample';
    }
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
        const checkHtml = isEnabled ? '<div style="margin-left:auto;color:var(--green-med);"><i class="fas fa-check"></i></div>' : '';
        const clickAttr = (sample.unique_only && isEnabled) ? '' : `onclick="addSpecialSample(${sampleId})"`;
        html += `
            <div class="available-special-sample ${disabledClass}" ${clickAttr} title="${title}">
                <div class="special-sample-info">
                    <div class="special-sample-name">${sample.special_name || sample.name}</div>
                    <div class="special-sample-type">${sample.special_type_name || sample.type}</div>
                </div>
                ${checkHtml}
            </div>`;
    });
    if (!html) {
        listDiv.innerHTML = '<div style="text-align:center;padding:18px;color:var(--gray-med);font-size:12px;">All samples of this type have been added</div>';
    } else {
        listDiv.innerHTML = html;
    }

}

function addSpecialSample(sampleId) {
    console.log('[SpecialSamples] addSpecialSample invoked with id:', sampleId);
    const sample = specialSampleTypesDataAll.find(s => s.ssid === sampleId || s.stid === sampleId);
    if (!sample) return;
    // If sample marked unique_only, prevent more than one visible instance
    const existingEl = document.querySelector(`#assayConfigCards .special-sample-item[data-sample-id="${sampleId}"]`);
    if (sample.unique_only && existingEl) {
        console.log('[SpecialSamples] Unique-only sample already present; abort');
        return;
    }
    // unique_only now interpreted as: this specific sample can only be added once (duplicates blocked by earlier check)
    // (Multiple different samples of same type still allowed.)
    // Build current enabled list (excluding placeholders if any logic later)
    console.log('[SpecialSamples] existing enabled before add:', specialSampleEnabledIds);
    specialSampleEnabledIds.push(sampleId);
    specialSampleInstanceConfigs.push(null);
    loadSpecialSamplesInterface({ enabled_ids: specialSampleEnabledIds });
    console.log('[SpecialSamples] After add, enabled ids ->', specialSampleEnabledIds);
    // Fallback: if after rebuild the item still not present, append manually to its group
    setTimeout(() => {
        if (!document.querySelector(`#assayConfigCards .special-sample-item[data-sample-id="${sampleId}"]`)) {
            console.warn('[SpecialSamples] Rebuild did not insert sample, performing manual append');
            const typeId = sample.special_type || sample.type_id || sample.sstid || 0;
            let groupList = document.getElementById(`specialSampleGroup_${typeId}`);
            if (!groupList) {
                // create minimal card for this type
                const anchor = document.getElementById('assayConfigCards');
                if (anchor) {
                    const cardId = `specialSampleTypeCard_${typeId}`;
                    anchor.insertAdjacentHTML('beforeend', `<div class="config-card" id="${cardId}" data-sample-type-group="${typeId}"><div class="special-samples-config-panel"><div class="special-samples-config-header"><span>Enabled ${sample.special_type_name || sample.type || 'Type '+typeId}</span><button type="button" class="btn-add-special-sample" onclick="showSpecialSampleSelectorForType(${typeId})"><i class=\"fas fa-plus\"></i> Add</button></div><div class="enabled-special-samples" id="specialSampleGroup_${typeId}"></div></div></div>`);
                    groupList = document.getElementById(`specialSampleGroup_${typeId}`);
                }
            }
            if (groupList) {
                groupList.insertAdjacentHTML('beforeend', specialSampleItemHTMLForGroup(sample, groupList.querySelectorAll('.special-sample-item').length));
                updateSpecialSamplesFromDOM();
            }
        }
    }, 0);
    renderAvailableSpecialSamples();
    hideSpecialSampleSelector();
}

// Ensure function accessible for inline onclick handlers
window.addSpecialSample = addSpecialSample;
window.showSpecialSampleConfigModalByInstance = showSpecialSampleConfigModalByInstance;

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
    // Rebuild arrays from DOM order after removal
    const items = Array.from(document.querySelectorAll('#assayConfigCards .special-sample-item'));
    specialSampleEnabledIds = items.map(i => parseInt(i.dataset.sampleId));
    // Reindex instance configs aligning to new order (drop configs for removed instance)
    const newConfigs = [];
    items.forEach((el, idx) => {
        const oldIndex = parseInt(el.dataset.instanceIndex);
        newConfigs[idx] = specialSampleInstanceConfigs[oldIndex] || null;
        el.dataset.instanceIndex = idx; // update DOM index attribute
    });
    specialSampleInstanceConfigs = newConfigs;
    updateSpecialSamplesFromDOM();
    renderAvailableSpecialSamples();
    if (!document.querySelector('#assayConfigCards .special-sample-item')) {
        document.getElementById('assayConfigCards').innerHTML += '<div class="no-special-samples">No special samples configured</div>';
    }
}

// Legacy modal functions removed; instance-based versions defined earlier.

function handlePlacementDetailDisplay(placement, modalEl) {
    const specific = modalEl.querySelector('.specificWellDetail');
    const after = modalEl.querySelector('.afterSamplesDetail');
    if (specific) specific.style.display = (placement === 'specific_well') ? 'flex' : 'none';
    if (after) after.style.display = (placement === 'after_samples') ? 'flex' : 'none';
}
