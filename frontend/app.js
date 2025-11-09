// Configuration
const API_URL = 'https://pkj2v7ecf3.execute-api.us-east-1.amazonaws.com/prod/';

// State
let currentDatasetId = null;
let statusCheckInterval = null;
let jobs = [];

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    initializeUpload();
    initializeButtons();
    loadJobsList();
    updateStats();
});

// Upload functionality
function initializeUpload() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');

    uploadArea.addEventListener('click', () => fileInput.click());

    uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', () => {
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelect(files[0]);
        }
    });

    fileInput.addEventListener('change', (e) => {
        if (e.target.files.length > 0) {
            handleFileSelect(e.target.files[0]);
        }
    });

    uploadBtn.addEventListener('click', handleUpload);
}

function handleFileSelect(file) {
    const uploadBtn = document.getElementById('uploadBtn');
    
    const validExtensions = ['.geojson', '.json', '.tif', '.tiff', '.geotiff'];
    const fileExt = '.' + file.name.split('.').pop().toLowerCase();
    
    if (!validExtensions.includes(fileExt)) {
        showToast('Invalid file type. Please upload GeoJSON or GeoTIFF files.', 'error');
        uploadBtn.disabled = true;
        return;
    }

    if (file.size > 1048576) {
        showToast('File size exceeds 1 MB limit.', 'error');
        uploadBtn.disabled = true;
        return;
    }

    uploadBtn.disabled = false;
    showToast(`File selected: ${file.name} (${(file.size / 1024).toFixed(2)} KB)`, 'success');
}

async function handleUpload() {
    const fileInput = document.getElementById('fileInput');
    const uploadBtn = document.getElementById('uploadBtn');
    const uploadProgress = document.getElementById('uploadProgress');
    const progressFill = document.getElementById('progressFill');
    const progressText = document.getElementById('progressText');

    if (!fileInput.files.length) {
        showToast('Please select a file first.', 'error');
        return;
    }

    const file = fileInput.files[0];
    uploadBtn.disabled = true;
    uploadProgress.style.display = 'block';
    
    // Simulate progress
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += 10;
        if (progress <= 90) {
            progressFill.style.width = progress + '%';
            progressText.textContent = `Uploading... ${progress}%`;
        }
    }, 200);

    try {
        const datasetId = `demo-${Date.now()}`;
        currentDatasetId = datasetId;

        const fileContent = await readFileAsBase64(file);
        
        progressFill.style.width = '95%';
        progressText.textContent = 'Processing...';

        const response = await fetch(`${API_URL}upload`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                datasetId: datasetId,
                fileName: file.name,
                fileType: file.name.endsWith('.geojson') || file.name.endsWith('.json') ? 'geojson' : 'geotiff',
                fileContent: fileContent,
            }),
        });

        clearInterval(progressInterval);
        progressFill.style.width = '100%';
        progressText.textContent = 'Complete!';

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || `Upload failed: ${response.statusText}`);
        }

        const data = await response.json();
        
        setTimeout(() => {
            uploadProgress.style.display = 'none';
            progressFill.style.width = '0%';
        }, 1000);

        showToast(`Upload successful! Processing started.`, 'success');
        
        document.getElementById('statusSection').style.display = 'block';
        document.getElementById('datasetId').textContent = datasetId;
        document.getElementById('processingIndicator').style.display = 'block';
        startStatusPolling(datasetId);
        
        loadJobsList();
        updateStats();

    } catch (error) {
        clearInterval(progressInterval);
        uploadProgress.style.display = 'none';
        progressFill.style.width = '0%';
        showToast(`Upload failed: ${error.message}`, 'error');
        uploadBtn.disabled = false;
    }
}

function readFileAsBase64(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = (e) => {
            const base64 = e.target.result.split(',')[1];
            resolve(base64);
        };
        reader.onerror = reject;
        reader.readAsDataURL(file);
    });
}

// Status polling
function startStatusPolling(datasetId) {
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
    }

    checkStatus(datasetId);

    statusCheckInterval = setInterval(() => {
        checkStatus(datasetId);
    }, 3000);
}

async function checkStatus(datasetId) {
    try {
        const response = await fetch(`${API_URL}status/${datasetId}`);
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }

        const data = await response.json();
        updateStatusDisplay(data);

        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
            }

            document.getElementById('processingIndicator').style.display = 'none';

            if (data.status === 'COMPLETED') {
                showToast('Processing completed successfully!', 'success');
                if (data.result) {
                    showResults(data.result);
                }
            } else {
                showToast('Processing failed. Please check the logs.', 'error');
            }
            
            loadJobsList();
            updateStats();
        }
    } catch (error) {
        console.error('Error checking status:', error);
    }
}

function updateStatusDisplay(data) {
    document.getElementById('datasetId').textContent = data.datasetId || '-';
    const statusEl = document.getElementById('status');
    statusEl.textContent = data.status || '-';
    statusEl.className = `status-badge ${data.status || ''}`;
    document.getElementById('fileName').textContent = data.fileName || '-';
    document.getElementById('createdAt').textContent = data.createdAt ? 
        new Date(data.createdAt).toLocaleString() : '-';
}

