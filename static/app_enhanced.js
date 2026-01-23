/**
 * Enhanced Talk to Your Data - Frontend Logic
 * Features: Query History, Saved Queries, Export, Visualization
 */

let currentResults = null;
let currentQuery = null;
let chart = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    loadQueryHistory();
    loadSavedQueries();
    loadQuickStats();
    checkHealth();

    // Ctrl+Enter to submit
    document.getElementById('question').addEventListener('keydown', (e) => {
        if (e.ctrlKey && e.key === 'Enter') {
            submitQuery();
        }
    });
});

// Submit query
async function submitQuery() {
    const questionEl = document.getElementById('question');
    const question = questionEl.value.trim();

    if (!question) {
        showStatus('Please enter a question', 'error');
        return;
    }

    showStatus('Processing your question...', 'loading');
    document.getElementById('submitBtn').disabled = true;

    try {
        const response = await fetch('/query', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                question,
                user_id: 'demo_user',
                username: 'Demo User',
                role: 'analyst'
            })
        });

        const data = await response.json();

        if (response.ok) {
            currentResults = data;
            currentQuery = question;
            displayResults(data);
            showStatus(`Query executed successfully in ${data.latency_ms.toFixed(0)}ms`, 'success');

            // Refresh history and stats
            loadQueryHistory();
            loadQuickStats();
        } else {
            showError(data);
        }
    } catch (error) {
        showStatus(`Error: ${error.message}`, 'error');
    } finally {
        document.getElementById('submitBtn').disabled = false;
    }
}

// Display results
function displayResults(data) {
    const resultsDiv = document.getElementById('results');
    resultsDiv.style.display = 'block';

    // Show table view by default
    showTab('table');

    // Build table
    buildTable(data.columns, data.rows);

    // Show SQL
    document.getElementById('generatedSql').textContent = data.generated_sql;

    // Show explanation
    document.getElementById('explanation').textContent = data.explanation || 'No explanation available';

    // Build chart
    buildChart(data.columns, data.rows);
}

// Build table
function buildTable(columns, rows) {
    const container = document.getElementById('resultsTable');

    if (!rows || rows.length === 0) {
        container.innerHTML = '<p style="color: #999;">No results returned</p>';
        return;
    }

    let html = '<table>';

    // Header
    html += '<thead><tr>';
    columns.forEach(col => {
        html += `<th>${escapeHtml(col)}</th>`;
    });
    html += '</tr></thead>';

    // Rows
    html += '<tbody>';
    rows.forEach(row => {
        html += '<tr>';
        columns.forEach(col => {
            const value = row[col];
            html += `<td>${formatValue(value)}</td>`;
        });
        html += '</tr>';
    });
    html += '</tbody></table>';

    container.innerHTML = html;
}

// Build chart
function buildChart(columns, rows) {
    if (!rows || rows.length === 0) return;

    const canvas = document.getElementById('resultChart');
    const ctx = canvas.getContext('2d');

    // Destroy previous chart
    if (chart) {
        chart.destroy();
    }

    // Try to find label and value columns
    let labelCol = columns[0];
    let valueCol = columns.find(c => c.toLowerCase().includes('total') ||
        c.toLowerCase().includes('sum') ||
        c.toLowerCase().includes('count') ||
        c.toLowerCase().includes('amount')) || columns[1];

    if (!valueCol) valueCol = columns[columns.length - 1];

    const labels = rows.map(r => String(r[labelCol]));
    const data = rows.map(r => Number(r[valueCol]) || 0);

    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: valueCol,
                data: data,
                backgroundColor: 'rgba(102, 126, 234, 0.7)',
                borderColor: 'rgba(102, 126, 234, 1)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: true,
                    position: 'top'
                },
                title: {
                    display: true,
                    text: `${labelCol} vs ${valueCol}`
                }
            },
            scales: {
                y: {
                    beginAtZero: true
                }
            }
        }
    });
}

// Show tab
function showTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.getAttribute('onclick') && tab.getAttribute('onclick').includes(`'${tabName}'`)) {
            tab.classList.add('active');
        }
    });

    // Update content
    document.querySelectorAll('.tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById(`${tabName}Tab`).classList.add('active');
}

