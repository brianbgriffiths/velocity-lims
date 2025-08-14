function saveAll() {
    const versionName = document.getElementById('versionName').value.trim();
    
    if (!versionName) {
        pylims_ui.error('Version name is required');
        return;
    }
    
    let versionChanged = false;
    let stepChanged = false;
    
    // First, save version name if it has changed
    saveVersionName().then((versionResult) => {
        versionChanged = versionResult && versionResult.status === 'success' && !versionResult.version_unchanged;
        
        // Then save step configuration if a step is selected
        if (selectedStepId) {
            return saveStepConfiguration(true); // Pass true to indicate this is part of unified save
        }
        return Promise.resolve({ status: 'success', config_unchanged: true });
    }).then((stepResult) => {
        stepChanged = stepResult && stepResult.status === 'success' && !stepResult.config_unchanged;
        
        // Show appropriate success message
        if (versionChanged || stepChanged) {
            if (versionChanged && stepChanged) {
                pylims_ui.success('Version name and step configuration saved successfully');
            } else if (versionChanged) {
                pylims_ui.success('Version name saved successfully');
            } else if (stepChanged) {
                pylims_ui.success('Step configuration saved successfully');
            }
        } else {
            pylims_ui.success('No changes detected');
        }
        
        console.log('All changes saved successfully');
    }).catch(error => {
        console.error('Error saving changes:', error);
        pylims_ui.error('Failed to save changes');
    });
}

function saveVersionName() {
    const versionName = document.getElementById('versionName').value.trim();
    
    const pyoptions = {
        data: {
            avid: avid,
            version_name: versionName
        },
        csrf: csrf,
        url: 'save_version_name',
        submit_mode: 'silent'
    };
    
    return pylims_post(pyoptions).then(result => {
        if (result.status === 'success') {
            if (result.version_unchanged) {
                console.log('Version name unchanged, no version increment');
                // Still update display to ensure consistency (in case of display drift)
                if (result.version) {
                    updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
                }
            } else {
                console.log('Version name saved successfully, version incremented');
                // Update version display with new patch version
                if (result.version) {
                    updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
                }
            }
        }
        return result;
    });
}

function updateVersionDisplay(major, minor, patch) {
    const versionBadge = document.querySelector('.version-badge');
    if (versionBadge) {
        // Extract the current status from the badge text
        const currentText = versionBadge.innerHTML;
        const statusMatch = currentText.match(/\((.*?)\)$/);
        const status = statusMatch ? statusMatch[1] : 'Draft';
        
        // Update the text content while preserving any HTML structure
        const newVersionText = `v${major}.${minor}.${patch} (${status})`;
        
        // If there are child nodes, update the text node
        if (versionBadge.childNodes.length > 0) {
            // Find and update the text node
            for (let i = 0; i < versionBadge.childNodes.length; i++) {
                if (versionBadge.childNodes[i].nodeType === Node.TEXT_NODE) {
                    versionBadge.childNodes[i].nodeValue = newVersionText;
                    break;
                }
            }
            // If no text node found, replace all content
            if (!Array.from(versionBadge.childNodes).some(node => node.nodeType === Node.TEXT_NODE)) {
                versionBadge.textContent = newVersionText;
            }
        } else {
            versionBadge.textContent = newVersionText;
        }
        
        console.log(`Version display updated to: ${newVersionText}`);
    } else {
        console.warn('Version badge element not found');
    }
}

function toggleStepOrder() {
    isReorderMode = !isReorderMode;
    const toggle = document.getElementById('stepOrderToggle');
    const lockIcon = document.getElementById('lockIcon');
    const lockText = document.getElementById('lockText');
    const stepsList = document.getElementById('stepsList');
    
    if (isReorderMode) {
        // Unlock mode - enable drag and drop
        toggle.classList.add('unlocked');
        lockIcon.className = 'fas fa-unlock';
        lockText.textContent = 'STEP ORDER';
        stepsList.classList.add('reorder-mode');
        enableDragAndDrop();
    } else {
        // Lock mode - disable drag and drop
        toggle.classList.remove('unlocked');
        lockIcon.className = 'fas fa-lock';
        lockText.textContent = 'STEP ORDER';
        stepsList.classList.remove('reorder-mode');
        disableDragAndDrop();
    }
}

function enableDragAndDrop() {
    const stepItems = document.querySelectorAll('.step-item');
    stepItems.forEach(item => {
        item.draggable = true;
        item.addEventListener('dragstart', handleDragStart);
        item.addEventListener('dragover', handleDragOver);
        item.addEventListener('drop', handleDrop);
        item.addEventListener('dragend', handleDragEnd);
    });
}

function disableDragAndDrop() {
    const stepItems = document.querySelectorAll('.step-item');
    stepItems.forEach(item => {
        item.draggable = false;
        item.removeEventListener('dragstart', handleDragStart);
        item.removeEventListener('dragover', handleDragOver);
        item.removeEventListener('drop', handleDrop);
        item.removeEventListener('dragend', handleDragEnd);
    });
}

function handleDragStart(e) {
    if (!isReorderMode) return;
    
    draggedElement = e.target;
    e.target.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.outerHTML);
}

function handleDragOver(e) {
    if (!isReorderMode) return;
    
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const afterElement = getDragAfterElement(e.currentTarget.parentNode, e.clientY);
    const stepsList = document.getElementById('stepsList');
    
    if (afterElement == null) {
        stepsList.appendChild(draggedElement);
    } else {
        stepsList.insertBefore(draggedElement, afterElement);
    }
}

function handleDrop(e) {
    if (!isReorderMode) return;
    
    e.preventDefault();
    e.stopPropagation();
    
    // Save the new order
    saveStepOrder();
    
    return false;
}

function handleDragEnd(e) {
    if (!isReorderMode) return;
    
    e.target.classList.remove('dragging');
    draggedElement = null;
    
    // Update step numbers
    updateStepNumbers();
}

function getDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.step-item:not(.dragging)')];
    
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

function updateStepNumbers() {
    const stepItems = document.querySelectorAll('#stepsList .step-item');
    stepItems.forEach((item, index) => {
        const orderElement = item.querySelector('.step-order');
        if (orderElement) {
            orderElement.textContent = index + 1;
        }
    });
}

function saveStepOrder() {
    const stepItems = document.querySelectorAll('#stepsList .step-item');
    const stepOrder = Array.from(stepItems).map(item => parseInt(item.dataset.stepId));
    
    const pyoptions = {
        data: {
            assay_id: assayId,
            step_order: stepOrder
        },
        csrf: csrf,
        url: 'save_step_order',
        submit_mode: 'silent'
    };
    
    pylims_post(pyoptions).then(result => {
        if (result.status === 'success') {
            if (result.version_unchanged) {
                console.log('Step order unchanged, no version increment');
                // Still update display to ensure consistency (in case of display drift)
                if (result.version) {
                    updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
                }
            } else {
                console.log('Step order saved successfully, version incremented');
                // Update version display with new patch version
                if (result.version) {
                    updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
                }
            }
        }
    }).catch(error => {
        console.error('Save step order error:', error);
        pylims_ui.error('Failed to save step order');
    });
}

