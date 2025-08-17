/**
 * Container Configuration Functions
 * Handles container management, drag & drop, and configuration
 */

// Globals (initialized once). Provided inline data should populate availableContainers elsewhere if needed.
if (typeof window.enabledContainerIds === 'undefined') {
    window.enabledContainerIds = new Set();
}
if (typeof window.availableContainers === 'undefined') {
    window.availableContainers = [];
}

// Hydrate from inline containerTypesData if present and not yet populated
if (typeof window.containerTypesData !== 'undefined' && Array.isArray(window.containerTypesData) && window.availableContainers.length === 0) {
    window.availableContainers = window.containerTypesData.slice();
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
