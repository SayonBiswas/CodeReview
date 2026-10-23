let clientId = localStorage.getItem('clientId');
if (!clientId) {
    clientId = crypto.randomUUID();
    localStorage.setItem('clientId', clientId);
}

// Check if this is a rescan
const parentSessionId = sessionStorage.getItem('parentSessionId');
if (parentSessionId) {
    const lastCode = sessionStorage.getItem('lastCode');
    const lastLanguage = sessionStorage.getItem('lastLanguage');
    const lastReviewType = sessionStorage.getItem('lastReviewType');
    const lastRequirements = sessionStorage.getItem('lastRequirements');

    if (lastCode) {
        document.getElementById('code').value = lastCode;
    }
    if (lastLanguage) {
        document.getElementById('language').value = lastLanguage;
    }
    if (lastReviewType) {
        document.getElementById('reviewType').value = lastReviewType;
    }
    if (lastRequirements) {
        document.getElementById('requirements').value = lastRequirements;
    }
}

document.getElementById('scanBtn').addEventListener('click', async () => {
    const code = document.getElementById('code').value;
    const language = document.getElementById('language').value;
    const reviewType = document.getElementById('reviewType').value;
    const requirements = document.getElementById('requirements').value;

    const errorDiv = document.getElementById('error');
    const loadingDiv = document.getElementById('loading');
    const scanBtn = document.getElementById('scanBtn');

    errorDiv.classList.add('hidden');
    loadingDiv.classList.remove('hidden');
    scanBtn.disabled = true;

    try {
        const requestBody = {
            code,
            language,
            review_type: reviewType,
            requirements: requirements || undefined
        };

        const currentParentId = sessionStorage.getItem('parentSessionId');
        if (currentParentId) {
            requestBody.parent_session_id = currentParentId;
            sessionStorage.removeItem('parentSessionId');
        }

        const response = await fetch('/scan', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Client-ID': clientId
            },
            body: JSON.stringify(requestBody)
        });

        if (response.ok) {
            const data = await response.json();
            sessionStorage.setItem('currentSession', JSON.stringify(data));
            sessionStorage.setItem('lastCode', code);
            sessionStorage.setItem('lastLanguage', language);
            sessionStorage.setItem('lastReviewType', reviewType);
            sessionStorage.setItem('lastRequirements', requirements || '');
            window.location.href = '/static/review.html';
        } else {
            const errorData = await response.json();
            errorDiv.textContent = errorData.detail || 'Scan failed';
            errorDiv.classList.remove('hidden');
        }
    } catch (error) {
        errorDiv.textContent = 'Network error. Please try again.';
        errorDiv.classList.remove('hidden');
    } finally {
        loadingDiv.classList.add('hidden');
        scanBtn.disabled = false;
    }
});