function selectStep(stepId, stepName) {
    // Don't select steps when in reorder mode
    if (isReorderMode) return;
    
    selectedStepId = stepId;
    
    // Update active state
    document.querySelectorAll('.step-item').forEach(item => {
        item.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    
    // Hide placeholder and show config panel
    document.getElementById('stepPlaceholder').style.display = 'none';
    document.getElementById('stepConfigPanel').style.display = 'block';
    
    // Update config panel content
    document.getElementById('stepConfigTitle').textContent = `Configure: ${stepName}`;
    
    console.log('Selected step:', stepId, stepName);
    
    // Load step configuration
    loadStepConfiguration(stepId);
}

function loadStepConfiguration(stepId) {
    // Ensure special sample types are initialized first
    if (specialSampleTypes.length === 0) {
        initializeSpecialSampleTypes();
    }
    loadStepConfigurationData(stepId);
}

function loadStepConfigurationData(stepId) {
    const pyoptions = {
        data: {
            scid: stepId
        },
        csrf: csrf,
        url: 'get_step_config',
        submit_mode: 'silent'
    };
    
    pylims_post(pyoptions).then(result => {
        if (result.status === 'success') {
            const config = result.step_config;
            
            console.log('Raw step configuration from API:', config);
            console.log('Containers in step config:', config.containers);
            console.log('Special samples in step config:', config.special_samples);
            
            // Populate form fields
            document.getElementById('stepName').value = config.step_name || '';
            document.getElementById('createSamples').checked = config.create_samples === 1;
            
            // Populate JSON fields with proper formatting
            document.getElementById('pagesConfig').value = JSON.stringify(config.pages || [], null, 2);
            document.getElementById('sampleDataConfig').value = JSON.stringify(config.sample_data || [], null, 2);
            document.getElementById('stepScriptsConfig').value = JSON.stringify(config.step_scripts || [], null, 2);
            
            // Load containers into visual interface
            loadContainersInterface(config.containers || []);
            
            // Load special samples into visual interfaces
            loadSpecialSamplesInterface(config.special_samples || []);
            
            // Load special sample configurations
            if (config.special_sample_config) {
                specialSampleConfigs = config.special_sample_config;
                // Update visual indicators for configured samples
                Object.keys(specialSampleConfigs).forEach(sampleId => {
                    const sampleItem = document.querySelector(`[data-sample-id="${sampleId}"]`);
                    if (sampleItem) {
                        const configButton = sampleItem.querySelector('.special-sample-config-button');
                        if (configButton) {
                            configButton.style.backgroundColor = 'var(--green-med)';
                            configButton.title = 'Sample configured - click to edit';
                        }
                    }
                });
            }
            
            console.log('Step configuration loaded:', config);
        }
    }).catch(error => {
        console.error('Load step config error:', error);
        pylims_ui.error('Failed to load step configuration');
    });
}

function saveStepConfiguration(isUnifiedSave = false) {
    if (!selectedStepId) {
        console.log('No step selected, skipping step configuration save');
        return Promise.resolve({ status: 'success', config_unchanged: true });
    }
    
    const stepName = document.getElementById('stepName').value.trim();
    
    if (!stepName) {
        const errorMsg = 'Step name is required';
        if (!isUnifiedSave) {
            pylims_ui.error(errorMsg);
        }
        return Promise.reject(new Error(errorMsg));
    }
    
    try {
        // Get containers from visual interface
        const containers = getContainersFromInterface();
        console.log('Containers being sent to backend:', containers);
        
        // Get special samples from visual interfaces (new format matching containers)
        const specialSamples = getSpecialSamplesFromInterface();
        
        // Parse other JSON fields
        const pages = JSON.parse(document.getElementById('pagesConfig').value || '[]');
        const sampleData = JSON.parse(document.getElementById('sampleDataConfig').value || '[]');
        const stepScripts = JSON.parse(document.getElementById('stepScriptsConfig').value || '[]');
        
        const pyoptions = {
            data: {
                scid: selectedStepId,
                step_name: stepName,
                containers: containers,
                special_samples: specialSamples,
                create_samples: document.getElementById('createSamples').checked ? 1 : 0,
                pages: pages,
                sample_data: sampleData,
                step_scripts: stepScripts
            },
            csrf: csrf,
            url: 'save_step_config',
            submit_mode: 'silent'
        };
        
        return pylims_post(pyoptions).then(result => {
            if (result.status === 'success') {
                if (result.config_unchanged) {
                    console.log('Step configuration unchanged, no version increment');
                    // Still update display to ensure consistency (in case of display drift)
                    if (result.version) {
                        updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
                    }
                } else {
                    console.log('Step configuration saved successfully, version incremented');
                    
                    // Update step name in the left panel if it changed
                    const stepItem = document.querySelector(`[data-step-id="${selectedStepId}"]`);
                    if (stepItem) {
                        const stepNameElement = stepItem.querySelector('.step-name');
                        if (stepNameElement) {
                            stepNameElement.textContent = stepName;
                        }
                    }
                    
                    // Update version display with new patch version if available
                    if (result.version) {
                        updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
                    }
                }
                
                // Only show success message if this is not part of unified save
                if (!isUnifiedSave) {
                    if (result.config_unchanged) {
                        pylims_ui.success('Step configuration unchanged');
                    } else {
                        pylims_ui.success(result.message || 'Step configuration saved successfully');
                    }
                }
            }
            return result;
        });
        
    } catch (e) {
        const errorMsg = 'Invalid JSON in configuration fields: ' + e.message;
        if (!isUnifiedSave) {
            pylims_ui.error(errorMsg);
        }
        return Promise.reject(e);
    }
}

function addNewStep() {
    console.log('Adding new step to assay:', assayId);
    // TODO: Implement add new step functionality
    pylims_ui.error('Add new step functionality will be implemented later');
}

// Container Management Functions
let availableContainers = [];
let enabledContainerIds = new Set();

// Special Samples Management Functions
let availableSpecialSamples = [];
let enabledSpecialSampleIds = {}; // Will be populated dynamically based on loaded types
let currentSpecialSampleType = null;
let specialSampleTypes = specialSampleTypesData || []; // Use data from server
let specialSampleTypeNames = {}; // Will be populated from server data

// Initialize special sample types data on page load
function initializeSpecialSampleTypes() {
    console.log('initializeSpecialSampleTypes called');
    console.log('specialSampleTypesData from Django:', specialSampleTypesData);
    console.log('specialSampleTypes variable:', specialSampleTypes);
    
    if (!specialSampleTypes || specialSampleTypes.length === 0) {
        console.warn('No special sample types found to initialize');
        return;
    }
    
    // Populate type names and initialize enabled IDs tracking
    specialSampleTypes.forEach(type => {
        specialSampleTypeNames[type.sstid] = type.special_type_name;
        enabledSpecialSampleIds[type.sstid] = new Set();
    });
    
    console.log('Initialized special sample types:', specialSampleTypes);
    console.log('Special sample type names:', specialSampleTypeNames);
    
    // Generate the special sample cards
    generateSpecialSampleCards();
}

function generateSpecialSampleCards() {
    const container = document.getElementById('configCardsContainer');
    if (!container) return;
    
    // Remove any existing special sample cards (but keep the containers card)
    const existingSpecialCards = container.querySelectorAll('.config-card:not(.config-card:first-child)');
    existingSpecialCards.forEach(card => card.remove());
    
    // Generate and append new special sample cards
    specialSampleTypes.forEach(type => {
        const typeName = type.special_type_name;
        const typeId = type.sstid;
        const containerId = `enabled_${typeId}`;
        
        const cardDiv = document.createElement('div');
        cardDiv.className = 'config-card';
        cardDiv.innerHTML = `
            <label class="form-label">${typeName} Configuration</label>
            <div class="special-samples-config-panel">
                <div class="special-samples-config-header">
                    <span>${typeName}</span>
                    <button type="button" class="btn-add-special-sample" onclick="showSpecialSampleSelector(${typeId})">
                        <i class="fas fa-plus"></i> Add
                    </button>
                </div>
                <div class="enabled-special-samples" id="${containerId}">
                    <div class="no-special-samples">No ${typeName.toLowerCase()} configured</div>
                </div>
            </div>
        `;
        
        container.appendChild(cardDiv);
    });
    
    console.log('Generated special sample cards for types:', specialSampleTypes);
}

function loadSpecialSamplesInterface(specialSamplesData) {
    console.log('loadSpecialSamplesInterface called with:', specialSamplesData);
    console.log('specialSamplesData type:', typeof specialSamplesData);
    
    // Clear all special sample containers
    specialSampleTypes.forEach(type => {
        const containerId = `enabled_${type.sstid}`;
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = `<div class="no-special-samples">No ${type.special_type_name.toLowerCase()} configured</div>`;
        }
    });
    
    // Clear tracking sets
    Object.keys(enabledSpecialSampleIds).forEach(typeId => {
        enabledSpecialSampleIds[typeId].clear();
    });
    
    // Check if data is null, undefined, or empty
    if (!specialSamplesData || 
        (typeof specialSamplesData === 'object' && Object.keys(specialSamplesData).length === 0)) {
        return;
    }
    
    // Handle new format: {enabled_ids: [1,2,3], configurations: {1: {special_type: 1}, 2: {special_type: 2}}}
    if (specialSamplesData.enabled_ids && specialSamplesData.configurations) {
        console.log('Processing special samples in new format');
        
        specialSamplesData.enabled_ids.forEach(sampleId => {
            const config = specialSamplesData.configurations[sampleId];
            if (!config || !config.special_type) return;
            
            const specialType = config.special_type;
            const sample = availableSpecialSamples.find(s => s.ssid === sampleId);
            
            if (sample) {
                const containerId = `enabled_${specialType}`;
                const container = document.getElementById(containerId);
                
                if (container) {
                    // Remove "no samples" message if present
                    const noSamplesDiv = container.querySelector('.no-special-samples');
                    if (noSamplesDiv) {
                        container.innerHTML = '';
                    }
                    
                    // Create and add sample item
                    const sampleElement = createSpecialSampleItemHTML(sample, specialType);
                    container.appendChild(sampleElement);
                    
                    // Update tracking
                    enabledSpecialSampleIds[specialType].add(sampleId);
                }
            }
        });
        return;
    }
    
    // Legacy handling for old format (organized by type or array)
    if (typeof specialSamplesData === 'object' && !Array.isArray(specialSamplesData)) {
        // Process each type in the organized structure
        Object.keys(specialSamplesData).forEach(typeId => {
            const typeIdInt = parseInt(typeId);
            const samplesForType = specialSamplesData[typeId];
            
            if (Array.isArray(samplesForType) && samplesForType.length > 0) {
                const containerId = `enabled_${typeId}`;
                loadSpecialSamplesForType(typeIdInt, samplesForType, containerId);
                
                // Update tracking sets
                samplesForType.forEach(sample => {
                    enabledSpecialSampleIds[typeIdInt].add(sample.ssid);
                    
                    // Ensure these samples are in our availableSpecialSamples list
                    if (!availableSpecialSamples.find(s => s.ssid === sample.ssid)) {
                        availableSpecialSamples.push(sample);
                    }
                });
            }
        });
        return;
    }
    
    // Legacy handling: if specialSamples is still an array (fallback)
    if (Array.isArray(specialSamplesData)) {
        // Group special samples by type
        const samplesByType = {};
        specialSampleTypes.forEach(type => {
            samplesByType[type.sstid] = [];
        });
        
        specialSamplesData.forEach(sample => {
            const type = sample.special_type || sample.type_id;
            if (samplesByType[type]) {
                samplesByType[type].push(sample);
                enabledSpecialSampleIds[type].add(sample.ssid);
            }
        });
        
        // Load each type into its respective container
        specialSampleTypes.forEach(type => {
            const containerId = `enabled_${type.sstid}`;
            loadSpecialSamplesForType(type.sstid, samplesByType[type.sstid], containerId);
        });
        
        // Ensure these samples are in our availableSpecialSamples list
        specialSamplesData.forEach(sample => {
            if (!availableSpecialSamples.find(s => s.ssid === sample.ssid)) {
                availableSpecialSamples.push(sample);
            }
        });
    }
}

function loadSpecialSamplesForType(type, samples, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !samples || samples.length === 0) {
        return;
    }
    
    let html = '';
    samples.forEach((sample, index) => {
        html += createSpecialSampleItemHTML(sample, type, index);
    });
    
    container.innerHTML = html;
    enableSpecialSampleDragAndDrop(containerId);
}

