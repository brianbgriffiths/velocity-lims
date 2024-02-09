function on_change_clear_msg_elements(obj) {
    function definePropertyRecursively(obj, key, value) {
        // If the value is an object, recursively define properties for it
        if (typeof value === 'object' && value !== null) {
            Object.keys(value).forEach(subKey => {
                definePropertyRecursively(value, subKey, value[subKey]);
            });
        }

        // Define getter and setter for the property
        Object.defineProperty(obj, key, {
            get() {
                return value;
            },
            set(newValue) {
                value = newValue;
                // Trigger the action when the property changes
                console.log(`Property '${key}' changed to:`, newValue);
				clear_msg_elements();
            }
        });
    }

    // Define properties for the top-level object
    Object.keys(obj).forEach(key => {
        definePropertyRecursively(obj, key, obj[key]);
    });
}