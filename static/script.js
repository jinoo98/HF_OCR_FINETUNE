let allData = [];
let currentIndex = 0;
let hasUnsavedChanges = false;
let currentScale = 1;
let translateX = 0, translateY = 0;

const fieldsToEdit = [
    { label: '상호명', keyIdx: 2 },
    { label: '사업자번호', keyIdx: 4 },
    { label: '날짜', keyIdx: 6 },
    { label: '합계', keyIdx: 8 }
];

async function fetchData() {
    try {
        const res = await fetch('/api/data');
        allData = await res.json();
        renderCurrent(true); // Initial render no transition
    } catch (err) {
        console.error('Error fetching data:', err);
    }
}

function handleInputChange() {
    hasUnsavedChanges = true;
    document.getElementById('saveStatus').innerText = 'Unsaved Changes';
    document.getElementById('saveStatus').classList.add('saving');

    const saveBtn = document.getElementById('saveBtn');
    saveBtn.classList.add('unsaved');
    saveBtn.innerText = 'Save Changes';
}

function updateProgress() {
    const total = allData.length;
    if (total === 0) return;

    const completed = allData.filter(d => d.checked).length;
    const progressPercent = (completed / total) * 100;

    document.getElementById('progressFill').style.width = `${progressPercent}%`;
}

async function renderCurrent(noTransition = false) {
    if (allData.length === 0) return;

    const imgElement = document.getElementById('receiptImage');
    const container = document.querySelector('.image-container');
    const entry = allData[currentIndex];
    const imagePath = entry.image_info[0].image_url.replace('./images/', '/dataset/images/');

    // Reset zoom on navigation
    currentScale = 1;
    translateX = 0;
    translateY = 0;
    imgElement.style.transform = '';
    imgElement.style.transition = 'opacity 0.3s ease, transform 0.3s ease';

    if (!noTransition) {
        imgElement.classList.add('fade');
        await new Promise(r => setTimeout(r, 300));
    }

    imgElement.src = imagePath;
    document.getElementById('pageInput').value = currentIndex + 1;
    document.getElementById('totalPages').innerText = ` / ${allData.length}`;

    if (!noTransition) {
        imgElement.onload = () => imgElement.classList.remove('fade');
    }

    const fieldsContainer = document.getElementById('fieldsList');
    fieldsContainer.innerHTML = '';

    fieldsToEdit.forEach(field => {
        const textInfo = entry.text_info[field.keyIdx + 1];
        const value = textInfo ? textInfo.text : '';

        const group = document.createElement('div');
        group.className = 'field-group';
        group.innerHTML = `
            <label>${field.label}</label>
            <input type="text" value="${value}" data-idx="${field.keyIdx + 1}">
        `;
        group.querySelector('input').addEventListener('input', handleInputChange);
        fieldsContainer.appendChild(group);
    });

    // Configure the button text depending on whether changes exist
    const saveBtn = document.getElementById('saveBtn');
    if (hasUnsavedChanges) {
        saveBtn.innerText = 'Save Changes';
    } else {
        saveBtn.innerText = 'Confirm';
    }

    // Status update
    const status = document.getElementById('saveStatus');
    status.innerText = 'Synced';
    status.classList.remove('saving');
    saveBtn.classList.remove('unsaved');
    hasUnsavedChanges = false;

    updateProgress();
}

async function saveChanges() {
    if (allData.length === 0) return;

    const status = document.getElementById('saveStatus');
    status.innerText = 'Saving...';
    status.classList.add('saving');

    const entry = allData[currentIndex];
    const inputs = document.querySelectorAll('.fields-container input');

    inputs.forEach(input => {
        const idx = parseInt(input.dataset.idx);
        if (entry.text_info[idx]) {
            entry.text_info[idx].text = input.value;
        }
    });

    // Auto-check this item on Confirm or Save
    entry.checked = true;

    try {
        const res = await fetch('/api/save', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                index: currentIndex,
                data: entry
            })
        });

        if (res.ok) {
            showToast();
            status.innerText = 'Synced';
            status.classList.remove('saving');

            const saveBtn = document.getElementById('saveBtn');
            saveBtn.classList.remove('unsaved');
            saveBtn.innerText = 'Confirm';

            hasUnsavedChanges = false;
            updateProgress();
        } else {
            alert('Error saving data');
            status.innerText = 'Error';
        }
    } catch (err) {
        console.error('Save error:', err);
        status.innerText = 'Error';
    }
}

function showToast() {
    const toast = document.getElementById('toast');
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 3000);
}

async function navigate(direction) {
    if (hasUnsavedChanges) {
        if (!confirm('You have unsaved changes. Discard and move?')) return;
    }

    if (direction === 'next' && currentIndex < allData.length - 1) {
        currentIndex++;
        await renderCurrent();
    } else if (direction === 'prev' && currentIndex > 0) {
        currentIndex--;
        await renderCurrent();
    }
}

document.getElementById('prevBtn').onclick = () => navigate('prev');
document.getElementById('nextBtn').onclick = () => navigate('next');
document.getElementById('saveBtn').onclick = saveChanges;

document.getElementById('pageInput').addEventListener('change', async (e) => {
    let newIndex = parseInt(e.target.value, 10) - 1;
    if (isNaN(newIndex)) {
        e.target.value = currentIndex + 1;
        return;
    }

    if (newIndex < 0) newIndex = 0;
    if (newIndex >= allData.length) newIndex = allData.length - 1;

    if (newIndex !== currentIndex) {
        if (hasUnsavedChanges) {
            if (!confirm('You have unsaved changes. Discard and move?')) {
                e.target.value = currentIndex + 1;
                return;
            }
        }
        currentIndex = newIndex;
        await renderCurrent();
    } else {
        e.target.value = currentIndex + 1;
    }
});

// Keyboard Shortcuts
window.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowLeft') {
        navigate('prev');
    } else if (e.key === 'ArrowRight') {
        navigate('next');
    } else if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault();
        saveChanges();
    }
});

// Image Zoom & Pan
const imgContainer = document.querySelector('.image-container');
const receiptImg = document.getElementById('receiptImage');

let isDragging = false;
let startX, startY;

receiptImg.style.cursor = 'grab';

function updateTransform() {
    receiptImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${currentScale})`;
}

imgContainer.addEventListener('wheel', (e) => {
    e.preventDefault();
    const zoomSensitivity = 0.15;
    const delta = e.deltaY > 0 ? -1 : 1;
    let newScale = currentScale + delta * zoomSensitivity;

    // Limits
    newScale = Math.max(0.1, Math.min(newScale, 15));

    currentScale = newScale;
    receiptImg.style.transition = 'transform 0.1s ease-out';
    updateTransform();
}, { passive: false });

imgContainer.addEventListener('mousedown', (e) => {
    isDragging = true;
    startX = e.clientX - translateX;
    startY = e.clientY - translateY;
    receiptImg.style.cursor = 'grabbing';
    receiptImg.style.transition = 'none'; // Remove transition for instant drag
    e.preventDefault(); // Prevent default image dragging
});

window.addEventListener('mousemove', (e) => {
    if (!isDragging) return;
    translateX = e.clientX - startX;
    translateY = e.clientY - startY;
    updateTransform();
});

window.addEventListener('mouseup', () => {
    if (isDragging) {
        isDragging = false;
        receiptImg.style.cursor = 'grab';
    }
});

imgContainer.addEventListener('dblclick', () => {
    currentScale = 1;
    translateX = 0;
    translateY = 0;
    receiptImg.style.transition = 'transform 0.3s ease';
    updateTransform();
});

// Initial load
fetchData();