function createSpecialSampleItemHTML(sample, type, index) {
    const sampleName = sample.special_name || 'Unknown Sample';
    const partNumber = sample.part_number || '';
    const ssid = sample.ssid;
    
    console.log('Creating special sample item:', { sample, sampleName, partNumber, ssid, type });
    
    return `
        <div class="special-sample-item" data-sample-id="${ssid}" data-sample-type="${type}" draggable="true">
            <div class="special-sample-drag-handle">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="special-sample-info">
                <div class="special-sample-name">${sampleName}</div>
                <div class="special-sample-details">${partNumber ? 'Part: ' + partNumber : 'No part number'}</div>
            </div>
            <button type="button" class="special-sample-config-button" onclick="showSpecialSampleConfigModal(${ssid}, '${sampleName}', ${type})" title="Configure sample">
                <i class="fas fa-cog"></i>
            </button>
        </div>
    `;
}

function enableSpecialSampleDragAndDrop(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const sampleItems = container.querySelectorAll('.special-sample-item');
    
    sampleItems.forEach(item => {
        item.addEventListener('dragstart', handleSpecialSampleDragStart);
        item.addEventListener('dragover', handleSpecialSampleDragOver);
        item.addEventListener('drop', handleSpecialSampleDrop);
        item.addEventListener('dragend', handleSpecialSampleDragEnd);
    });
}

