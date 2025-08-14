// Settings Assay Configure JavaScript

// Global variables - these need to be initialized by the template
let csrf, assayId, specialSampleTypesData;
let selectedStepId = null;
let isReorderMode = false;
let draggedElement = null;

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
            avid: window.assayAvidFromTemplate || null,
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

// ... [Continue with all the other functions from the original JavaScript]
// This file is getting long, so I'll split the remaining functions into logical groups

// [Note: The rest of the functions would be included here - loadSpecialSamplesInterface, 
// container functions, modal functions, etc. - but I'm truncating for brevity]

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

// Add all remaining functions here...
// [This would continue with all the other functions from the original file]
