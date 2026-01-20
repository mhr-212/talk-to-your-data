/**
 * Talk to Your Data - Frontend JavaScript
 * Handles UI interactions and API calls
 */

async function submitQuery() {
    const question = document.getElementById('question').value.trim();
    
    if (!question) {
        showStatus('Please enter a question', 'error');
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    const originalText = submitBtn.textContent;
    
    // Show loading state
    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span>Analyzing...';
    showStatus('Analyzing your question...', 'loading');
    clearResults();

    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question: question,
                user_id: 'web_user_1',
                username: 'analyst',
                role: 'analyst',
            }),
        });

        const data = await response.json();

        if (!response.ok) {
            showError(data);
            return;
        }

        displayResults(data);
        showStatus('✓ Query executed successfully', 'success');
    } catch (error) {
        showStatus(`Network error: ${error.message}`, 'error');
        console.error('Error:', error);
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = originalText;
    }
}

function displayResults(data) {
    // Show explanation
    const explanationEl = document.getElementById('explanation');
    explanationEl.textContent = data.explanation || 'No explanation available';

    // Show SQL
    const sqlEl = document.getElementById('sql');
    sqlEl.textContent = data.generated_sql;

    // Show table
    const tableContainer = document.getElementById('tableContainer');
    if (data.rows && data.rows.length > 0) {
        const table = buildTable(data.columns, data.rows);
        tableContainer.innerHTML = table;
    } else {
        tableContainer.innerHTML = '<div class="no-results">No rows returned</div>';
    }

    // Show metadata
    const metaEl = document.getElementById('meta');
    metaEl.textContent = `Rows: ${data.rows.length} | Latency: ${data.latency_ms}ms`;

    // Show results section
    document.getElementById('results').classList.add('show');
}

function buildTable(columns, rows) {
    let html = '<table class="data-table"><thead><tr>';

    // Header
    columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead><tbody>';

    // Rows
    rows.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            const value = row[col];
            const displayValue = formatValue(value);
            html += `<td>${escapeHtml(displayValue)}</td>`;
        });
        html += '</tr>';
    });

    html += '</tbody></table>';
    return html;
}

function formatValue(value) {
    if (value === null || value === undefined) {
        return '—';
    }
    if (typeof value === 'number') {
        // Format numbers with thousand separators
        if (Number.isInteger(value)) {
            return value.toLocaleString();
        }
        return parseFloat(value).toFixed(2);
    }
    return String(value);
}

function escapeHtml(text) {
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, m => map[m]);
}

function showStatus(message, type) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
}

function showError(data) {
    const statusEl = document.getElementById('status');
    statusEl.innerHTML = `
        <strong>Error:</strong> ${escapeHtml(data.error)}
        ${data.generated_sql ? `<div class="error-details"><strong>Generated SQL:</strong> ${escapeHtml(data.generated_sql)}</div>` : ''}
        ${data.details ? `<div class="error-details">${escapeHtml(data.details)}</div>` : ''}
    `;
    statusEl.className = 'status error';
}

function clearResults() {
    document.getElementById('results').classList.remove('show');
    document.getElementById('status').textContent = '';
    document.getElementById('status').className = 'status';
}

// Allow submitting with Ctrl+Enter or Cmd+Enter in textarea
document.addEventListener('DOMContentLoaded', () => {
    const questionInput = document.getElementById('question');
    questionInput.addEventListener('keydown', (e) => {
        if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
            submitQuery();
        }
    });

    // Optional: Load health status on page load
    checkHealth();
});

async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('Health check:', data);
        if (data.services.database && data.services.genai_client) {
            // All systems go
        } else {
            console.warn('Some services degraded:', data.services);
        }
    } catch (error) {
        console.error('Health check failed:', error);
    }
}