function showResults(result) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsDiv = document.getElementById('results');
    
    resultsSection.style.display = 'block';
    resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    const summary = result.summary || result;
    
    let html = '<div class="results-grid">';
    
    if (summary.pointCount !== undefined) {
        html += `
            <div class="result-card">
                <h3>📍 Points</h3>
                <div class="value">${summary.pointCount}</div>
                <div class="label">Total point features</div>
            </div>
        `;
    }
    
    if (summary.polygonCount !== undefined) {
        html += `
            <div class="result-card">
                <h3>🔷 Polygons</h3>
                <div class="value">${summary.polygonCount}</div>
                <div class="label">Total polygon features</div>
            </div>
        `;
    }
    
    if (summary.polygonArea !== undefined) {
        html += `
            <div class="result-card">
                <h3>📐 Area</h3>
                <div class="value">${summary.polygonArea.toFixed(6)}</div>
                <div class="label">Total polygon area</div>
            </div>
        `;
    }
    
    if (summary.bbox) {
        html += `
            <div class="result-card">
                <h3>📦 Bounding Box</h3>
                <div class="value">[${summary.bbox.map(v => v.toFixed(4)).join(', ')}]</div>
                <div class="label">[minX, minY, maxX, maxY]</div>
            </div>
        `;
    }
    
    if (summary.pointCentroid) {
        html += `
            <div class="result-card">
                <h3>🎯 Centroid</h3>
                <div class="value">[${summary.pointCentroid.map(v => v.toFixed(4)).join(', ')}]</div>
                <div class="label">Point centroid coordinates</div>
            </div>
        `;
    }
    
    html += '</div>';
    
    html += `
        <details style="margin-top: 25px;">
            <summary style="cursor: pointer; font-weight: 600; padding: 15px; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); border-radius: 10px; transition: all 0.3s ease;">
                📄 View Full JSON Results
            </summary>
            <pre style="margin-top: 15px; padding: 20px; background: #f8f9fa; border-radius: 10px; overflow-x: auto; font-size: 0.9em; line-height: 1.6;">${JSON.stringify(result, null, 2)}</pre>
        </details>
    `;
    
    resultsDiv.innerHTML = html;
}

// Jobs list
async function loadJobsList() {
    const jobsList = document.getElementById('jobsList');
    jobsList.innerHTML = '<div class="loading-state"><div class="spinner-small"></div><p>Loading jobs...</p></div>';

    try {
        const response = await fetch(`${API_URL}jobs`);
        if (!response.ok) {
            throw new Error('Failed to fetch jobs');
        }

        const data = await response.json();
        jobs = data.jobs || [];
        displayJobsList(jobs);
        updateStats();
    } catch (error) {
        jobsList.innerHTML = `<div class="loading-state"><p style="color: var(--error);">Error loading jobs: ${error.message}</p></div>`;
    }
}

function displayJobsList(jobsList) {
    const jobsContainer = document.getElementById('jobsList');
    
    if (jobsList.length === 0) {
        jobsContainer.innerHTML = '<div class="loading-state"><p>No jobs found. Upload a file to get started!</p></div>';
        return;
    }

    jobsList.sort((a, b) => new Date(b.createdAt) - new Date(a.createdAt));

    let html = '';
    jobsList.forEach(job => {
        html += `
            <div class="job-item" onclick="viewJob('${job.datasetId}')">
                <div class="job-item-info">
                    <div class="job-item-id">${job.datasetId}</div>
                    <div class="job-item-meta">
                        ${job.fileName || 'Unknown file'} • 
                        ${new Date(job.createdAt).toLocaleString()}
                    </div>
                </div>
                <span class="status-badge ${job.status}">${job.status}</span>
            </div>
        `;
    });

    jobsContainer.innerHTML = html;
}

function viewJob(datasetId) {
    currentDatasetId = datasetId;
    document.getElementById('statusSection').style.display = 'block';
    document.getElementById('datasetId').textContent = datasetId;
    document.getElementById('processingIndicator').style.display = 'block';
    startStatusPolling(datasetId);
    
    document.getElementById('statusSection').scrollIntoView({ behavior: 'smooth' });
}

// Button handlers
function initializeButtons() {
    document.getElementById('refreshBtn').addEventListener('click', () => {
        if (currentDatasetId) {
            checkStatus(currentDatasetId);
            showToast('Status refreshed', 'success');
        }
    });

    document.getElementById('refreshJobsBtn').addEventListener('click', () => {
        loadJobsList();
        showToast('Jobs list refreshed', 'success');
    });
}

// Stats
function updateStats() {
    const totalJobs = jobs.length;
    const activeJobs = jobs.filter(j => j.status === 'PENDING' || j.status === 'PROCESSING').length;
    
    document.getElementById('totalJobs').textContent = totalJobs;
    document.getElementById('activeJobs').textContent = activeJobs;
}

// Toast notifications
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.animation = 'toastSlideIn 0.3s ease-out reverse';
        setTimeout(() => {
            container.removeChild(toast);
        }, 300);
    }, 3000);
}

// Helper functions
function showAbout() {
    alert('SGAF - Serverless Geospatial Analysis Framework\n\nA fully serverless, free-tier-compliant geospatial data processing system using 14+ AWS Services.\n\nBuilt with ❤️ using AWS Serverless Services');
}

function showHelp() {
    alert('Help & Support\n\n1. Upload GeoJSON or GeoTIFF files (max 1MB)\n2. Monitor job status in real-time\n3. View analysis results when complete\n4. Check email for notifications\n\nFor issues, check CloudWatch logs or contact support.');
}

// Make viewJob available globally
window.viewJob = viewJob;
