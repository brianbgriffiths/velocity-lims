/**
 * Main Assay View Functions
 * Handles main assay operations, version management, and step ordering
 */

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
        csrf: document.querySelector('[name=csrfmiddlewaretoken]').value,
        url: '../save_version_name',
        submit_mode: 'silent'
    };
    
    return pylims_post(pyoptions).then(result => {
        if (result.status === 'success') {
            console.log('Version name save response:', result);
            
            if (!result.version_unchanged) {
                updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
            }
            
            return result;
        } else {
            throw new Error(result.error || 'Failed to save version name');
        }
    });
}

function updateVersionDisplay(major, minor, patch) {
    const versionElement = document.getElementById('currentVersion');
    if (versionElement) {
        versionElement.textContent = `v${major}.${minor}.${patch || 0}`;
    }
}

// Step Order Management Functions
function toggleStepOrder() {
    const lockButton = document.querySelector('.lock-button');
    const isLocked = lockButton.classList.contains('locked');
    
    if (isLocked) {
        // Unlock mode - enable drag and drop
        lockButton.classList.remove('locked');
        lockButton.innerHTML = '<i class="fas fa-unlock"></i> Unlock';
        lockButton.title = 'Click to lock step order';
        
        enableDragAndDrop();
    } else {
        // Lock mode - disable drag and drop
        lockButton.classList.add('locked');
        lockButton.innerHTML = '<i class="fas fa-lock"></i> Lock';
        lockButton.title = 'Click to unlock step order';
        
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
    e.dataTransfer.setData('text/plain', e.target.dataset.stepId);
    e.target.classList.add('dragging');
}

function handleDragOver(e) {
    e.preventDefault();
    const container = document.querySelector('.steps-list');
    const afterElement = getDragAfterElement(container, e.clientY);
    const dragging = document.querySelector('.dragging');
    
    if (afterElement == null) {
        container.appendChild(dragging);
    } else {
        container.insertBefore(dragging, afterElement);
    }
}

function handleDrop(e) {
    e.preventDefault();
}

function handleDragEnd(e) {
    e.target.classList.remove('dragging');
    updateStepNumbers();
    saveStepOrder();
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
    const stepItems = document.querySelectorAll('.step-item');
    stepItems.forEach((item, index) => {
        const stepNumber = item.querySelector('.step-number');
        if (stepNumber) {
            stepNumber.textContent = index + 1;
        }
    });
}

function saveStepOrder() {
    const stepItems = document.querySelectorAll('.step-item');
    const stepOrder = Array.from(stepItems).map(item => parseInt(item.dataset.stepId));
    
    const pyoptions = {
        data: {
            assay_id: assayId,
            step_order: stepOrder
        },
        csrf: document.querySelector('[name=csrfmiddlewaretoken]').value,
        url: '../save_step_order',
        submit_mode: 'silent'
    };
    
    pylims_post(pyoptions).then(result => {
        if (result.status === 'success') {
            console.log('Step order saved:', result);
            if (!result.version_unchanged) {
                updateVersionDisplay(result.version.version_major, result.version.version_minor, result.version.version_patch);
            }
        } else {
            console.error('Failed to save step order:', result.error);
            pylims_ui.error('Failed to save step order');
        }
    }).catch(error => {
        console.error('Error saving step order:', error);
        pylims_ui.error('Failed to save step order');
    });
}

function selectStep(stepId, stepName) {
    // Clear any existing selection
    document.querySelectorAll('.step-item').forEach(item => {
        item.classList.remove('selected');
    });
    
    // Select the clicked step
    const stepElement = document.querySelector(`[data-step-id="${stepId}"]`);
    if (stepElement) {
        stepElement.classList.add('selected');
    }
    
    // Update the selected step info
    selectedStepId = stepId;
    selectedStepName = stepName;
    
    // Update the step configuration panel title
    const stepConfigTitle = document.querySelector('#stepConfigTitle');
    if (stepConfigTitle) {
        stepConfigTitle.textContent = `Step Configuration: ${stepName}`;
    }
    
    // Show the step configuration panel
    const rightPanel = document.querySelector('.right-panel');
    if (rightPanel) {
        rightPanel.style.display = 'block';
    }
    
    // Load the step configuration
    loadStepConfiguration(stepId);
}

function addNewStep() {
    // This function would handle creating a new step
    // Implementation depends on your step creation workflow
    console.log('Add new step functionality to be implemented');
}
