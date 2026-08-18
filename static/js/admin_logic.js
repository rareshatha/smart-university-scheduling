let currentSearchMatches = [];
let isSearchMode = false; 
let archivedRequests = JSON.parse(localStorage.getItem('archivedRequests')) || [];
let activeFilteredData = []; 
let GlobalCalculatedConflicts = []; 

function initAdminDashboard() {
    console.log("SUS System: Master Dashboard Engaged.");
    
    const termSelect = document.getElementById('termSelect');
    const dFilter = document.getElementById('deptFilter');
    const searchBtn = document.getElementById('deepSearchBtn');
    const exportExcelBtn = document.getElementById('exportExcelBtn');
    const closeGridBtn = document.getElementById('closeGridPanelBtn');
    const exportRegistryCSVBtn = document.getElementById('exportRegistryCSVBtn');
    
    if (termSelect) termSelect.onchange = updateDashboard;
    if (dFilter) dFilter.onchange = updateDashboard;
    
    if (searchBtn) {
        searchBtn.onclick = () => {
            const searchInput = document.getElementById('globalSearchInput');
            const query = searchInput ? searchInput.value.trim().toLowerCase() : '';
            handleExplicitSearch(query);
        };
    }

    if (closeGridBtn) {
        closeGridBtn.onclick = hideVisualContainers;
    }

    if (exportExcelBtn) {
        exportExcelBtn.onclick = () => {
            const data = isSearchMode ? currentSearchMatches : activeFilteredData;
            if (typeof SUSTimeGridEngine !== 'undefined') {
                SUSTimeGridEngine.exportToCSV('SUS_Filtered_TimeGrid_Schedule.csv', data);
            }
        };
    }

    if (exportRegistryCSVBtn) {
        exportRegistryCSVBtn.onclick = () => {
            if (typeof SUSTimeGridEngine !== 'undefined') {
                SUSTimeGridEngine.exportToCSV('SUS_Complete_Academic_Registry.csv', activeFilteredData);
            }
        };
    }
    
    updateDashboard(); 
    loadIncomingRequests(); 
}

function updateDashboard() {
    const termElement = document.getElementById('termSelect');
    const deptElement = document.getElementById('deptFilter');
    
    const selectedTerm = termElement ? termElement.value : "Fall 2024 - 2421";
    const selectedDept = deptElement ? deptElement.value : 'all';

    if (typeof allData === 'undefined' || !allData) return;

    let filteredData = allData.filter(d => 
        String(d.Term).trim().toLowerCase() === String(selectedTerm).replace('.xlsx', '').trim().toLowerCase() ||
        String(d.sourceFile).trim().toLowerCase() === String(selectedTerm).trim().toLowerCase()
    );
    
    if (selectedDept !== 'all') {
        filteredData = filteredData.filter(d => d.Subject === selectedDept);
    }

    const newCourses = new Set(filteredData.map(d => d['Course Title'] || d.Descr || 'N/A')).size;
    const newRooms = new Set(filteredData.map(d => d.Room || d['Facil ID'] || 'ONLINE')).size;
    const newInstructors = new Set(filteredData.map(d => d['Instructor'] || d.Name || 'UNKNOWN')).size;

    animateValue("totalCourses", parseInt(document.getElementById('totalCourses').innerText) || 0, newCourses, 1000);
    animateValue("totalRooms", parseInt(document.getElementById('totalRooms').innerText) || 0, newRooms, 1000);
    animateValue("totalInstructors", parseInt(document.getElementById('totalInstructors').innerText) || 0, newInstructors, 1000);

    activeFilteredData = mapDataToEngineStructure(filteredData);

    generateDetailedConflictLog(filteredData);

    fillRegistryTable(activeFilteredData);

    if (!isSearchMode) {
        const container = document.getElementById('visualGridWrapperPanel');
        if(container) container.style.display = 'none';
    } else {
        const searchInput = document.getElementById('globalSearchInput');
        if (searchInput && searchInput.value.trim() !== '') {
            handleExplicitSearch(searchInput.value.trim().toLowerCase());
        } else {
            hideVisualContainers();
        }
    }

    renderAdminChartByDays(filteredData);
}

function handleExplicitSearch(query) {
    const container = document.getElementById('visualGridWrapperPanel');
    
    if (!query) {
        alert("Please enter an Instructor name, Course Title, or Room number to execute search!");
        return;
    }

    isSearchMode = true;
    currentSearchMatches = activeFilteredData.filter(slot => 
        slot.instructorName.toLowerCase().includes(query) ||
        slot.courseName.toLowerCase().includes(query) ||
        slot.roomNumber.toLowerCase().includes(query)
    );

    if(container) {
        container.style.display = 'block';
        setTimeout(() => {
            container.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }, 100);
    }
 
    if (typeof SUSTimeGridEngine !== 'undefined') {
        SUSTimeGridEngine.renderGrid('susTimeGridContainer', currentSearchMatches, 'admin', null, GlobalCalculatedConflicts);
    }
}

