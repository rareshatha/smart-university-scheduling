let myFullData = []; 

const getCurrentProfID = () => localStorage.getItem('username'); 
const getCurrentProfName = () => localStorage.getItem('full_name'); 

async function initInstructorPortal() {
    let loggedInID = getCurrentProfID();
    let loggedInName = getCurrentProfName();

    if (!loggedInID || loggedInID === "undefined") {
        const courseListArea = document.getElementById('courseListArea');
        if (courseListArea) {
            courseListArea.innerHTML = '<span class="badge bg-danger text-white p-2">⚠️ Session identity lost. Please login again.</span>';
        }
        return;
    }

    setupModalListeners();

    const exportBtn = document.getElementById('exportInstructorCSV');
    if (exportBtn) {
        exportBtn.onclick = downloadInstructorCSV;
    }

    try {
        const res = await fetch('/get_initial_data');
        const fullDataset = await res.json();
        window.allData = fullDataset;

        if (!loggedInName || loggedInName === "undefined" || loggedInName === loggedInID) {
            const matchRecord = fullDataset.find(item => {
                const idInExcel = String(item['Instructor ID'] || item.InstID || item.ID || '').trim().toLowerCase();
                return idInExcel === String(loggedInID).trim().toLowerCase();
            });
            if (matchRecord) {
                loggedInName = matchRecord.Instructor || matchRecord.Name;
                localStorage.setItem('full_name', loggedInName);
            } else {
                loggedInName = loggedInID; 
            }
        }

        const profNameEl = document.getElementById('profName');
        const profIDEl = document.getElementById('profID');
        if (profNameEl) profNameEl.innerText = loggedInName.replace(/["']/g, "").trim();
        if (profIDEl) profIDEl.innerText = loggedInID;

        myFullData = fullDataset.filter(item => {
            const fieldsToTest = [item.Instructor, item.Name, item['Instructor Name'], item['Instructor ID'], item.InstID, item.ID];
            return fieldsToTest.some(val => matchInstructor(val, loggedInName, loggedInID));
        });
        
        const termSelect = document.getElementById('termSelect');
        if (termSelect) {
            const terms = [...new Set(myFullData.map(i => i.Term))].filter(Boolean).sort();
            if (terms.length === 0) {
                termSelect.innerHTML = '<option value="">No active Semesters Found</option>';
            } else {
                termSelect.innerHTML = terms.map(t => `<option value="${t}">${t}</option>`).join('');
                termSelect.onchange = filterByTerm;
                termSelect.selectedIndex = 0;
            }
        }
        
        filterByTerm();

    } catch (e) { console.error(e); }
}

function matchInstructor(itemField, loggedName, loggedID) {
    if (!itemField) return false;
    const cleanItem = String(itemField).replace(/["']/g, "").replace(/\s+/g, " ").trim().toLowerCase();
    const cleanLoggedName = String(loggedName).replace(/["']/g, "").replace(/\s+/g, " ").trim().toLowerCase();
    const cleanLoggedID = String(loggedID).replace(/\s+/g, "").trim().toLowerCase();
    if (cleanItem === cleanLoggedID || cleanItem === cleanLoggedName) return true;
    return false;
}

async function filterByTerm() {
    const termSelect = document.getElementById('termSelect');
    const selectedTerm = termSelect ? termSelect.value : "";

    if (!selectedTerm) return;

    const termData = myFullData.filter(i => String(i.Term).trim().toLowerCase() === String(selectedTerm).trim().toLowerCase());
    const courses = [...new Set(termData.map(i => i.Descr || i['Course Title'] || i.Subject))].filter(Boolean);
    
    const courseListArea = document.getElementById('courseListArea');
    if (courseListArea) {
        courseListArea.innerHTML = courses.length ? 
            courses.map(c => `<div class="course-item"><i class="fa fa-book-open me-2 small"></i>${c}</div>`).join('') :
            '<p class="text-muted small">No courses for this term.</p>';
    }
    
    if (document.getElementById('modalCourseSelect')) {
        document.getElementById('modalCourseSelect').innerHTML = courses.map(c => `<option value="${c}">${c}</option>`).join('');
        handleCourseSelectionChange();
    }

    let mappedGridMatrix = mapInstructorDataToEngine(termData);
    let instructorLocalConflicts = [];

    try {
        const response = await fetch('/get_instructor_requests');
        const allRequests = await response.json();
        
        const doctorRequests = allRequests.filter(req => 
            String(req.instructor_id).trim().toLowerCase() === String(getCurrentProfID()).trim().toLowerCase() &&
            String(req.term_code).trim().toLowerCase() === String(selectedTerm).trim().toLowerCase()
        );

        doctorRequests.forEach(req => {
            let fullDayName = req.requested_day || req.day;
            if (fullDayName === 'Sun') fullDayName = 'Sunday';
            if (fullDayName === 'Mon') fullDayName = 'Monday';
            if (fullDayName === 'Tues') fullDayName = 'Tuesday';
            if (fullDayName === 'Wed') fullDayName = 'Wednesday';
            if (fullDayName === 'Thurs') fullDayName = 'Thursday';

            const currentStatus = String(req.status).trim().toLowerCase();

            // 🌟 تأمين الحقول المفرومة وتثبيت الـ startTime والـ endTime لكي لا يقفز الوقت لـ 8:00
            if (currentStatus === 'rejected') {
                mappedGridMatrix.push({
                    courseName: req.course_name || "Requested Class",
                    courseCode: req.course_code_clean || req.course_code || "N/A",
                    instructorName: req.instructor_name || getCurrentProfName(),
                    instructorId: req.instructor_id || getCurrentProfID(),
                    roomNumber: req.requested_room || 'N/A',
                    section: req.class_section || "001",
                    day: fullDayName,
                    startTime: req.start_time || req.requested_time,
                    endTime: req.end_time || req.requested_end_time,
                    status: 'Rejected',
                    enrolledStudents: req.total_enrolled || 0,
                    roomCapacity: req.capacity || 30,
                    conflictDetail: req.adminNotes || req.note || "Administrative Rejection Note."
                });
                instructorLocalConflicts.push({ courseNameA: req.course_name, courseNameB: "__REJECTED__", detailText: req.adminNotes });
            } 
            else if (currentStatus === 'pending') {
                mappedGridMatrix.push({
                    courseName: req.course_name || "Pending Class",
                    courseCode: req.course_code_clean || req.course_code || "N/A",
                    instructorName: req.instructor_name || getCurrentProfName(),
                    instructorId: req.instructor_id || getCurrentProfID(),
                    roomNumber: req.requested_room || 'N/A',
                    section: req.class_section || "001",
                    day: fullDayName, 
                    startTime: req.start_time || req.requested_time, // القراءة الصحيحة من الباك إند
                    endTime: req.end_time || req.requested_end_time,
                    status: 'Pending', 
                    enrolledStudents: req.total_enrolled || 0,
                    roomCapacity: req.capacity || 30
                });
            }
            else if (currentStatus === 'approved') {
                mappedGridMatrix.push({
                    courseName: req.course_name,
                    courseCode: req.course_code_clean || req.course_code || "N/A",
                    instructorName: req.instructor_name || getCurrentProfName(),
                    instructorId: req.instructor_id || getCurrentProfID(),
                    roomNumber: req.requested_room || 'N/A',
                    section: req.class_section || "001",
                    day: fullDayName, 
                    startTime: req.start_time || req.requested_time,
                    endTime: req.end_time || req.requested_end_time,
                    status: 'Approved', 
                    enrolledStudents: req.total_enrolled || 0,
                    roomCapacity: req.capacity || 40
                });
            }
        });

    } catch (err) { console.warn(err); }
    
    calculateLocalConflicts(mappedGridMatrix, instructorLocalConflicts);

    if (typeof SUSTimeGridEngine !== 'undefined') {
        SUSTimeGridEngine.renderGrid('susTimeGridContainer', mappedGridMatrix, 'instructor', getCurrentProfID(), instructorLocalConflicts);
        window.currentInstructorGridData = mappedGridMatrix;
    }
}

function calculateLocalConflicts(matrix, conflictsArray) {
    const parse = (t) => { 
        if(!t) return 0; let clean = String(t).replace(/(AM|PM)/i, '').trim();
        const [h, m] = clean.split(':').map(Number); let fh = h;
        if (String(t).toUpperCase().includes('PM') && h < 12) fh += 12;
        if (String(t).toUpperCase().includes('AM') && h === 12) fh = 0;
        return fh * 60 + (m || 0); 
    };
    for(let i=0; i<matrix.length; i++) {
        for(let j=i+1; j<matrix.length; j++) {
            if(matrix[i].day === matrix[j].day && matrix[i].status !== 'Pending' && matrix[j].status !== 'Pending') {
                const s1 = parse(matrix[i].startTime), e1 = parse(matrix[i].endTime);
                const s2 = parse(matrix[j].startTime), e2 = parse(matrix[j].endTime);
                if(s1 < e2 && s2 < e1) {
                    conflictsArray.push({
                        courseNameA: matrix[i].courseName,
                        courseNameB: matrix[j].courseName,
                        detailText: `Overlap on timeline between [${matrix[i].courseName}] and [${matrix[j].courseName}].`
                    });
                }
            }
        }
    }
}

function mapInstructorDataToEngine(rawLines) {
    let mapped = [];
    rawLines.forEach(item => {
        const courseName = item['Course Title'] || item.Descr || 'N/A';
        const courseCode = `${item.Subject || ''}${item.Catalog || ''}`.trim() || 'N/A';
        const room = item.Room || item['Facil ID'] || 'ONLINE';
        const section = item.Section || item['Class Section'] || item['Class Sec'] || '001';
        
        let days = [];
        if (item.Sun === 'Y' || item.SUN === 'Y') days.push('Sunday');
        if (item.Mon === 'Y' || item.MON === 'Y') days.push('Monday');
        if (item.Tues === 'Y' || item.TUE === 'Y' || item.Tue === 'Y') days.push('Tuesday');
        if (item.Wed === 'Y' || item.WED === 'Y') days.push('Wednesday');
        if (item.Thurs === 'Y' || item.THU === 'Y' || item.Thu === 'Y') days.push('Thursday');

        days.forEach(d => {
            mapped.push({
                courseName: courseName,
                courseCode: courseCode,
                instructorName: getCurrentProfName(),
                instructorId: getCurrentProfID(),
                roomNumber: room,
                section: section,
                day: d,
                startTime: item['Start Time'] || item['Mtg Start'] || '',
                endTime: item['End Time'] || item['Mtg End'] || '',
                status: 'Approved',
                enrolledStudents: item['Tot Enrl'] || 0,
                roomCapacity: item['Cap Enrl'] || 40
            });
        });
    });
    return mapped;
}

function handleCourseSelectionChange() {
    const courseSelect = document.getElementById('modalCourseSelect');
    const sectionSelect = document.getElementById('modalSectionSelect');
    if (!courseSelect || !sectionSelect || !window.allData) return;
    
    const selectedCourse = courseSelect.value;
    const matchedSections = myFullData.filter(item => (item.Descr || item['Course Title'] || item.Subject) === selectedCourse);
    const sections = [...new Set(matchedSections.map(item => item.Section || item['Class Section'] || item['Class Sec'] || '001'))].filter(Boolean);
    
    if (sections.length === 0) {
        sectionSelect.innerHTML = '<option value="001">001 (Default)</option>';
    } else {
        sectionSelect.innerHTML = sections.map(sec => `<option value="${sec}">${sec}</option>`).join('');
    }
}

function setupModalListeners() {
    const daySelect = document.getElementById('modalDaySelect');
    const startSelect = document.getElementById('modalStartTimeSelect'); 
    const endSelect = document.getElementById('modalEndTimeSelect');
    
    if(daySelect) daySelect.onchange = loadAvailableRooms;
    if(startSelect) startSelect.onchange = loadAvailableRooms;
    if(endSelect) endSelect.onchange = loadAvailableRooms;
}

function loadAvailableRooms() {
    const daySelect = document.getElementById('modalDaySelect');
    const startSelect = document.getElementById('modalStartTimeSelect'); 
    const endSelect = document.getElementById('modalEndTimeSelect');     
    const roomSelect = document.getElementById('modalRoomSelect');       
    if (!daySelect || !startSelect || !endSelect || !roomSelect) return;
    if (!startSelect.value || !endSelect.value) return;

    const parse = (tStr) => { 
        if(!tStr) return 0; 
        let clean = String(tStr).trim().toUpperCase();
        let modifier = clean.includes('PM') ? 'PM' : 'AM';
        let [hours, minutes] = clean.replace(/(AM|PM)/g, '').trim().split(':').map(Number);
        if (modifier === 'PM' && hours < 12) hours += 12;
        if (modifier === 'AM' && hours === 12) hours = 0;
        return (hours * 60) + (minutes || 0); 
    };

    const reqStart = parse(startSelect.value);
    const reqEnd = parse(endSelect.value);
    const targetDay = daySelect.value;
    
    if (typeof window.allData === 'undefined' || window.allData.length === 0) return;

    const allRoomsInSystem = Array.from(new Set(window.allData.map(d => d.Room || d['Facil ID'] || d['Facility ID']))).filter(r => r && r !== 'ONLINE' && r !== 'PENDING ROOM');
    
    const roomCapacities = {};
    window.allData.forEach(d => {
        const r = d.Room || d['Facil ID'] || d['Facility ID'];
        if (r) roomCapacities[r] = d['Cap Enrl'] || d.Capacity || 35;
    });
    
    const busyRooms = [];
    window.allData.forEach(item => {
        let matchDay = false;
        if (targetDay === 'Sun' && (item.Sun === 'Y' || item.SUN === 'Y')) matchDay = true;
        if (targetDay === 'Mon' && (item.Mon === 'Y' || item.MON === 'Y')) matchDay = true;
        if (targetDay === 'Tues' && (item.Tues === 'Y' || item.TUE === 'Y' || item.Tue === 'Y')) matchDay = true;
        if (targetDay === 'Wed' && (item.Wed === 'Y' || item.WED === 'Y')) matchDay = true;
        if (targetDay === 'Thurs' && (item.Thurs === 'Y' || item.THU === 'Y' || item.Thu === 'Y')) matchDay = true;

        if (matchDay) {
            const itemStart = parse(item['Start Time'] || item['Mtg Start']);
            const itemEnd = parse(item['End Time'] || item['Mtg End']);
            const itemRoom = item.Room || item['Facil ID'] || item['Facility ID'];
            
            if ((reqStart < itemEnd && reqStart >= itemStart) || (reqStart < itemEnd && reqEnd > itemStart)) {
                if (itemRoom && !busyRooms.includes(itemRoom)) busyRooms.push(itemRoom);
            }
        }
    });
    
    const vacantRooms = allRoomsInSystem.filter(r => !busyRooms.includes(r));
    
    let optionsHTML = `<option value="ONLINE" style="color: #475569; font-weight: bold;">🌐 ONLINE (Virtual Class Slot)</option>`;
    if (vacantRooms.length === 0) {
        optionsHTML += `<option value="" disabled>❌ No physical empty rooms available for this timeframe!</option>`;
    } else {
        vacantRooms.forEach(r => {
            optionsHTML += `<option value="${r}">🚪 Room ${r} (Vacant | Capacity: ${roomCapacities[r] || 35} students)</option>`;
        });
    }
    roomSelect.innerHTML = optionsHTML;
}

function saveNewRequest() {
    const courseSelect = document.getElementById('modalCourseSelect');
    const sectionSelect = document.getElementById('modalSectionSelect');
    const daySelect = document.getElementById('modalDaySelect');
    const startSelect = document.getElementById('modalStartTimeSelect');
    const endSelect = document.getElementById('modalEndTimeSelect');
    const roomSelect = document.getElementById('roomSelect') || document.getElementById('modalRoomSelect');
    const notesTextArea = document.getElementById('modalNotes');
    const termSelect = document.getElementById('termSelect');

    if(!startSelect.value || !endSelect.value) return alert("Please set complete Start and End time");

    const activeCourseRow = myFullData.find(item => 
        (item.Descr || item['Course Title'] || item.Subject) === courseSelect.value &&
        String(item.Section || item['Class Section'] || item['Class Sec'] || '001').trim() === String(sectionSelect.value).trim()
    );

    const realCourseCode = activeCourseRow ? `${activeCourseRow.Subject || ''}${activeCourseRow.Catalog || ''}`.trim() : "N/A";
    const realEnrolled = activeCourseRow ? (activeCourseRow['Tot Enrl'] || 0) : 0;
    const realCapacity = activeCourseRow ? (activeCourseRow['Cap Enrl'] || 25) : 25;


const payload = {
    instructor_id: getCurrentProfID(),
    instructor_name: getCurrentProfName(),
    course_code: realCourseCode,
    course_name: courseSelect.value, 
    class_section: sectionSelect.value, 
    requested_day: daySelect.value,
    start_time: startSelect.value,
    end_time: endSelect.value, 
    requested_room: roomSelect.value,
    total_enrolled: realEnrolled,
    capacity: realCapacity,
    note: notesTextArea.value.trim(),
    term_code: termSelect ? termSelect.value : ""
};

    fetch('/submit_instructor_request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(result => {
        alert(`🎉 Request successfully recorded!`);
        bootstrap.Modal.getInstance(document.getElementById('requestModal')).hide();
        document.getElementById('slotRequestForm').reset();
        initInstructorPortal(); 
    })
    .catch(() => alert("Failed to submit request to server."));
}

function downloadInstructorCSV() {
    if (!window.currentInstructorGridData || window.currentInstructorGridData.length === 0) {
        return alert("No active schedule available currently to export.");
    }
    if (typeof SUSTimeGridEngine !== 'undefined') {
        SUSTimeGridEngine.exportToCSV(`Instructor_${getCurrentProfID()}_Schedule.csv`, window.currentInstructorGridData);
    }
}

window.onload = initInstructorPortal;