function handleSpecialSampleDragStart(e) {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.outerHTML);
    e.target.classList.add('dragging');
    draggedElement = e.target;
}

function handleSpecialSampleDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const afterElement = getSpecialSampleDragAfterElement(e.currentTarget.parentNode, e.clientY);
    const container = e.currentTarget.parentNode;
    
    if (afterElement == null) {
        container.appendChild(draggedElement);
    } else {
        container.insertBefore(draggedElement, afterElement);
    }
}

function handleSpecialSampleDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Update the special samples array based on new order
    updateSpecialSamplesFromDOM();
    
    return false;
}

function handleSpecialSampleDragEnd(e) {
    e.target.classList.remove('dragging');
    draggedElement = null;
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

function getSpecialSamplesFromInterface() {
    const enabledIds = [];
    const configurations = {};
    
    // Get samples from each type container
    specialSampleTypes.forEach(type => {
        const containerId = `enabled_${type.sstid}`;
        const container = document.getElementById(containerId);
        if (!container) return;
        
        const sampleItems = container.querySelectorAll('.special-sample-item');
        sampleItems.forEach(item => {
            const sampleId = parseInt(item.dataset.sampleId);
            const sampleType = parseInt(item.dataset.sampleType);
            
            // Add to enabled IDs list
            enabledIds.push(sampleId);
            
            // Create configuration for this sample
            configurations[sampleId] = {
                special_type: sampleType,
                // Add any other configuration options here as needed
            };
        });
    });
    
    const result = {
        enabled_ids: enabledIds,
        configurations: configurations
    };
    
    console.log('Getting special samples from interface (new format):', result);
    return result;
}

function updateSpecialSamplesFromDOM() {
    // This function could be used to maintain order if needed
    console.log('Special samples order updated');
}

function showSpecialSampleSelector(type) {
    currentSpecialSampleType = type;
    const modal = document.getElementById('specialSampleSelectorModal');
    const typeLabel = document.getElementById('specialSampleTypeLabel');
    
    typeLabel.textContent = specialSampleTypeNames[type];
    modal.style.display = 'flex';
    
    // Just render available special samples (they should already be loaded)
    renderAvailableSpecialSamples();
}

function hideSpecialSampleSelector() {
    const modal = document.getElementById('specialSampleSelectorModal');
    modal.style.display = 'none';
}

function loadAllAvailableSpecialSamples() {
    console.log('loadAllAvailableSpecialSamples called');
    console.log('specialSampleTypes:', specialSampleTypes);
    
    if (!specialSampleTypes || specialSampleTypes.length === 0) {
        console.warn('No special sample types available to load samples for');
        return;
    }
    
    // Load special samples for each type
    specialSampleTypes.forEach(type => {
        console.log(`Loading special samples for type: ${type.sstid} (${type.special_type_name})`);
        
        const pyoptions = {
            data: {
                special_type_id: type.sstid
            },
            csrf: csrf,
            url: 'get_special_samples',
            submit_mode: 'silent'
        };
        
        pylims_post(pyoptions).then(result => {
            console.log(`Special samples response for type ${type.sstid} (${type.special_type_name}):`, result);
            if (result.status === 'success') {
                const newSamples = result.special_samples || [];
                console.log(`New samples from API for type ${type.sstid}:`, newSamples);
                
                // Merge new samples with existing ones, avoiding duplicates
                newSamples.forEach(newSample => {
                    if (!availableSpecialSamples.find(existing => existing.ssid === newSample.ssid)) {
                        availableSpecialSamples.push(newSample);
                        console.log(`Added sample ${newSample.ssid} (${newSample.special_name}) to available samples`);
                    }
                });
                
                console.log(`Total available special samples after loading type ${type.sstid}:`, availableSpecialSamples.length);
            } else {
                console.error(`Failed to load special samples for type ${type.sstid}:`, result);
            }
        }).catch(error => {
            console.error(`Error loading special samples for type ${type.sstid}:`, error);
        });
    });
}

function renderAvailableSpecialSamples() {
    const listDiv = document.getElementById('availableSpecialSamplesList');
    
    console.log('renderAvailableSpecialSamples called');
    console.log('availableSpecialSamples:', availableSpecialSamples);
    console.log('currentSpecialSampleType:', currentSpecialSampleType);
    console.log('enabledSpecialSampleIds:', enabledSpecialSampleIds);
    
    // Filter samples by current type
    const samplesForType = availableSpecialSamples.filter(sample => 
        sample.special_type === currentSpecialSampleType
    );
    
    console.log('samplesForType:', samplesForType);
    
    if (samplesForType.length === 0) {
        const typeName = specialSampleTypeNames[currentSpecialSampleType]?.toLowerCase() || 'samples';
        listDiv.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--gray-med);">No ${typeName} available</div>`;
        return;
    }
    
    let html = '';
    samplesForType.forEach(sample => {
        const sampleName = sample.special_name || 'Unknown Sample';
        const partNumber = sample.part_number || '';
        const ssid = sample.ssid;
        
        const isEnabled = enabledSpecialSampleIds[currentSpecialSampleType].has(ssid);
        const disabledClass = isEnabled ? 'disabled' : '';
        const title = isEnabled ? 'Sample already added' : 'Click to add this sample';
        
        console.log('Rendering special sample:', { sample, sampleName, partNumber, ssid, isEnabled });
        
        html += `
            <div class="available-container ${disabledClass}" 
                 onclick="${isEnabled ? '' : `addSpecialSample(${ssid})`}" 
                 title="${title}">
                <div class="container-preview" data-type="${currentSpecialSampleType}">
                    <i class="fas fa-vial"></i>
                </div>
                <div class="container-info">
                    <div class="container-name">${sampleName}</div>
                    <div class="container-details">${partNumber ? 'Part: ' + partNumber : 'No part number'}</div>
                </div>
                ${isEnabled ? '<div style="margin-left: auto; color: var(--green-med);"><i class="fas fa-check"></i></div>' : ''}
            </div>
        `;
    });
    
    listDiv.innerHTML = html;
}

