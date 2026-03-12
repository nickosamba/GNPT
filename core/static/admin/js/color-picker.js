// Color Picker Enhancement for Categorie Admin
// Adds a color palette with predefined colors

document.addEventListener('DOMContentLoaded', function() {
    const colorInput = document.querySelector('input[name="couleur"]');
    
    if (!colorInput) return;

    // Define a palette of suggested colors
    const colorPalette = [
        '#3B82F6', // Blue
        '#10B981', // Emerald
        '#F59E0B', // Amber
        '#EF4444', // Red
        '#8B5CF6', // Violet
        '#EC4899', // Pink
        '#06B6D4', // Cyan
        '#84CC16', // Lime
        '#F97316', // Orange
        '#14B8A6', // Teal
        '#6366F1', // Indigo
        '#F43F5E', // Rose
    ];

    // Create palette container
    const paletteContainer = document.createElement('div');
    paletteContainer.className = 'color-palette';
    paletteContainer.title = 'Sélection rapide de couleur';

    // Create color swatches
    colorPalette.forEach(color => {
        const swatch = document.createElement('span');
        swatch.className = 'color-swatch';
        swatch.style.backgroundColor = color;
        swatch.title = color;
        swatch.addEventListener('click', function() {
            colorInput.value = color;
            // Trigger change event
            colorInput.dispatchEvent(new Event('change', { bubbles: true }));
            
            // Update visual selection
            document.querySelectorAll('.color-swatch').forEach(s => s.classList.remove('selected'));
            swatch.classList.add('selected');
        });
        paletteContainer.appendChild(swatch);
    });

    // Insert palette after the color input
    const formField = colorInput.closest('div') || colorInput.parentElement;
    if (formField) {
        const helpText = document.createElement('p');
        helpText.className = 'help-text';
        helpText.textContent = 'Cliquez sur une couleur pour la sélectionner rapidement :';
        formField.insertBefore(helpText, formField.nextSibling);
        formField.insertBefore(paletteContainer, helpText.nextSibling);
    }

    // Initialize selected state
    if (colorInput.value) {
        const selectedSwatch = Array.from(paletteContainer.children).find(
            swatch => swatch.title === colorInput.value
        );
        if (selectedSwatch) {
            selectedSwatch.classList.add('selected');
        }
    }
});
