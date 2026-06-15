const API_URL = 'http://localhost:8003/process';

let currentResult = null;
let currentSlide = 0;
let zoomLevels = {0: 1, 1: 1};
let selectedFile = null;

// DOM
const fileInput = document.getElementById('fileInput');
const uploadArea = document.getElementById('uploadArea');
const processBtn = document.getElementById('processBtn');
const loading = document.getElementById('loading');
const resultsSection = document.getElementById('resultsSection');
const previewImg = document.getElementById('previewImg');
const uploadPreview = document.getElementById('uploadPreview');
const uploadPlaceholder = document.querySelector('.upload-placeholder');
const removeFileBtn = document.getElementById('removeFileBtn');

// Carousel
const prevBtn = document.getElementById('prevBtn');
const nextBtn = document.getElementById('nextBtn');
const indicators = document.querySelectorAll('.indicator');
const slides = document.querySelectorAll('.slide');

// Step indicators in loading
const step1 = document.getElementById('step1');
const step2 = document.getElementById('step2');
const step3 = document.getElementById('step3');

// Upload handling
uploadArea.addEventListener('click', (e) => {
    if (e.target === removeFileBtn || removeFileBtn.contains(e.target)) return;
    fileInput.click();
});

uploadArea.addEventListener('dragover', (e) => {
    e.preventDefault();
    uploadArea.style.borderColor = '#b45f2b';
});

uploadArea.addEventListener('dragleave', () => {
    uploadArea.style.borderColor = '#e0c8b0';
});

uploadArea.addEventListener('drop', (e) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.type.startsWith('image/')) {
        handleFileSelect(file);
    }
    uploadArea.style.borderColor = '#e0c8b0';
});

fileInput.addEventListener('change', (e) => {
    if (e.target.files[0]) handleFileSelect(e.target.files[0]);
});

removeFileBtn.addEventListener('click', () => {
    selectedFile = null;
    uploadPreview.style.display = 'none';
    uploadPlaceholder.style.display = 'block';
    processBtn.disabled = true;
    fileInput.value = '';
});

function handleFileSelect(file) {
    selectedFile = file;
    const reader = new FileReader();
    reader.onload = (e) => {
        previewImg.src = e.target.result;
        uploadPlaceholder.style.display = 'none';
        uploadPreview.style.display = 'block';
        processBtn.disabled = false;
    };
    reader.readAsDataURL(file);
}

// Carousel navigation
function showSlide(index) {
    slides.forEach(slide => slide.classList.remove('active'));
    indicators.forEach(ind => ind.classList.remove('active'));
    
    slides[index].classList.add('active');
    indicators[index].classList.add('active');
    currentSlide = index;
    
    prevBtn.disabled = index === 0;
    nextBtn.disabled = index === slides.length - 1;
}

prevBtn.addEventListener('click', () => {
    if (currentSlide > 0) showSlide(currentSlide - 1);
});

nextBtn.addEventListener('click', () => {
    if (currentSlide < slides.length - 1) showSlide(currentSlide + 1);
});

indicators.forEach((ind, idx) => {
    ind.addEventListener('click', () => showSlide(idx));
});

// Zoom functionality
function initZoom(slideId, containerId, imgId, zoomOutId, zoomInId, resetId, levelId) {
    let zoom = 1;
    const container = document.getElementById(containerId);
    const img = document.getElementById(imgId);
    
    if (!img) return;
    
    document.getElementById(zoomOutId).addEventListener('click', () => {
        zoom = Math.max(0.5, zoom - 0.1);
        img.style.transform = `scale(${zoom})`;
        document.getElementById(levelId).innerText = `${Math.round(zoom * 100)}%`;
    });
    
    document.getElementById(zoomInId).addEventListener('click', () => {
        zoom = Math.min(3, zoom + 0.1);
        img.style.transform = `scale(${zoom})`;
        document.getElementById(levelId).innerText = `${Math.round(zoom * 100)}%`;
    });
    
    document.getElementById(resetId).addEventListener('click', () => {
        zoom = 1;
        img.style.transform = `scale(1)`;
        document.getElementById(levelId).innerText = `100%`;
    });
}

// Process
processBtn.addEventListener('click', async () => {
    if (!selectedFile) return;
    
    const formData = new FormData();
    formData.append('file', selectedFile);
    
    processBtn.disabled = true;
    loading.style.display = 'block';
    resultsSection.style.display = 'none';
    
    step1.classList.add('active');
    
    try {
        const response = await fetch(API_URL, { method: 'POST', body: formData });
        const data = await response.json();
        
        step1.classList.remove('active');
        step2.classList.add('active');
        await new Promise(r => setTimeout(r, 500));
        step2.classList.remove('active');
        step3.classList.add('active');
        await new Promise(r => setTimeout(r, 300));
        
        currentResult = data;
        displayResults(data);
        
        loading.style.display = 'none';
        resultsSection.style.display = 'block';
        showSlide(0);
        
    } catch (error) {
        alert(`Ошибка: ${error.message}`);
        loading.style.display = 'none';
        processBtn.disabled = false;
    } finally {
        step1.classList.remove('active');
        step2.classList.remove('active');
        step3.classList.remove('active');
    }
});