function addSpecialSample(sampleId) {
    const sample = availableSpecialSamples.find(s => s.ssid === sampleId);
    if (!sample || enabledSpecialSampleIds[currentSpecialSampleType].has(sampleId)) {
        console.log('Sample not found or already enabled:', sampleId, sample);
        return;
    }
    
    console.log('Adding special sample:', sample);
    enabledSpecialSampleIds[currentSpecialSampleType].add(sampleId);
    
    // Find the container ID for this type
    const containerId = `enabled_${currentSpecialSampleType}`;
    const container = document.getElementById(containerId);
    
    if (!container) return;
    
    // Remove "no samples" message if present
    const noSamplesDiv = container.querySelector('.no-special-samples');
    if (noSamplesDiv) {
        container.innerHTML = '';
    }
    
    const sampleHTML = createSpecialSampleItemHTML(sample, currentSpecialSampleType, enabledSpecialSampleIds[currentSpecialSampleType].size - 1);
    container.insertAdjacentHTML('beforeend', sampleHTML);
    
    // Re-enable drag and drop
    enableSpecialSampleDragAndDrop(containerId);
    
    // Update the available samples display
    renderAvailableSpecialSamples();
    
    // Hide modal
    hideSpecialSampleSelector();
}

function removeSpecialSample(sampleId, type) {
    if (!enabledSpecialSampleIds[type].has(sampleId)) {
        return;
    }
    
    enabledSpecialSampleIds[type].delete(sampleId);
    
    // Remove configuration for this sample
    if (specialSampleConfigs[sampleId]) {
        delete specialSampleConfigs[sampleId];
        console.log(`Removed configuration for sample ID ${sampleId}`);
    }
    
    // Remove from DOM
    const sampleItem = document.querySelector(`[data-sample-id="${sampleId}"][data-sample-type="${type}"]`);
    if (sampleItem) {
        sampleItem.remove();
    }
    
    // Check if no samples remain for this type
    const containerId = `enabled_${type}`;
    const container = document.getElementById(containerId);
    if (container && enabledSpecialSampleIds[type].size === 0) {
        const typeName = specialSampleTypeNames[type]?.toLowerCase() || 'samples';
        container.innerHTML = `<div class="no-special-samples">No ${typeName} configured</div>`;
    }
}

function loadContainersInterface(containers) {
    const enabledContainersDiv = document.getElementById('enabledContainers');
    
    console.log('loadContainersInterface called with:', containers);
    console.log('Container count:', containers ? containers.length : 0);
    console.log('Container data type:', typeof containers);
    console.log('Is containers array?', Array.isArray(containers));
    
    if (!containers || containers.length === 0) {
        enabledContainersDiv.innerHTML = '<div class="no-containers">No containers configured for this step</div>';
        enabledContainerIds.clear();
        updateContainerConfigTextarea([]);
        // Clear container configurations
        window.containerConfigurations = {};
        return;
    }
    
    enabledContainerIds.clear();
    // Initialize or clear container configurations
    if (!window.containerConfigurations) {
        window.containerConfigurations = {};
    }
    
    let html = '';
    
    containers.forEach((container, index) => {
        console.log(`Processing container ${index}:`, container);
        console.log(`Container ${index} keys:`, Object.keys(container));
        
        let containerId;
        let fullContainer = null;
        
        // Handle different container formats:
        // 1. Legacy format: just integers [1, 2, 3]
        // 2. Simplified format: {cid: 1, config: {...}}
        // 3. Full container objects from database: {cid: 1, type_name: "...", rows: 8, ...}
        if (typeof container === 'number') {
            // Legacy format: just an integer
            containerId = container;
            console.log(`Legacy format container ID: ${containerId}`);
            // Find the full container details from availableContainers
            fullContainer = availableContainers.find(c => c.cid === containerId);
            console.log(`Found full container for legacy ID ${containerId}:`, fullContainer);
        } else if (container && container.cid) {
            // Object format with cid
            containerId = container.cid;
            console.log(`Object format container ID: ${containerId}`);
            
            // Check if this is a full container object (has type_name) or simplified (just cid + config)
            if (container.type_name) {
                // Full container object from backend
                fullContainer = container;
                console.log(`Using full container object for ID ${containerId}`);
                // Also add to availableContainers if not already there
                if (!availableContainers.find(c => c.cid === containerId)) {
                    availableContainers.push(container);
                }
            } else {
                // Simplified format, find full details in availableContainers
                fullContainer = availableContainers.find(c => c.cid === containerId);
                console.log(`Found full container for simplified ID ${containerId}:`, fullContainer);
            }
            
            // Load container configuration if it exists
            if (container.config) {
                window.containerConfigurations[containerId] = container.config;
                console.log(`Loaded config for container ${containerId}:`, container.config);
            }
        } else {
            console.warn('Unknown container format:', container);
            return;
        }
        
        if (!fullContainer) {
            console.warn(`Full container details not found for container ID ${containerId}`);
            console.warn(`Available containers:`, availableContainers);
            return;
        }
        
        console.log(`Adding container ID ${containerId} to enabled set`);
        enabledContainerIds.add(containerId);
        
        // Initialize empty config if none exists (for legacy data)
        if (!window.containerConfigurations[containerId]) {
            window.containerConfigurations[containerId] = {};
        }
        
        console.log(`Creating HTML for container ${containerId}`);
        html += createContainerItemHTML(fullContainer, index);
    });
    
    enabledContainersDiv.innerHTML = html;
    updateContainerConfigTextarea(containers);
    enableContainerDragAndDrop();
}

function createContainerItemHTML(container, index) {
    // Handle field names from the API based on actual database schema
    const typeName = container.type_name || 'Unknown Container';
    const rows = container.rows || 0;
    const columns = container.columns || 0;
    const cid = container.cid;
    const color = container.color || 1; // Default to color 1 if no color specified
    
    // Check if container has configuration
    const hasConfig = window.containerConfigurations && window.containerConfigurations[cid] && 
                     Object.keys(window.containerConfigurations[cid]).length > 1; // More than just container_id
    
    // Use thin gear for unconfigured, solid gear for configured
    const gearIcon = hasConfig ? 'fas fa-cog' : 'far fa-cog';
    const buttonTitle = hasConfig ? 'Container configured - click to edit' : 'Configure container';
    
    console.log('Creating container item:', { container, typeName, rows, columns, cid, color, hasConfig });
    
    return `
        <div class="container-item color-${color}" data-container-id="${cid}" draggable="true">
            <div class="container-drag-handle">
                <i class="fas fa-grip-vertical"></i>
            </div>
            <div class="container-info">
                <div class="container-name">${typeName}</div>
                <div class="container-details">${rows}×${columns} wells</div>
            </div>
            <button type="button" class="container-config-button" onclick="showContainerConfigModal(${cid}, '${typeName}')" title="${buttonTitle}">
                <i class="${gearIcon}"></i>
            </button>
        </div>
    `;
}

