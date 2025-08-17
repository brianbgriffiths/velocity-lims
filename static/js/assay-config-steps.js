/**
 * Step Configuration Functions
 * Handles step configuration loading, saving, and management
 */

function loadStepConfiguration(stepId) {
    // Ensure special sample types are initialized first
    if (specialSampleTypes.length === 0) {
        initializeSpecialSampleTypes();
    }
    
    // Ensure available special samples are loaded before loading step config
    if (availableSpecialSamples.length === 0) {
        console.log('Loading available special samples before step configuration');
        loadAllAvailableSpecialSamples();
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
            const pagesConfigElement = document.getElementById('pagesConfig');
            if (pagesConfigElement) {
                pagesConfigElement.value = JSON.stringify(config.pages || [], null, 2);
            }
            document.getElementById('sampleDataConfig').value = JSON.stringify(config.sample_data || [], null, 2);
            document.getElementById('stepScriptsConfig').value = JSON.stringify(config.step_scripts || [], null, 2);
            
            // Load containers into visual interface
            loadContainersInterface(config.containers || []);
            
            // Load special samples into visual interfaces
            loadSpecialSamplesInterface(config.special_samples || []);
            
            // Load pages into visual interface
            console.log('About to call loadPagesInterface with:', config.pages);
            console.log('Before loadPagesInterface - checking container existence:');
            console.log('enabledContainers:', document.getElementById('enabledContainers'));
            console.log('enabledPages (before delay):', document.getElementById('enabledPages'));
            setTimeout(() => {
                console.log('enabledPages (after delay):', document.getElementById('enabledPages'));
                loadPagesInterface(config.pages || []);
            }, 100); // Small delay to ensure DOM is ready
            
            // Store current step config globally for page functions
            currentStepConfig = config;
            
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
        
        // Get pages from visual interface (new format matching containers)
        const pages = getPagesFromInterface();
        
        // Parse other JSON fields
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
                        
                        // Also update the step config title if this step is currently selected
                        if (selectedStepId) {
                            document.getElementById('stepConfigTitle').textContent = `Configure: ${stepName}`;
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

function initializeSpecialSampleTypes() {
    console.log('Initializing special sample types...');
    
    // Parse special sample types from global JSON
    try {
        const specialSampleTypesJson = document.getElementById('specialSampleTypesData');
        if (specialSampleTypesJson && specialSampleTypesJson.textContent) {
            specialSampleTypes = JSON.parse(specialSampleTypesJson.textContent);
            console.log('Special sample types loaded:', specialSampleTypes);
            
            // Group by type for easier access
            specialSampleTypeGroups = {};
            specialSampleTypes.forEach(sample => {
                const typeId = sample.sstid;
                if (!specialSampleTypeGroups[typeId]) {
                    specialSampleTypeGroups[typeId] = {
                        type_name: sample.special_type_name,
                        samples: []
                    };
                }
                specialSampleTypeGroups[typeId].samples.push(sample);
            });
            
            console.log('Special sample type groups:', specialSampleTypeGroups);
            
            // Generate UI cards for each type
            generateSpecialSampleCards();
        } else {
            console.warn('No special sample types data found in DOM');
        }
    } catch (error) {
        console.error('Error parsing special sample types:', error);
    }
}

function generateSpecialSampleCards() {
    const configCardsContainer = document.querySelector('.config-cards');
    if (!configCardsContainer) {
        console.error('Config cards container not found');
        return;
    }
    
    // Get unique type IDs
    const typeIds = [...new Set(specialSampleTypes.map(sample => sample.sstid))];
    console.log('Generating cards for type IDs:', typeIds);
    
    typeIds.forEach(typeId => {
        const typeSamples = specialSampleTypes.filter(sample => sample.sstid === typeId);
        if (typeSamples.length === 0) return;
        
        const typeName = typeSamples[0].special_type_name;
        const bucketId = `specialSamples${typeId}`;
        
        const cardHTML = `
            <div class="config-card special-samples-card" data-type-id="${typeId}">
                <label class="form-label">${typeName} Configuration</label>
                <div class="special-samples-panel">
                    <div class="special-samples-header">
                        <span>Enabled ${typeName}</span>
                        <button type="button" class="btn-add-special-sample" onclick="showSpecialSampleSelector(${typeId})">
                            <i class="fas fa-plus"></i> Add
                        </button>
                    </div>
                    <div class="enabled-special-samples special-samples-bucket" id="${bucketId}">
                        <div class="no-special-samples">No ${typeName.toLowerCase()} configured</div>
                    </div>
                </div>
            </div>
        `;
        
        // Insert the card before the pages configuration section
        const pagesSection = document.querySelector('.pages-section');
        if (pagesSection) {
            configCardsContainer.insertBefore(
                document.createRange().createContextualFragment(cardHTML).firstElementChild,
                pagesSection
            );
        } else {
            configCardsContainer.appendChild(
                document.createRange().createContextualFragment(cardHTML).firstElementChild
            );
        }
    });
    
    console.log('Generated special sample cards for all types');
}
