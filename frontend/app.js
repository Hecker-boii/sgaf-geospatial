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

// Status polling - optimized for faster updates
let fastPollInterval = null;

function startStatusPolling(datasetId) {
    // Clear any existing intervals
    if (statusCheckInterval) {
        clearInterval(statusCheckInterval);
        statusCheckInterval = null;
    }
    if (fastPollInterval) {
        clearInterval(fastPollInterval);
        fastPollInterval = null;
    }

    // Check immediately
    checkStatus(datasetId);

    // Fast polling for first 30 seconds (every 1 second)
    let fastPollCount = 0;
    fastPollInterval = setInterval(() => {
        fastPollCount++;
        checkStatus(datasetId);
        
        // After 30 seconds, switch to slower polling
        if (fastPollCount >= 30) {
            if (fastPollInterval) {
                clearInterval(fastPollInterval);
                fastPollInterval = null;
            }
            statusCheckInterval = setInterval(() => {
                checkStatus(datasetId);
            }, 3000);
        }
    }, 1000);
}

async function checkStatus(datasetId) {
    try {
        const response = await fetch(`${API_URL}status/${datasetId}`, {
            cache: 'no-cache',
            headers: {
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
        });
        if (!response.ok) {
            throw new Error('Failed to fetch status');
        }

        const data = await response.json();
        console.log('Status check response:', JSON.stringify(data, null, 2)); // Debug log
        
        // Update status display immediately
        updateStatusDisplay(data);

        // Check if we have results (handle multiple nested structures)
        let hasResults = false;
        let resultData = null;
        
        if (data.result) {
            console.log('Result structure:', JSON.stringify(data.result, null, 2)); // Debug
            
            // Check if result has summary directly
            if (data.result.summary) {
                hasResults = true;
                resultData = data.result;
                console.log('Found results with summary structure');
            }
            // Check if result itself is the summary (has pointCount or polygonCount)
            else if (data.result.pointCount !== undefined || data.result.polygonCount !== undefined || 
                     (data.result.M && data.result.M.summary)) {
                hasResults = true;
                // Handle DynamoDB format if needed
                if (data.result.M && data.result.M.summary) {
                    // Convert DynamoDB format
                    resultData = { summary: convertDynamoDBFormat(data.result.M.summary) };
                } else {
                    resultData = { summary: data.result };
                }
                console.log('Found results with direct summary data');
            }
            // Check for nested M (DynamoDB map format)
            else if (data.result.M) {
                if (data.result.M.summary) {
                    hasResults = true;
                    resultData = { summary: convertDynamoDBFormat(data.result.M.summary) };
                    console.log('Found results in DynamoDB M format');
                }
            }
        }
        
        // Helper function to convert DynamoDB format (if needed)
        function convertDynamoDBFormat(obj) {
            if (!obj || typeof obj !== 'object') return obj;
            if (obj.M) {
                // It's a DynamoDB map, convert recursively
                const result = {};
                for (const [key, value] of Object.entries(obj.M)) {
                    if (value && typeof value === 'object') {
                        if (value.S !== undefined) result[key] = value.S;
                        else if (value.N !== undefined) result[key] = parseFloat(value.N);
                        else if (value.BOOL !== undefined) result[key] = value.BOOL;
                        else if (value.L !== undefined) result[key] = value.L.map(item => convertDynamoDBFormat(item));
                        else if (value.M !== undefined) result[key] = convertDynamoDBFormat(value);
                        else result[key] = value;
                    } else {
                        result[key] = value;
                    }
                }
                return result;
            }
            return obj;
        }

        // Show results immediately when available
        if (hasResults && resultData) {
            document.getElementById('processingIndicator').style.display = 'none';
            showResults(resultData);
            console.log('Results displayed successfully');
        }

        // Handle completion or failure
        if (data.status === 'COMPLETED' || data.status === 'FAILED') {
            console.log('Status is COMPLETED or FAILED, stopping polling');
            
            // Clear all intervals immediately
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
                statusCheckInterval = null;
            }
            if (fastPollInterval) {
                clearInterval(fastPollInterval);
                fastPollInterval = null;
            }

            document.getElementById('processingIndicator').style.display = 'none';

            if (data.status === 'COMPLETED') {
                // Always try to show results when completed
                if (hasResults && resultData) {
                    showResults(resultData);
                    showToast('✅ Processing completed successfully! Results displayed below.', 'success');
                } else if (data.result) {
                    // Try to show results even if structure is different
                    console.log('Attempting to show results with different structure');
                    showResults(data.result);
                    showToast('✅ Processing completed successfully!', 'success');
                } else {
                    showToast('✅ Processing completed successfully! Fetching results...', 'success');
                    // Retry once more after a short delay
                    setTimeout(() => {
                        checkStatus(datasetId);
                    }, 2000);
                }
            } else {
                showToast('❌ Processing failed. Please check the logs.', 'error');
                if (data.error) {
                    console.error('Error details:', data.error);
                }
            }
            
            loadJobsList();
            updateStats();
        } else {
            // Still processing - show indicator only if no results yet
            if ((data.status === 'PROCESSING' || data.status === 'PENDING') && !hasResults) {
                document.getElementById('processingIndicator').style.display = 'block';
            } else if (hasResults) {
                // We have results, hide processing indicator
                document.getElementById('processingIndicator').style.display = 'none';
            }
        }
    } catch (error) {
        console.error('Error checking status:', error);
        showToast('Error checking status: ' + error.message, 'error');
    }
}