function hideVisualContainers() {
    isSearchMode = false;
    const container = document.getElementById('visualGridWrapperPanel');
    if(container) container.style.display = 'none';
    
    const searchInput = document.getElementById('globalSearchInput');
    if(searchInput) searchInput.value = '';
}

function fillRegistryTable(data) {
    const tableBody = document.getElementById('vTableBody');
    if (!tableBody) return;
    tableBody.innerHTML = '';

    if (data.length === 0) {
        tableBody.innerHTML = '<tr><td colspan="9" class="text-center text-muted">No academic registry rows available for current parameters.</td></tr>';
        return;
    }

    data.forEach(item => {
        const row = document.createElement('tr');
        row.innerHTML = `
            <td>Current Term</td>
            <td class="fw-bold text-navy">${item.courseCode}</td>
            <td class="text-start small">${item.courseName}</td>
            <td><code>${item.section}</code></td>
            <td>${item.instructorName}</td>
            <td class="text-secondary small">${item.instructorId}</td>
            <td><span class="badge bg-light text-dark border px-2 py-1">${item.roomNumber}</span></td>
            <td class="fw-semibold text-secondary small">${item.day}</td>
            <td><span class="badge bg-secondary-subtle text-secondary fw-bold px-2 py-1">${item.startTime} - ${item.endTime}</span></td>
        `;
        tableBody.appendChild(row);
    });
}

function mapDataToEngineStructure(rawLines) {
    let mapped = [];
    rawLines.forEach(item => {
        const sectionNo = item.Section || item.ClassSec || item['Class Section'] || '001';
        const courseName = item['Course Title'] || item.Descr || 'N/A';
        const courseCode = `${item.Subject || ''}${item.Catalog || ''}`.trim() || 'N/A';
        const instructorName = item.Instructor || item.Name || 'UNKNOWN';
        const instID = item['Instructor ID'] || item.InstID || item.ID || 'N/A';
        const room = item.Room || item['Facil ID'] || 'ONLINE';

        let days = [];
        if (item.Sun === 'Y' || item.SUN === 'Y') days.push('Sunday');
        if (item.Mon === 'Y' || item.MON === 'Y') days.push('Monday');
        if (item.Tues === 'Y' || item.TUE === 'Y' || item.Tue === 'Y') days.push('Tuesday');
        if (item.Wed === 'Y' || item.WED === 'Y') days.push('Wednesday');
        if (item.Thurs === 'Y' || item.THU === 'Y' || item.Thu === 'Y') days.push('Thursday');

        days.forEach(d => {
            mapped.push({
                courseName: courseName, courseCode: courseCode, instructorName: instructorName, instructorId: instID, roomNumber: room, section: sectionNo, day: d, startTime: item['Start Time'] || item['Mtg Start'] || '', endTime: item['End Time'] || item['Mtg End'] || '', status: 'Approved', enrolledStudents: item['Tot Enrl'] || 0, roomCapacity: item['Cap Enrl'] || 40
            });
        });
    });
    return mapped;
}

