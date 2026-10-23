const clientId = localStorage.getItem('clientId');
const sessionData = JSON.parse(sessionStorage.getItem('currentSession'));

if (!sessionData) {
    window.location.href = '/static/index.html';
}

let itemIds = {};

async function loadSessionDetails() {
    try {
        const response = await fetch(`/session/${sessionData.session_id}`, {
            headers: {
                'X-Client-ID': clientId
            }
        });

        if (response.ok) {
            const data = await response.json();
            data.findings.forEach(f => {
                itemIds[`${f.category}_${f.title}`] = f.id;
            });
        }
    } catch (error) {
        console.error('Failed to load session details');
    }
}

function renderReview() {
    document.getElementById('score').textContent = sessionData.overall_score;
    document.getElementById('grade').textContent = sessionData.grade;
    document.getElementById('totalFindings').textContent = sessionData.findings.length;
    document.getElementById('aiStatus').textContent = sessionData.ai_status;

    if (sessionData.comparison) {
        document.getElementById('comparison').classList.remove('hidden');
        document.getElementById('resolvedCount').textContent = sessionData.comparison.resolved.length;
        document.getElementById('stillOpenCount').textContent = sessionData.comparison.still_open.length;
        document.getElementById('newCount').textContent = sessionData.comparison.new.length;
    }

    const findingsList = document.getElementById('findingsList');
    const severityColors = {
        'Critical': 'bg-red-600',
        'High': 'bg-orange-600',
        'Medium': 'bg-yellow-600',
        'Low': 'bg-green-600'
    };

    findingsList.innerHTML = sessionData.findings.map((finding, index) => `
        <div class="mb-4 bg-gray-700 rounded p-4 finding-card" data-index="${index}">
            <div class="flex justify-between items-start mb-2">
                <span class="px-2 py-1 rounded text-xs font-bold ${severityColors[finding.severity] || 'bg-gray-600'}">${finding.severity}</span>
                <span class="text-gray-400 text-sm">Line ${finding.line_no || 'N/A'}</span>
            </div>
            <h3 class="font-bold text-lg mb-1">${finding.title}</h3>
            <p class="text-gray-300 text-sm mb-2">${finding.description}</p>
            <p class="text-gray-400 text-sm mb-2"><strong>Fix:</strong> ${finding.fix}</p>
            ${finding.ai_explanation ? `
                <div class="bg-gray-800 rounded p-3 mt-2">
                    <p class="text-blue-400 text-sm font-bold mb-1">AI Explanation:</p>
                    <p class="text-gray-300 text-sm">${finding.ai_explanation}</p>
                </div>
            ` : ''}
            ${finding.fix_code ? `
                <div class="bg-gray-800 rounded p-3 mt-2">
                    <p class="text-green-400 text-sm font-bold mb-1">Code Fix:</p>
                    <pre class="text-gray-300 text-sm overflow-x-auto"><code>${finding.fix_code}</code></pre>
                </div>
            ` : ''}
            <div class="mt-3">
                <select class="status-select bg-gray-600 text-white rounded px-3 py-1 text-sm" onchange="updateStatus(${index}, this.value)">
                    <option value="open" ${finding.status === 'open' ? 'selected' : ''}>Open</option>
                    <option value="acknowledged" ${finding.status === 'acknowledged' ? 'selected' : ''}>Acknowledged</option>
                    <option value="in_progress" ${finding.status === 'in_progress' ? 'selected' : ''}>In Progress</option>
                    <option value="resolved" ${finding.status === 'resolved' ? 'selected' : ''}>Resolved</option>
                    <option value="ignored" ${finding.status === 'ignored' ? 'selected' : ''}>Ignored</option>
                </select>
            </div>
        </div>
    `).join('');
}

async function updateStatus(index, status) {
    const finding = sessionData.findings[index];
    const key = `${finding.category}_${finding.title}`;
    const itemId = itemIds[key];

    if (!itemId) {
        alert('Unable to update status - item ID not found');
        return;
    }

    try {
        const response = await fetch(`/issue/${itemId}`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'X-Client-ID': clientId
            },
            body: JSON.stringify({ status })
        });

        if (!response.ok) {
            alert('Failed to update status');
        } else {
            finding.status = status;
        }
    } catch (error) {
        alert('Error updating status');
    }
}

document.getElementById('downloadPdf').addEventListener('click', async () => {
    try {
        const response = await fetch(`/report/${sessionData.session_id}/pdf`, {
            headers: {
                'X-Client-ID': clientId
            }
        });

        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `report_${sessionData.session_id}.pdf`;
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
        } else {
            alert('Failed to download PDF');
        }
    } catch (error) {
        alert('Error downloading PDF');
    }
});

document.getElementById('rescanBtn').addEventListener('click', () => {
    sessionStorage.setItem('parentSessionId', sessionData.session_id);
    window.location.href = '/static/index.html';
});

loadSessionDetails().then(renderReview);