function enableContainerDragAndDrop() {
    const containerItems = document.querySelectorAll('.container-item');
    
    containerItems.forEach(item => {
        item.addEventListener('dragstart', handleContainerDragStart);
        item.addEventListener('dragover', handleContainerDragOver);
        item.addEventListener('drop', handleContainerDrop);
        item.addEventListener('dragend', handleContainerDragEnd);
    });
}

function handleContainerDragStart(e) {
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.outerHTML);
    e.target.classList.add('dragging');
    draggedElement = e.target;
}

function handleContainerDragOver(e) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    
    const afterElement = getContainerDragAfterElement(e.currentTarget.parentNode, e.clientY);
    const enabledContainers = document.getElementById('enabledContainers');
    
    if (afterElement == null) {
        enabledContainers.appendChild(draggedElement);
    } else {
        enabledContainers.insertBefore(draggedElement, afterElement);
    }
}

function handleContainerDrop(e) {
    e.preventDefault();
    e.stopPropagation();
    
    // Update the containers array based on new order
    updateContainersFromDOM();
    
    return false;
}

function handleContainerDragEnd(e) {
    e.target.classList.remove('dragging');
    draggedElement = null;
}

function getContainerDragAfterElement(container, y) {
    const draggableElements = [...container.querySelectorAll('.container-item:not(.dragging)')];
    
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

function updateContainersFromDOM() {
    const containerItems = document.querySelectorAll('.container-item');
    const containers = [];
    
    containerItems.forEach(item => {
        const containerId = parseInt(item.dataset.containerId);
        const container = availableContainers.find(c => c.cid === containerId);
        if (container) {
            containers.push(container);
        }
    });
    
    console.log('Updated containers from DOM:', containers);
    updateContainerConfigTextarea(containers);
}

function getContainersFromInterface() {
    // Return object with enabled container IDs and their configurations
    const containersData = {
        enabled_ids: Array.from(enabledContainerIds),
        configurations: {}
    };
    
    // Only include containers that have actual configuration
    enabledContainerIds.forEach(containerId => {
        if (window.containerConfigurations && window.containerConfigurations[containerId]) {
            const config = window.containerConfigurations[containerId];
            if (config && Object.keys(config).length > 0) {
                containersData.configurations[containerId] = config;
            }
        }
    });
    
    console.log('Getting containers data for step config:', containersData);
    return containersData;
}

function updateContainerConfigTextarea(containers) {
    document.getElementById('containerConfig').value = JSON.stringify(containers, null, 2);
}

function showContainerSelector() {
    const modal = document.getElementById('containerSelectorModal');
    modal.style.display = 'flex';
    
    // Just render available containers (they should already be loaded)
    renderAvailableContainers();
}

function hideContainerSelector() {
    const modal = document.getElementById('containerSelectorModal');
    modal.style.display = 'none';
}

function loadAvailableContainers() {
    console.log('loadAvailableContainers called');
    const pyoptions = {
        data: {},
        csrf: csrf,
        url: 'get_container_types',
        submit_mode: 'silent'
    };
    
    pylims_post(pyoptions).then(result => {
        console.log('Available containers response:', result);
        if (result.status === 'success') {
            const newContainers = result.container_types || [];
            console.log('New containers from API:', newContainers);
            
            // Merge new containers with existing ones, avoiding duplicates
            newContainers.forEach(newContainer => {
                if (!availableContainers.find(existing => existing.cid === newContainer.cid)) {
                    availableContainers.push(newContainer);
                }
            });
            
            console.log('Merged available containers:', availableContainers);
            renderAvailableContainers();
        }
    }).catch(error => {
        console.error('Error loading container types:', error);
        document.getElementById('availableContainersList').innerHTML = 
            '<div style="text-align: center; padding: 20px; color: var(--red-med);">Failed to load container types</div>';
    });
}

function renderAvailableContainers() {
    const listDiv = document.getElementById('availableContainersList');
    
    console.log('renderAvailableContainers called');
    console.log('availableContainers:', availableContainers);
    console.log('enabledContainerIds:', Array.from(enabledContainerIds));
    
    if (availableContainers.length === 0) {
        listDiv.innerHTML = '<div style="text-align: center; padding: 20px; color: var(--gray-med);">No container types available</div>';
        return;
    }
    
    let html = '';
    availableContainers.forEach(container => {
        // Handle field names from the API based on actual database schema
        const typeName = container.type_name || 'Unknown Container';
        const rows = container.rows || 0;
        const columns = container.columns || 0;
        const cid = container.cid;
        const color = container.color || 1; // Default to color 1 if no color specified
        
        const isEnabled = enabledContainerIds.has(cid);
        const disabledClass = isEnabled ? 'disabled' : '';
        const title = isEnabled ? 'Container already added' : 'Click to add this container';
        
        console.log('Rendering container:', { container, typeName, rows, columns, cid, color, isEnabled });
        
        html += `
            <div class="available-container ${disabledClass}" 
                 onclick="${isEnabled ? '' : `addContainer(${cid})`}" 
                 title="${title}">
                <div class="container-preview color-${color}">
                    ${rows}×${columns}
                </div>
                <div class="container-info">
                    <div class="container-name">${typeName}</div>
                    <div class="container-details">${rows}×${columns} wells</div>
                </div>
                ${isEnabled ? '<div style="margin-left: auto; color: var(--green-med);"><i class="fas fa-check"></i></div>' : ''}
            </div>
        `;
    });
    
    listDiv.innerHTML = html;
}

function addContainer(containerId) {
    const container = availableContainers.find(c => c.cid === containerId);
    if (!container || enabledContainerIds.has(containerId)) {
        console.log('Container not found or already enabled:', containerId, container);
        return;
    }
    
    console.log('Adding container:', container);
    enabledContainerIds.add(containerId);
    
    // Initialize empty configuration for the new container
    if (!window.containerConfigurations) {
        window.containerConfigurations = {};
    }
    if (!window.containerConfigurations[containerId]) {
        window.containerConfigurations[containerId] = {};
        console.log(`Initialized empty configuration for container ${containerId}`);
    }
    
    // Add to the enabled containers display
    const enabledContainersDiv = document.getElementById('enabledContainers');
    const noContainersDiv = enabledContainersDiv.querySelector('.no-containers');
    
    if (noContainersDiv) {
        enabledContainersDiv.innerHTML = '';
    }
    
    const containerHTML = createContainerItemHTML(container, enabledContainerIds.size - 1);
    enabledContainersDiv.insertAdjacentHTML('beforeend', containerHTML);
    
    // Re-enable drag and drop
    enableContainerDragAndDrop();
    
    // Update the containers array
    updateContainersFromDOM();
    
    // Update the available containers display
    renderAvailableContainers();
    
    // Hide modal
    hideContainerSelector();
}

function removeContainer(containerId) {
    if (!enabledContainerIds.has(containerId)) {
        return;
    }
    
    enabledContainerIds.delete(containerId);
    
    // Remove container configuration
    if (window.containerConfigurations && window.containerConfigurations[containerId]) {
        delete window.containerConfigurations[containerId];
        console.log(`Removed configuration for container ${containerId}`);
    }
    
    // Remove from DOM
    const containerItem = document.querySelector(`[data-container-id="${containerId}"]`);
    if (containerItem) {
        containerItem.remove();
    }
    
    // Check if no containers remain
    const enabledContainersDiv = document.getElementById('enabledContainers');
    if (enabledContainerIds.size === 0) {
        enabledContainersDiv.innerHTML = '<div class="no-containers">No containers configured for this step</div>';
    }
    
    // Update the containers array
    updateContainersFromDOM();
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    const containerModal = document.getElementById('containerSelectorModal');
    const specialSampleModal = document.getElementById('specialSampleSelectorModal');
    const configModal = document.getElementById('specialSampleConfigModal');
    
    if (e.target === containerModal) {
        hideContainerSelector();
    }
    
    if (e.target === specialSampleModal) {
        hideSpecialSampleSelector();
    }
    
    if (e.target === configModal) {
        hideSpecialSampleConfigModal();
    }
});

