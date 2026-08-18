let allData = [];
let myChart = null; 
const START_HOUR = 8, END_HOUR = 20, ROW_HEIGHT = 70;

window.addEventListener('DOMContentLoaded', async () => {
    const path = window.location.pathname;
    await refreshGlobalData(); 

    let retryCount = 0;
    const checkDataAndInit = setInterval(() => {
        if (allData.length > 0 || retryCount > 20) {
            clearInterval(checkDataAndInit);
            console.log("Success: Global Data is ready. Initializing components...");

            if (path.includes('/visitor')) {
                if (typeof populateVisitorDropdowns === "function") populateVisitorDropdowns();
                renderVisitorTable(allData);
            } 
            else if (path.includes('/admin')) {

                if (typeof initAdminDashboard === "function") {
                    initAdminDashboard();
                }
            } 
            else if (path.includes('/instructor')) {
                if (typeof initInstructorPortal === "function") initInstructorPortal();
            }
        }
        retryCount++;
    }, 200); 
});

async function refreshGlobalData() {
    try {
        const response = await fetch('/get_initial_data');
        const data = await response.json();
        allData = (data && !data.error) ? data : (JSON.parse(localStorage.getItem('activeDataset')) || []);
        localStorage.setItem('activeDataset', JSON.stringify(allData));
    } catch (err) {
        console.error("Data Fetch Error, falling back to local storage:", err);
        allData = JSON.parse(localStorage.getItem('activeDataset')) || [];
    }
}

function renderVisitorTable(data) {
    const body = document.getElementById('vTableBody');
    if (!body) return;

    if (!data || data.length === 0) {
        body.innerHTML = '<tr><td colspan="7" class="text-center p-4 text-muted">No data available for this selection.</td></tr>';
        return;
    }
    
    body.innerHTML = data.map(item => {
        const activeDaysArr = getActiveDays(item);
        const daysString = activeDaysArr.length > 0 ? activeDaysArr.join(', ') : 'Online';
        const courseFullCode = `${item.Subject || ''} ${item.Catalog || ''}`;
        const mtgStart = item['Mtg Start'] || '';
        const mtgEnd = item['Mtg End'] || '';
        const timeString = mtgStart && mtgEnd ? `${mtgStart} - ${mtgEnd}` : mtgStart;

        return `
        <tr>
            <td><small>${item.Term || 'N/A'}</small></td>
            <td><b class="text-navy">${courseFullCode}</b></td> 
            <td class="text-start small">${item.Descr || 'N/A'}</td>
            <td>${item.Name || 'N/A'}</td>
            <td><span class="badge bg-light text-navy border">${item['Facil ID'] || 'N/A'}</span></td>
            <td><span class="small fw-bold text-secondary">${daysString}</span></td>
            
            <td><span class="tag-time">${timeString}</span></td>
        </tr>`;
    }).join('');
}

function hasCommonDay(a, b) {
    const days = ['Sun', 'Mon', 'Tues', 'Wed', 'Thurs'];
    return days.some(d => a[d] === 'Y' && b[d] === 'Y');
}

function getActiveDays(item) {
    let days = [];
    if (item.Sun === 'Y') days.push('Sun');
    if (item.Mon === 'Y') days.push('Mon');
    if (item.Tues === 'Y') days.push('Tue');
    if (item.Wed === 'Y') days.push('Wed');
    if (item.Thurs === 'Y') days.push('Thu');
    return days;
}