// Export data
async function exportData(format) {
    if (!currentResults || !currentQuery) {
        showStatus('No results to export', 'error');
        return;
    }

    showStatus(`Exporting as ${format.toUpperCase()}...`, 'loading');

    try {
        const response = await fetch('/query/export', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                format,
                columns: currentResults.columns,
                rows: currentResults.rows,
                query: currentQuery,
                sql: currentResults.generated_sql
            })
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `query_results_${Date.now()}.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);

            showStatus(`Exported successfully as ${format.toUpperCase()}`, 'success');
        } else {
            const data = await response.json();
            showStatus(`Export failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Export error: ${error.message}`, 'error');
    }
}

// Save current query
async function saveCurrentQuery() {
    const question = document.getElementById('question').value.trim();

    if (!question) {
        showStatus('No query to save', 'error');
        return;
    }

    const name = prompt('Enter a name for this query:');
    if (!name) return;

    try {
        const response = await fetch('/saved-queries', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                user_id: 'demo_user',
                name: name,
                question: question,
                description: ''
            })
        });

        const data = await response.json();

        if (response.ok) {
            showStatus('Query saved successfully!', 'success');
            loadSavedQueries();
        } else {
            showStatus(`Save failed: ${data.error}`, 'error');
        }
    } catch (error) {
        showStatus(`Save error: ${error.message}`, 'error');
    }
}

// Upload File
async function uploadFile(input) {
    if (!input.files || !input.files[0]) return;

    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);

    showStatus(`Uploading ${file.name}...`, 'loading');

    try {
        const response = await fetch('/upload', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok) {
            showStatus(`Success! Uploaded '${data.table}' with ${data.rows} rows.`, 'success');
            // Clear input so same file can be selected again if needed
            input.value = '';

            // Suggest a question
            document.getElementById('question').value = `Show me sample data from ${data.table}`;
            document.getElementById('question').focus();
        } else {
            const errorMsg = data.details ? `${data.error}: ${data.details}` : data.error;
            showStatus(`Upload failed: ${errorMsg}`, 'error');
        }
    } catch (error) {
        showStatus(`Upload error: ${error.message}`, 'error');
    }
}

// Load query history
async function loadQueryHistory() {
    try {
        const response = await fetch('/logs?limit=10');
        const data = await response.json();

        const container = document.getElementById('queryHistory');

        if (!data.logs || data.logs.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 0.85em;">No recent queries</p>';
            return;
        }

        let html = '';
        data.logs.slice(0, 10).forEach(log => {
            const timeAgo = getTimeAgo(new Date(log.timestamp));
            html += `
                <div class="history-item" onclick="loadQuery('${escapeHtml(log.question)}')">
                    <div class="history-question">${truncate(escapeHtml(log.question), 60)}</div>
                    <div class="history-meta">${timeAgo} • ${log.status}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load history:', error);
    }
}

// Load saved queries
async function loadSavedQueries() {
    try {
        const response = await fetch('/saved-queries?user_id=demo_user');
        const data = await response.json();

        const container = document.getElementById('savedQueries');

        if (!data.queries || data.queries.length === 0) {
            container.innerHTML = '<p style="color: #999; font-size: 0.85em;">No saved queries</p>';
            return;
        }

        let html = '';
        data.queries.forEach(query => {
            html += `
                <div class="saved-query-item" onclick="loadQuery('${escapeHtml(query.question)}')">
                    <div class="saved-query-name">${escapeHtml(query.name)}</div>
                    <div class="saved-query-question">${truncate(escapeHtml(query.question), 50)}</div>
                </div>
            `;
        });

        container.innerHTML = html;
    } catch (error) {
        console.error('Failed to load saved queries:', error);
    }
}

// Load quick stats
async function loadQuickStats() {
    try {
        const response = await fetch('/analytics/dashboard');
        const data = await response.json();

        const container = document.getElementById('quickStats');

        const stats = data.analytics;
        const successRate = stats.total_queries > 0
            ? ((stats.successful_queries / stats.total_queries) * 100).toFixed(0)
            : 0;

        container.innerHTML = `
            <div style="padding: 10px 0; border-bottom: 1px solid #eee;">
                <div>Total Queries: <strong>${stats.total_queries}</strong></div>
            </div>
            <div style="padding: 10px 0; border-bottom: 1px solid #eee;">
                <div>Avg Latency: <strong>${stats.avg_latency_ms.toFixed(0)}ms</strong></div>
            </div>
            <div style="padding: 10px 0;">
                <div>Success Rate: <strong>${successRate}%</strong></div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load stats:', error);
    }
}

// Load query into input
function loadQuery(question) {
    document.getElementById('question').value = question;
    document.getElementById('question').focus();
}

// Show status
function showStatus(message, type) {
    const statusEl = document.getElementById('status');
    statusEl.textContent = message;
    statusEl.className = `status-${type}`;
    statusEl.style.display = 'block';

    if (type !== 'loading') {
        setTimeout(() => {
            statusEl.style.display = 'none';
        }, 5000);
    }
}

// Show error
function showError(data) {
    let message = data.error || 'Unknown error';
    if (data.generated_sql) {
        message += `\n\nGenerated SQL:\n${data.generated_sql}`;
    }
    showStatus(message, 'error');
}

// Clear all
function clearAll() {
    document.getElementById('question').value = '';
    document.getElementById('results').style.display = 'none';
    document.getElementById('status').style.display = 'none';
    currentResults = null;
    currentQuery = null;

    if (chart) {
        chart.destroy();
        chart = null;
    }
}

// Check health
async function checkHealth() {
    try {
        const response = await fetch('/health');
        const data = await response.json();
        console.log('Health check:', data);
    } catch (error) {
        console.error('Health check failed:', error);
    }
}

// Utility functions
function formatValue(value) {
    if (value === null || value === undefined) {
        return '<span style="color: #ccc;">null</span>';
    }

    if (typeof value === 'number') {
        if (Number.isInteger(value)) {
            return value.toLocaleString();
        }
        return value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }

    return escapeHtml(String(value));
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncate(str, maxLen) {
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}

function getTimeAgo(date) {
    const seconds = Math.floor((new Date() - date) / 1000);

    if (seconds < 60) return 'Just now';
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
    if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
    return `${Math.floor(seconds / 86400)}d ago`;
}