// Special Sample Configuration Modal Functions
let currentConfigSampleId = null;
let currentConfigSampleType = null;
let specialSampleConfigs = {}; // Store configurations by sample ID

function showSpecialSampleConfigModal(sampleId, sampleName, sampleType) {
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

// Add event listeners for placement radio buttons
document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('input[name="placement"]').forEach(radio => {
        radio.addEventListener('change', function() {
            updatePlacementDetails(this.value);
        });
    });
});

// Container Configuration Modal Functions
let currentContainerId = null;
let currentContainerName = null;

function showContainerConfigModal(containerId, containerName) {
    console.log('showContainerConfigModal called with:', containerId, containerName);
    
    currentContainerId = containerId;
    currentContainerName = containerName;
    
    // Check if modal exists
    const modal = document.getElementById('containerConfigModal');
    if (!modal) {
        console.error('Container config modal not found!');
        return;
    }
    
    // Update modal title
    const titleElement = document.getElementById('configContainerName');
    if (titleElement) {
        titleElement.textContent = containerName;
    } else {
        console.error('configContainerName element not found!');
    }
    
    // Load existing configuration
    try {
        loadContainerConfig(containerId);
    } catch (error) {
        console.error('Error loading container config:', error);
    }
    
    // Show modal using CSS class
    modal.classList.add('show');
    
    console.log('Modal show class added, should be visible now');
}


// Toggle functions for container config
function toggleRenameOptions() {
    const renameCheckbox = document.getElementById('renameContainer');
    const renameTextRow = document.getElementById('renameTextRow');
    
    if (renameCheckbox && renameTextRow) {
        renameTextRow.style.display = renameCheckbox.checked ? 'flex' : 'none';
        
        // Initialize token system when showing rename options
        if (renameCheckbox.checked) {
            initializeTokenSystem();
        }
    }
}

// Token system for container naming
function initializeTokenSystem() {
    const input = document.getElementById('containerNewName');
    const popup = document.getElementById('tokenPopup');
    
    if (!input || !popup) return;
    
    let selectedIndex = -1;
    let isPopupVisible = false;
    let cursorPosition = 0;
    
    // Handle input events
    input.addEventListener('input', function(e) {
        const value = this.value;
        cursorPosition = this.selectionStart;
        
        // Check if user typed opening brace
        if (value.charAt(cursorPosition - 1) === '{') {
            showTokenPopup();
        } else if (isPopupVisible && (value.charAt(cursorPosition - 1) === '}' || !value.includes('{'))) {
            hideTokenPopup();
        }
    });
    
    // Handle keydown for navigation and selection
    input.addEventListener('keydown', function(e) {
        if (!isPopupVisible) return;
        
        const options = popup.querySelectorAll('.token-option');
        
        switch(e.key) {
            case 'ArrowDown':
                e.preventDefault();
                selectedIndex = Math.min(selectedIndex + 1, options.length - 1);
                updateSelection();
                break;
            case 'ArrowUp':
                e.preventDefault();
                selectedIndex = Math.max(selectedIndex - 1, -1);
                updateSelection();
                break;
            case 'Enter':
            case 'Tab':
                e.preventDefault();
                handleTokenSelection();
                break;
            case 'Escape':
                hideTokenPopup();
                break;
        }
    });
    
    // Handle clicks outside to close popup
    document.addEventListener('click', function(e) {
        if (!input.contains(e.target) && !popup.contains(e.target)) {
            hideTokenPopup();
        }
    });
    
    // Handle token option clicks
    popup.addEventListener('click', function(e) {
        const option = e.target.closest('.token-option');
        if (option) {
            const token = option.dataset.token;
            
            // Handle special tokens with selects
            if (token === 'container_value') {
                const select = option.querySelector('#containerValueSelect');
                if (select.value) {
                    insertToken(`container_value:${select.value}`);
                } else {
                    // Show message or highlight select
                    select.focus();
                    select.style.borderColor = 'var(--red-med)';
                    setTimeout(() => {
                        select.style.borderColor = 'var(--gray-med)';
                    }, 1500);
                }
            } else if (token === 'batch_value') {
                const select = option.querySelector('#batchValueSelect');
                if (select.value) {
                    insertToken(`batch_value:${select.value}`);
                } else {
                    // Show message or highlight select
                    select.focus();
                    select.style.borderColor = 'var(--red-med)';
                    setTimeout(() => {
                        select.style.borderColor = 'var(--gray-med)';
                    }, 1500);
                }
            } else {
                insertToken(token);
            }
        }
    });
    
    // Handle Enter/Tab for tokens with selects
    function handleTokenSelection() {
        if (selectedIndex >= 0) {
            const options = popup.querySelectorAll('.token-option');
            const selectedOption = options[selectedIndex];
            const token = selectedOption.dataset.token;
            
            if (token === 'container_value') {
                const select = selectedOption.querySelector('#containerValueSelect');
                if (select.value) {
                    insertToken(`container_value:${select.value}`);
                } else {
                    select.focus();
                    return;
                }
            } else if (token === 'batch_value') {
                const select = selectedOption.querySelector('#batchValueSelect');
                if (select.value) {
                    insertToken(`batch_value:${select.value}`);
                } else {
                    select.focus();
                    return;
                }
            } else {
                insertToken(token);
            }
        }
    }
    
    function showTokenPopup() {
        const rect = input.getBoundingClientRect();
        const modalRect = document.getElementById('containerConfigModal').getBoundingClientRect();
        const wrapper = input.closest('.container-name-input-wrapper');
        
        // Position relative to the input wrapper
        popup.style.display = 'block';
        popup.style.left = '0px';
        popup.style.top = (input.offsetHeight + 2) + 'px';
        
        isPopupVisible = true;
        selectedIndex = -1;
        updateSelection();
    }
    
    function hideTokenPopup() {
        popup.style.display = 'none';
        isPopupVisible = false;
        selectedIndex = -1;
    }
    
    function updateSelection() {
        const options = popup.querySelectorAll('.token-option');
        options.forEach((option, index) => {
            option.classList.toggle('selected', index === selectedIndex);
        });
    }
    
    function insertToken(token) {
        const value = input.value;
        const start = input.selectionStart;
        
        // Find the opening brace position
        let bracePos = start - 1;
        while (bracePos >= 0 && value.charAt(bracePos) !== '{') {
            bracePos--;
        }
        
        if (bracePos >= 0) {
            // Replace from opening brace to cursor with token
            const newValue = value.substring(0, bracePos) + '{' + token + '}' + value.substring(start);
            input.value = newValue;
            
            // Set cursor position after the inserted token
            const newCursorPos = bracePos + token.length + 2;
            input.setSelectionRange(newCursorPos, newCursorPos);
        }
        
        hideTokenPopup();
        input.focus();
    }
}