function generateDetailedConflictLog(data) {
    const conflictBox = document.getElementById('conflictBox');
    if (!conflictBox) return;
    GlobalCalculatedConflicts = [];
    let conflictsFound = [];
    
    const parse = (t) => { 
        if(!t) return 0; 
        let cleanT = String(t).replace(/(AM|PM)/i, '').trim();
        const [h, m] = cleanT.split(':').map(Number); 
        let finalH = h;
        if (String(t).toUpperCase().includes('PM') && h < 12) finalH += 12;
        if (String(t).toUpperCase().includes('AM') && h === 12) finalH = 0;
        return finalH * 60 + (m || 0); 
    };

    for (let i = 0; i < data.length; i++) {
        for (let j = i + 1; j < data.length; j++) {
            const itemA = data[i]; const itemB = data[j];
            let hasCommonDay = (itemA.Sun === 'Y' && itemB.Sun === 'Y') || (itemA.Mon === 'Y' && itemB.Mon === 'Y') || (itemA.Tues === 'Y' && itemB.Tues === 'Y') || (itemA.Wed === 'Y' && itemB.Wed === 'Y') || (itemA.Thurs === 'Y' && itemB.Thurs === 'Y');
            if (hasCommonDay) {
                const s1 = parse(itemA['Start Time'] || itemA['Mtg Start']); const e1 = parse(itemA['End Time'] || itemA['Mtg End']);
                const s2 = parse(itemB['Start Time'] || itemB['Mtg Start']); const e2 = parse(itemB['End Time'] || itemB['Mtg End']);
                if (s1 < e2 && s2 < e1) {
                    const roomA = itemA.Room || itemA['Facil ID'] || 'ONLINE'; const roomB = itemB.Room || itemB['Facil ID'] || 'ONLINE';
                    const nameA = itemA['Course Title'] || itemA.Descr || 'N/A'; const nameB = itemB['Course Title'] || itemB.Descr || 'N/A';
                    const instrA = itemA.Instructor || itemA.Name; const instrB = itemB.Instructor || itemB.Name;
                    if (roomA !== 'ONLINE' && roomA === roomB) {
                        const msg = `Room Conflict: Room ${roomA} is doubly booked for [${nameA}] and [${nameB}].`;
                        conflictsFound.push({ type: 'Room Conflict', detail: `Room <b>${roomA}</b> for [${nameA}] & [${nameB}].` });
                        GlobalCalculatedConflicts.push({ courseNameA: nameA, courseNameB: nameB, detailText: msg });
                    }
                    if (instrA && instrA !== 'UNKNOWN' && instrA === instrB) {
                        const msg = `Instructor Conflict: Dr. ${instrA} has overlapping classes.`;
                        conflictsFound.push({ type: 'Instructor Conflict', detail: `Dr. <b>${instrA}</b> overlapping ([${nameA}] & [${nameB}]).` });
                        GlobalCalculatedConflicts.push({ courseNameA: nameA, courseNameB: nameB, detailText: msg });
                    }
                }
            }
        }
    }
    if (conflictsFound.length === 0) {
        conflictBox.innerHTML = `<div class="text-center p-3 text-success fw-bold"><span>All Constraints Resolved!</span></div>`;
    } else {
        conflictBox.innerHTML = conflictsFound.map(c => `<div class="conflict-item p-2 mb-1 border-start border-3 ${c.type === 'Room Conflict' ? 'border-danger bg-light' : 'border-warning bg-light'} small"><b>${c.type}:</b> ${c.detail}</div>`).join('');
    }
}