// Display results
function displayResults(data) {
    // Original image
    const reader = new FileReader();
    reader.onload = (e) => {
        const origImg = document.getElementById('originalImage');
        origImg.src = e.target.result;
    };
    reader.readAsDataURL(selectedFile);
    
    // Segmented image
    const segmentedFilename = data.segmentation?.segmented_image_filename;
    if (segmentedFilename) {
        document.getElementById('segmentedImage').src = `http://localhost:8002/get_image/${segmentedFilename}`;
    } else {
        document.getElementById('segmentedImage').src = '/placeholder-segmented.jpg';
    }
        
    // Cells count
    const cellsCount = data.segmentation?.cells?.length || 0;
    document.getElementById('cellsCount').innerText = cellsCount;
    
    // ГРУППИРУЕМ ЯЧЕЙКИ ПО СТРОКАМ
    const ocrResults = data.ocr_results || [];
    const rowsMap = new Map();
    
    // Создаем карту LLM коррекций
    const llmMap = new Map();
    if (data.llm_correction && data.llm_correction.results) {
        data.llm_correction.results.forEach(item => {
            const key = `${item.row}|${item.col_name_rus}`;
            llmMap.set(key, item.corrected_text);
        });
    }
    
    ocrResults.forEach(item => {
        const rowNum = item.row;
        if (!rowsMap.has(rowNum)) {
            rowsMap.set(rowNum, {});
        }
        const colName = item.col_name_rus || item.col_name;
        const key = `${rowNum}|${colName}`;
        const corrected = llmMap.get(key);
        
        rowsMap.get(rowNum)[colName] = {
            original: item.text || '—',
            corrected: corrected || item.text || '—',
            changed: corrected && corrected !== item.text
        };
    });
    
    // Подсчет метрик качества (реальные)
    let totalCells = 0;
    let correctedCells = 0;
    let totalChars = 0;
    let changedChars = 0;
    
    for (const [rowNum, cells] of rowsMap) {
        for (const [colName, data] of Object.entries(cells)) {
            totalCells++;
            if (data.changed) {
                correctedCells++;
            }
            // Сравниваем символы для CER
            const maxLen = Math.max(data.original.length, data.corrected.length);
            for (let i = 0; i < maxLen; i++) {
                if (data.original[i] !== data.corrected[i]) {
                    changedChars++;
                }
                totalChars++;
            }
        }
    }
    
    const cer = totalChars > 0 ? Math.round((changedChars / totalChars) * 100) : 0;
    const accuracy = 100 - cer;
    
    document.getElementById('cerValue').innerText = `${cer}%`;
    document.getElementById('accuracyValue').innerText = `${accuracy}%`;
    
    // Заполняем таблицу
    const tbody = document.querySelector('#resultsTable tbody');
    tbody.innerHTML = '';
    
    const columnOrder = ['Имя родившегося', 'Родители', 'Восприемники (крестные)', 'Священник'];
    let rowNumber = 1;
    
    for (const [rowNum, cells] of rowsMap) {
        const tr = tbody.insertRow();
        tr.insertCell(0).innerText = rowNumber++;
        
        columnOrder.forEach(colName => {
            const cellData = cells[colName] || { original: '—', corrected: '—', changed: false };
            
            if (cellData.changed) {
                // Показываем оба варианта
                tr.insertCell(1).innerHTML = `
                    <div style="display: flex; flex-direction: column; gap: 4px;">
                        <span style="font-size: 0.85em; color: #666;">OCR: ${cellData.original}</span>
                        <span style="font-weight: bold; color: #2e7d32;">→ ${cellData.corrected}</span>
                    </div>
                `;
            } else {
                // Только оригинал
                tr.insertCell(1).innerHTML = `<span>${cellData.original}</span>`;
            }
        });
        
        // Статус строки
        const hasChanges = Object.values(cells).some(c => c.changed);
        tr.insertCell(5).innerHTML = hasChanges 
            ? '<span class="badge-corrected">✅ Исправлено</span>'
            : '<span class="badge-original">○ Оригинал</span>';
    }
    
    if (rowsMap.size === 0) {
        const tr = tbody.insertRow();
        const td = tr.insertCell(0);
        td.colSpan = 6;
        td.style.textAlign = 'center';
        td.innerText = 'Нет данных для отображения';
    }
    
    // Zoom init
    setTimeout(() => {
        initZoom(0, 'originalImageContainer', 'originalImage', 'zoomOut0', 'zoomIn0', 'resetZoom0', 'zoomLevel0');
        initZoom(1, 'segmentedImageContainer', 'segmentedImage', 'zoomOut1', 'zoomIn1', 'resetZoom1', 'zoomLevel1');
    }, 100);
    
    // JSON downloads
    document.getElementById('downloadOcrJson').onclick = () => downloadJson(data.ocr_results, 'ocr_results.json');
    document.getElementById('downloadLlmJson').onclick = () => downloadJson(data.llm_correction, 'llm_results.json');
    document.getElementById('downloadFullJson').onclick = () => downloadJson(data, 'full_results.json');
}

function downloadJson(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}