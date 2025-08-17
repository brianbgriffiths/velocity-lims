/**
 * Step Configuration Functions
 * Handles step configuration loading, saving, and management
 */

function loadStepConfiguration(stepId) {
    // Ensure special samples data is initialized (uses special-samples module globals)
    try {
    if (typeof window.specialSampleTypesData === 'undefined' || window.specialSampleTypesData.length === 0) {
            if (typeof initializeSpecialSampleTypes === 'function') {
                console.log('Initializing special sample types (steps module)');
                initializeSpecialSampleTypes();
            } else {
                console.warn('initializeSpecialSampleTypes not yet available');
            }
        }
    } catch (e) {
        console.warn('Special samples initialization check failed:', e);
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

// (Removed duplicated special sample initialization/card generation code; now lives in assay-config-special-samples.js)