function updateStatusDisplay(data) {
    const datasetIdEl = document.getElementById('datasetId');
    const statusEl = document.getElementById('status');
    const fileNameEl = document.getElementById('fileName');
    const createdAtEl = document.getElementById('createdAt');
    
    if (datasetIdEl) datasetIdEl.textContent = data.datasetId || '-';
    if (statusEl) {
        const status = data.status || '-';
        statusEl.textContent = status;
        statusEl.className = `status-badge ${status}`;
        
        // Update processing indicator based on status
        const processingIndicator = document.getElementById('processingIndicator');
        if (status === 'PROCESSING' || status === 'PENDING') {
            if (processingIndicator) processingIndicator.style.display = 'block';
        } else if (status === 'COMPLETED' || status === 'FAILED') {
            if (processingIndicator) processingIndicator.style.display = 'none';
        }
    }
    if (fileNameEl) fileNameEl.textContent = data.fileName || '-';
    if (createdAtEl) {
        createdAtEl.textContent = data.createdAt ? 
            new Date(data.createdAt).toLocaleString() : '-';
    }
}

function showResults(result) {
    const resultsSection = document.getElementById('resultsSection');
    const resultsDiv = document.getElementById('results');
    
    // Show immediately without waiting
    resultsSection.style.display = 'block';
    
    // Handle both nested and flat result structures
    let summary = result;
    if (result && result.summary) {
        summary = result.summary;
    }
    // If summary itself has a summary (nested), unwrap it
    if (summary && summary.summary) {
        summary = summary.summary;
    }
    
    // Handle DynamoDB string format (floats stored as strings)
    if (summary) {
        // Convert string numbers back to numbers for display
        if (typeof summary.pointCount === 'string') {
            summary.pointCount = parseInt(summary.pointCount) || 0;
        }
        if (typeof summary.polygonCount === 'string') {
            summary.polygonCount = parseInt(summary.polygonCount) || 0;
        }
        if (typeof summary.polygonArea === 'string') {
            summary.polygonArea = parseFloat(summary.polygonArea) || 0;
        }
        if (typeof summary.otherCount === 'string') {
            summary.otherCount = parseInt(summary.otherCount) || 0;
        }
        // Handle bbox array (convert strings to numbers)
        if (summary.bbox && Array.isArray(summary.bbox)) {
            summary.bbox = summary.bbox.map(v => {
                if (typeof v === 'string') {
                    const num = parseFloat(v);
                    return isNaN(num) ? v : num;
                }
                return v;
            });
        }
        // Handle centroid array (convert strings to numbers)
        if (summary.pointCentroid && Array.isArray(summary.pointCentroid)) {
            summary.pointCentroid = summary.pointCentroid.map(v => {
                if (typeof v === 'string') {
                    const num = parseFloat(v);
                    return isNaN(num) ? v : num;
                }
                return v;
            });
        }
    }
    
    // Scroll smoothly after a brief delay to ensure content is rendered
    setTimeout(() => {
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 100);
    
    // Check if we have valid summary data
    if (!summary || (typeof summary !== 'object')) {
        resultsDiv.innerHTML = '<div class="loading-state"><p>No results data available yet. Please wait...</p></div>';
        return;
    }
    
    let html = '<div class="results-grid">';
    
    // Point Count
    const pointCount = summary.pointCount !== undefined ? (typeof summary.pointCount === 'string' ? parseInt(summary.pointCount) : summary.pointCount) : 0;
    html += `
        <div class="result-card">
            <h3>📍 Points</h3>
            <div class="value">${pointCount.toLocaleString()}</div>
            <div class="label">Total point features</div>
        </div>
    `;
    
    // Polygon Count
    const polygonCount = summary.polygonCount !== undefined ? (typeof summary.polygonCount === 'string' ? parseInt(summary.polygonCount) : summary.polygonCount) : 0;
    html += `
        <div class="result-card">
            <h3>🔷 Polygons</h3>
            <div class="value">${polygonCount.toLocaleString()}</div>
            <div class="label">Total polygon features</div>
        </div>
    `;
    
    // Polygon Area
    if (summary.polygonArea !== undefined) {
        const area = typeof summary.polygonArea === 'string' ? parseFloat(summary.polygonArea) : summary.polygonArea;
        html += `
            <div class="result-card">
                <h3>📐 Area</h3>
                <div class="value">${area.toFixed(6)}</div>
                <div class="label">Total polygon area (square units)</div>
            </div>
        `;
    }
    
    // Other Count
    if (summary.otherCount !== undefined) {
        const otherCount = typeof summary.otherCount === 'string' ? parseInt(summary.otherCount) : summary.otherCount;
        html += `
            <div class="result-card">
                <h3>📊 Other Features</h3>
                <div class="value">${otherCount.toLocaleString()}</div>
                <div class="label">Other feature types</div>
            </div>
        `;
    }
    
    // Bounding Box
    if (summary.bbox && Array.isArray(summary.bbox) && summary.bbox.length === 4) {
        const bbox = summary.bbox.map(v => {
            if (typeof v === 'string') {
                const num = parseFloat(v);
                return isNaN(num) ? v : num;
            }
            return v;
        });
        html += `
            <div class="result-card">
                <h3>📦 Bounding Box</h3>
                <div class="value">[${bbox.map(v => (typeof v === 'number' ? v.toFixed(4) : v)).join(', ')}]</div>
                <div class="label">[minX, minY, maxX, maxY]</div>
            </div>
        `;
    }
    
    // Centroid
    if (summary.pointCentroid && Array.isArray(summary.pointCentroid) && summary.pointCentroid.length >= 2) {
        const centroid = summary.pointCentroid.map(v => {
            if (typeof v === 'string') {
                const num = parseFloat(v);
                return isNaN(num) ? v : num;
            }
            return v;
        });
        html += `
            <div class="result-card">
                <h3>🎯 Centroid</h3>
                <div class="value">[${centroid.map(v => (typeof v === 'number' ? v.toFixed(4) : v)).join(', ')}]</div>
                <div class="label">Point centroid coordinates</div>
            </div>
        `;
    }
    
    // Processing Status
    if (summary.ok !== undefined) {
        html += `
            <div class="result-card">
                <h3>✅ Status</h3>
                <div class="value">${summary.ok ? 'Success' : 'Warning'}</div>
                <div class="label">Processing status</div>
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