function hideContainerConfigModal() {
    const modal = document.getElementById('containerConfigModal');
    if (modal) {
        modal.classList.remove('show');
    }
    currentContainerId = null;
    currentContainerName = null;
}

// Close container modal when clicking outside
document.addEventListener('click', function(event) {
    const modal = document.getElementById('containerConfigModal');
    const dialog = document.querySelector('.container-config-dialog');
    
    if (modal && modal.style.display === 'flex' && !dialog.contains(event.target)) {
        hideContainerConfigModal();
    }
});

function saveContainerConfig() {
    if (!currentContainerId) {
        console.error('No container selected for configuration');
        return;
    }
    
    // Collect configuration data from form
    const config = {
        container_id: currentContainerId,
        output_count: parseInt(document.getElementById('outputCount').value),
        output_for: document.getElementById('outputFor').value,
        n_samples_count: parseInt(document.getElementById('nSamplesCount').value),
        rename_container: document.getElementById('renameContainer').checked,
        container_new_name: document.getElementById('containerNewName').value.trim(),
        placement: document.getElementById('containerPlacement').value
    };
    
    console.log('Saving container configuration for:', currentContainerId, config);
    
    // Store configuration in container configurations object
    if (!window.containerConfigurations) {
        window.containerConfigurations = {};
    }
    window.containerConfigurations[currentContainerId] = config;
    
    // Refresh the container display to show the configuration indicator
    const containerItem = document.querySelector(`[data-container-id="${currentContainerId}"]`);
    if (containerItem) {
        const container = availableContainers.find(c => c.cid === currentContainerId);
        if (container) {
            const index = Array.from(containerItem.parentNode.children).indexOf(containerItem);
            containerItem.outerHTML = createContainerItemHTML(container, index);
        }
    }
    
    // Save the step configuration to persist container config to database
    saveStepConfiguration(true).then(result => {
        if (result.status === 'success') {
            hideContainerConfigModal();
            pylims_ui.success('Container configuration saved successfully');
        }
    }).catch(error => {
        console.error('Save container config error:', error);
        pylims_ui.error('Failed to save container configuration');
    });
}

function loadContainerConfig(containerId) {
    console.log('Loading config for container:', containerId);
    
    // Helper function to safely set element value
    function safeSetValue(elementId, value, type = 'value') {
        const element = document.getElementById(elementId);
        if (element) {
            if (type === 'checked') {
                element.checked = value;
            } else {
                element.value = value;
            }
        } else {
            console.error(`Element ${elementId} not found!`);
        }
    }
    
    // Load existing configuration if available
    if (window.containerConfigurations && window.containerConfigurations[containerId]) {
        const config = window.containerConfigurations[containerId];
        console.log('Found existing config:', config);
        
        safeSetValue('outputCount', config.output_count || 1);
        safeSetValue('outputFor', config.output_for || 'every_input');
        safeSetValue('nSamplesCount', config.n_samples_count || 1);
        safeSetValue('renameContainer', config.rename_container || false, 'checked');
        safeSetValue('containerNewName', config.container_new_name || '');
        safeSetValue('containerPlacement', config.placement || 'operator');
        
        // Handle dynamic visibility
        toggleRenameOptions();
        const nSamplesRow = document.getElementById('nSamplesRow');
        if (nSamplesRow) {
            nSamplesRow.style.display = config.output_for === 'n_samples' ? 'flex' : 'none';
        }
    } else {
        console.log('No existing config found, setting defaults');
        // Set default values
        safeSetValue('outputCount', 1);
        safeSetValue('outputFor', 'every_input');
        safeSetValue('nSamplesCount', 1);
        safeSetValue('renameContainer', false, 'checked');
        safeSetValue('containerNewName', '');
        safeSetValue('containerPlacement', 'operator');
        
        // Reset dynamic visibility
        const renameTextRow = document.getElementById('renameTextRow');
        const nSamplesRow = document.getElementById('nSamplesRow');
        if (renameTextRow) renameTextRow.style.display = 'none';
        if (nSamplesRow) nSamplesRow.style.display = 'none';
    }
}

function removeCurrentContainer() {
    if (!currentContainerId) {
        console.error('No container selected for removal');
        return;
    }
    
    if (confirm(`Are you sure you want to remove the container "${currentContainerName}"?`)) {
        removeContainer(currentContainerId);
        hideContainerConfigModal();
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    console.log('Assay configure page loaded for assay ID:', assayId);
    
    // Initialize special sample types from server data
    initializeSpecialSampleTypes();
    console.log('Special sample types initialized, page ready');
    
    // Load container types once at page initialization
    loadAvailableContainers();
    
    // Load all special sample types once at page initialization
    loadAllAvailableSpecialSamples();
    
    // Setup container config event listeners
    setTimeout(() => {
        const outputForSelect = document.getElementById('outputFor');
        const nSamplesRow = document.getElementById('nSamplesRow');
        
        if (outputForSelect && nSamplesRow) {
            outputForSelect.addEventListener('change', function() {
                nSamplesRow.style.display = this.value === 'n_samples' ? 'flex' : 'none';
            });
        }
    }, 100);
});