function loadIncomingRequests() {
    const requestBox = document.getElementById('requestBox'); 
    if (!requestBox) return;

    fetch('http://127.0.0.1:5001/get_instructor_requests')
    .then(res => {
        if (!res.ok) throw new Error("API Network error");
        return res.json();
    })
    .then(requests => {
        requestBox.innerHTML = ''; 
        
        if (!requests || requests.length === 0) { 
            requestBox.innerHTML = '<div class="p-3 text-muted small text-center"><i class="fa-regular fa-folder-open me-1"></i> No incoming slot requests at the moment.</div>'; 
            return; 
        }

        requests.forEach((req, index) => {
            if(archivedRequests.some(archived => archived.timestamp === req.timestamp && archived.instructor_id === req.instructor_id)) {
                return;
            }

            const div = document.createElement('div'); 
            div.className = "request-item p-3 mb-2 border-start border-3 border-warning bg-light small animate__animated animate__fadeIn";
            
            const serializedReq = JSON.stringify(req).replace(/"/g, '&quot;');

            div.innerHTML = `
                <div class="d-flex justify-content-between align-items-center mb-1">
                    <b class="text-navy"><i class="fa fa-user-tie me-1"></i> ${req.instructor_name || 'Professor'}</b>
                    <span class="badge bg-secondary-subtle text-secondary" style="font-size: 0.72rem;">${req.timestamp || ''}</span>
                </div>
                <p class="mb-1 text-dark">Requested to assign <b>${req.course_name || req.course_code}</b> to Room <b>${req.requested_room || 'N/A'}</b>.</p>
                <div class="text-muted mb-2" style="font-size: 0.72rem;">
                    <i class="fa-regular fa-clock me-1"></i> Slot: ${req.requested_day || req.day || ''} (${req.requested_time || req.start_time || ''})
                </div>
                
                <div class="input-group input-group-sm mb-2">
                    <input type="text" id="note-${index}" class="form-control form-control-sm" placeholder="Write adjustment or rejection notes here...">
                </div>
                <div class="d-flex gap-2 justify-content-end">
                    <button class="btn btn-sm btn-success px-3 fw-bold" onclick="processRequestAction(${index}, '${serializedReq}', 'Approved')">Approve</button>
                    <button class="btn btn-sm btn-danger px-3 fw-bold" onclick="processRequestAction(${index}, '${serializedReq}', 'Rejected')">Reject</button>
                </div>
            `;
            requestBox.appendChild(div);
        });

        if(requestBox.innerHTML === '') {
            requestBox.innerHTML = '<div class="p-3 text-muted small text-center"><i class="fa-regular fa-folder-open me-1"></i> All incoming requests have been handled.</div>';
        }
    })
    .catch(error => {
        console.warn("[SUS Requests API] Server offline, rendering static fallback storage.");
        requestBox.innerHTML = '<div class="p-3 text-muted small text-center"><i class="fa-regular fa-folder-open me-1"></i> No incoming slot requests at the moment.</div>'; 
    });
}

function processRequestAction(index, escapedRequestStr, actionStatus) {
    const requestData = JSON.parse(escapedRequestStr.replace(/&quot;/g, '"'));
    const noteInput = document.getElementById(`note-${index}`);
    const adminNote = noteInput ? noteInput.value.trim() : "";

    const finalizedDecision = {
        ...requestData,
        status: actionStatus,
        adminNotes: adminNote || "No administrative notes provided.",
        processedAt: new Date().toLocaleString()
    };

    archivedRequests.push(finalizedDecision);
    localStorage.setItem('archivedRequests', JSON.stringify(archivedRequests));

    fetch('http://127.0.0.1:5001/update_request_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(finalizedDecision)
    })
    .then(res => res.json())
    .then(serverResult => {
        console.log("[SUS Backend Pipeline Check]:", serverResult.message);
    })
    .catch(err => console.warn("Failed to sync request status with Flask server database."));

    if (actionStatus === 'Approved') {
        let fullDayName = requestData.requested_day || requestData.day;
        if (fullDayName === 'Sun') fullDayName = 'Sunday';
        if (fullDayName === 'Mon') fullDayName = 'Monday';
        if (fullDayName === 'Tues') fullDayName = 'Tuesday';
        if (fullDayName === 'Wed') fullDayName = 'Wednesday';
        if (fullDayName === 'Thurs') fullDayName = 'Thursday';

        activeFilteredData.push({
            courseName: requestData.course_name,
            courseCode: requestData.course_code_clean || requestData.course_code || 'N/A',
            instructorName: requestData.instructor_name,
            instructorId: requestData.instructor_id,
            roomNumber: requestData.requested_room,
            section: requestData.class_section || '001',
            day: fullDayName,
            startTime: requestData.start_time || requestData.requested_time,
            endTime: requestData.end_time || requestData.requested_end_time,
            status: 'Approved',
            enrolledStudents: requestData.total_enrolled || 0,
            roomCapacity: requestData.capacity || 40
        });
    }

    if (isSearchMode) {
        const searchInput = document.getElementById('globalSearchInput');
        if (searchInput && searchInput.value.trim() !== '') {
            handleExplicitSearch(searchInput.value.trim().toLowerCase());
        }
    } else {
        fillRegistryTable(activeFilteredData);
    }
    
    loadIncomingRequests();
    alert(`🎉 Request marked as [${actionStatus}] successfully and piped into Matrix!`);
}

function animateValue(id, start, end, duration) {
    const obj = document.getElementById(id); if (!obj) return;
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp; const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerHTML = Math.floor(progress * (end - start) + start); if (progress < 1) window.requestAnimationFrame(step); else obj.innerHTML = end;
    };
    window.requestAnimationFrame(step);
}

function renderAdminChartByDays(data) {
    const canvas = document.getElementById('loadChart'); if (!canvas) return; const ctx = canvas.getContext('2d');
    const hours = ['08:00', '10:00', '12:00', '14:00', '16:00', '18:00', '20:00'];
    const getDayData = (dayKey) => hours.map(h => data.filter(d => (d[dayKey] === 'Y' || d[dayKey.toUpperCase()] === 'Y') && String(d['Start Time'] || d['Mtg Start']).includes(h)).length);
    if (window.myChart instanceof Chart) {
        window.myChart.data.datasets[0].data = getDayData('Sun'); window.myChart.data.datasets[1].data = getDayData('Mon'); window.myChart.data.datasets[2].data = getDayData('Tues'); window.myChart.data.datasets[3].data = getDayData('Wed'); window.myChart.data.datasets[4].data = getDayData('Thurs'); window.myChart.update(); 
    } else {
        window.myChart = new Chart(ctx, { type: 'line', data: { labels: hours, datasets: [{ label: 'SUN', data: getDayData('Sun'), borderColor: '#ff6384', tension: 0.4 }, { label: 'MON', data: getDayData('Mon'), borderColor: '#36a2eb', tension: 0.4 }, { label: 'TUE', data: getDayData('Tues'), borderColor: '#ffce56', tension: 0.4 }, { label: 'WED', data: getDayData('Wed'), borderColor: '#4bc0c0', tension: 0.4 }, { label: 'THU', data: getDayData('Thurs'), borderColor: '#9966ff', tension: 0.4 }] }, options: { responsive: true, maintainAspectRatio: false } });
    }
}