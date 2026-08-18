const SUSTimeGridEngine = {
    days: ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday'],
    visibleHours: [
        '08:00 AM', '09:00 AM', '10:00 AM', '11:00 AM', '12:00 PM', '01:00 PM', 
        '02:00 PM', '03:00 PM', '04:00 PM', '05:00 PM', '06:00 PM', '07:00 PM', 
        '08:00 PM', '09:00 PM', '10:00 PM'
    ],
    
    dayStartMinutes: 8 * 60,  
    dayEndMinutes: 22 * 60,  
    minuteStep: 10,

    injectStyles: function() {
        if (document.getElementById('sus-engine-styles')) return;
        const style = document.createElement('style');
        style.id = 'sus-engine-styles';
        style.innerHTML = `
            .sus-grid-outer-container {
                display: grid;
                grid-template-columns: 100px 1fr;
                background-color: #ffffff;
                border: 1px solid #e2e8f0;
                border-radius: 12px;
                overflow: hidden;
                font-family: system-ui, -apple-system, sans-serif;
                box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
            }
            .sus-time-axis { display: grid; background-color: #f8fafc; border-right: 1px solid #e2e8f0; }
            .sus-axis-header { background-color: #0f172a; color: #f8fafc; text-align: center; padding: 16px 0; font-weight: 700; font-size: 0.85rem; height: 50px; }
            .sus-time-label-block { display: flex; align-items: start; justify-content: center; color: #64748b; font-size: 0.78rem; font-weight: 700; padding-top: 4px; box-sizing: border-box; border-bottom: 1px solid rgba(226, 232, 240, 0.4); }
            .sus-days-container { display: grid; grid-template-columns: repeat(5, minmax(160px, 1fr)); background-color: #ffffff; position: relative; }
            .sus-day-column-header { background-color: #0f172a; color: #f8fafc; text-align: center; padding: 16px 8px; font-weight: 700; font-size: 0.85rem; height: 50px; border-left: 1px solid #1e293b; }
            .sus-day-grid-overlay { position: absolute; top: 50px; left: 0; right: 0; bottom: 0; display: grid; grid-template-columns: repeat(5, 1fr); pointer-events: none; }
            .sus-grid-day-wire { border-right: 1px solid rgba(226, 232, 240, 0.5); position: relative; }
            .sus-grid-hour-wire { position: absolute; left: 0; right: 0; border-bottom: 1px solid rgba(241, 245, 249, 0.9); }
            .sus-cards-content-layer { position: absolute; top: 50px; left: 0; right: 0; bottom: 0; display: grid; grid-template-columns: repeat(5, 1fr); }
            .sus-day-card-lane { position: relative; height: 100%; border-right: 1px solid rgba(226, 232, 240, 0.3); }

            .sus-absolute-card { position: absolute; left: 4px; right: 4px; border-radius: 8px; padding: 10px; box-sizing: border-box; display: flex; flex-direction: column; justify-content: flex-start; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.04); cursor: pointer; transition: all 0.15s ease; }
            .sus-absolute-card:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.08); z-index: 100; }
            
            /* الكروت بحالاتها الثلاث اللوجستية المعتمدة */
            .sus-card-approved { background-color: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #16a34a; color: #14532d; }
            .sus-card-pending { background-color: #fef9c3; border: 2px dashed #facc15; border-left: 5px solid #eab308; color: #713f12; }
            .sus-card-conflict { background-color: #fef2f2; border: 1px solid #fca5a5; border-left: 5px solid #dc2626; color: #7f1d1d; animation: pulse-conflict 2s infinite; }
            
            @keyframes pulse-conflict {
                0% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0.2); }
                50% { box-shadow: 0 0 0 4px rgba(220, 38, 38, 0); }
                100% { box-shadow: 0 0 0 0 rgba(220, 38, 38, 0); }
            }

            .sus-card-title { font-weight: 700; font-size: 0.8rem; margin-bottom: 4px; text-overflow: ellipsis; white-space: nowrap; overflow: hidden; }
            .sus-card-meta { font-size: 0.7rem; color: #475569; font-weight: 500; margin-bottom: 1px; }
            .sus-status-text { font-size: 0.65rem; font-weight: 700; text-transform: uppercase; margin-top: auto; }

            /* نافذة المعلومات العائمة Tooltip */
            .sus-tooltip { position: absolute; background-color: #1e293b; color: #f8fafc; padding: 12px 16px; border-radius: 8px; font-size: 0.75rem; line-height: 1.5; z-index: 9999; box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.3); width: 280px; pointer-events: none; display: none; border: 1px solid #475569; }
            .sus-tooltip strong { color: #38bdf8; }
            .sus-tooltip .tooltip-conflict-alert { color: #f87171; background-color: rgba(220, 38, 38, 0.2); padding: 4px 6px; border-radius: 4px; margin-top: 5px; font-weight: bold; border-left: 3px solid #dc2626; }
        `;
        document.head.appendChild(style);
    },

    getMinutesFromStart: function(timeStr) {
        let clean = String(timeStr).trim().toUpperCase();
        let modifier = clean.includes('PM') ? 'PM' : 'AM';
        let [hours, minutes] = clean.replace(/(AM|PM)/g, '').trim().split(':').map(Number);
        if (modifier === 'PM' && hours < 12) hours += 12;
        if (modifier === 'AM' && hours === 12) hours = 0;
        const absoluteMinutes = hours * 60 + (minutes || 0);
        return Math.max(0, absoluteMinutes - this.dayStartMinutes);
    },

    renderGrid: function(containerId, scheduleData, userRole, currentInstructorId = null, systemConflicts = []) {
        this.injectStyles();
        const container = document.getElementById(containerId);
        if (!container) return;

        const totalHoursCount = this.visibleHours.length - 1; 
        const hourBlockHeight = 90; 
        const totalGridHeight = totalHoursCount * hourBlockHeight; 
        const totalMinutesWindow = this.dayEndMinutes - this.dayStartMinutes; 
        const pixelsPerMinute = totalGridHeight / totalMinutesWindow; 

        let html = `<div class="sus-grid-outer-container">`;

        html += `<div class="sus-time-axis"><div class="sus-axis-header">Time</div>`;
        this.visibleHours.forEach((hour, idx) => {
            if (idx === this.visibleHours.length - 1) return;
            html += `<div class="sus-time-label-block" style="height: ${hourBlockHeight}px;">${hour}</div>`;
        });
        html += `</div>`;

        html += `<div class="sus-days-container">`;
        this.days.forEach(day => { html += `<div class="sus-day-column-header">${day.toUpperCase()}</div>`; });

        html += `<div class="sus-day-grid-overlay">`;
        this.days.forEach(() => {
            html += `<div class="sus-grid-day-wire">`;
            for(let h = 0; h < totalHoursCount; h++) {
                html += `<div class="sus-grid-hour-wire" style="top: ${h * hourBlockHeight}px; height: ${hourBlockHeight}px;"></div>`;
            }
            html += `</div>`;
        });
        html += `</div>`;

        html += `<div class="sus-cards-content-layer">`;
        this.days.forEach((day) => {
            html += `<div class="sus-day-card-lane">`;

            const daySlots = scheduleData.filter(s => s.day === day);

            daySlots.forEach(slot => {
                if (userRole === 'instructor' && currentInstructorId && String(slot.instructorId).trim().toLowerCase() !== String(currentInstructorId).trim().toLowerCase()) {
                    return;
                }

                const specificConflict = systemConflicts.find(c => 
                    c.courseNameA === slot.courseName || c.courseNameB === slot.courseName
                );
                const hasConflict = !!specificConflict;
                
                let cardClass = 'sus-absolute-card sus-card-approved';
                if (slot.status === 'Pending' || slot.status === 'pending') {
                    cardClass = 'sus-absolute-card sus-card-pending';
                }

                if (hasConflict || slot.status === 'Rejected' || slot.status === 'rejected') {
                    cardClass = 'sus-absolute-card sus-card-conflict';
                    if (specificConflict) slot.conflictDetail = specificConflict.detailText; 
                }

                const startMins = this.getMinutesFromStart(slot.startTime);
                const endMins = this.getMinutesFromStart(slot.endTime);
                
                const topPixel = startMins * pixelsPerMinute;
                const cardHeight = (endMins - startMins) * pixelsPerMinute - 4; 

                html += `
                    <div class="${cardClass}" 
                         style="top: ${topPixel}px; height: ${cardHeight}px;"
                         data-slot-details='${JSON.stringify(slot).replace(/'/g, "&apos;")}'
                         onmousemove="SUSTimeGridEngine.moveTooltip(event)"
                         onmouseover="SUSTimeGridEngine.showTooltip(event)" 
                         onmouseout="SUSTimeGridEngine.hideTooltip()">
                        <div class="sus-card-title">${slot.courseName}</div>
                        <div class="sus-card-meta">🚪 Rm: ${slot.roomNumber}</div>
                        <div class="sus-card-meta">🔢 Sec: ${slot.section}</div>
                `;
                
                if (hasConflict) {
                    html += `<div class="sus-status-text" style="color: #b91c1c;">⚠️ Conflict</div>`;
                } else if (slot.status === 'Pending' || slot.status === 'pending') {
                    html += `<div class="sus-status-text" style="color: #ca8a04; font-size:0.65rem;">⚠️ Waiting For Admin Approval</div>`;
                } else if (slot.status === 'Rejected' || slot.status === 'rejected') {
                    html += `<div class="sus-status-text" style="color: #b91c1c;">❌ Request Rejected</div>`;
                }
                
                html += `</div>`;
            });

            html += `</div>`;
        });

        html += `</div></div></div><div id="susGridTooltip" class="sus-tooltip"></div>`;
        container.innerHTML = html;
    },

    showTooltip: function(event) {
        const tooltip = document.getElementById('susGridTooltip');
        if (!tooltip) return;
        const card = event.currentTarget;
        const data = JSON.parse(card.getAttribute('data-slot-details'));
        
        let tooltipContent = `
            <strong>Course Name:</strong> ${data.courseName}<br>
            <strong>Subject Code:</strong> ${data.courseCode}<br>
            <strong>Section No:</strong> ${data.section}<br>
            <strong>Time Frame:</strong> ${data.startTime} - ${data.endTime}<br>
            <strong>Instructor:</strong> ${data.instructorName}<br>
            <strong>Location Room:</strong> ${data.roomNumber}<br>
            <strong>Status Log:</strong> <span>${data.status}</span>
        `;
        if (data.conflictDetail) {
            tooltipContent += `<div class="tooltip-conflict-alert">⚠️ Note: ${data.conflictDetail}</div>`;
        }
        tooltip.innerHTML = tooltipContent;
        tooltip.style.display = 'block';
        this.moveTooltip(event);
    },

    moveTooltip: function(event) {
        const tooltip = document.getElementById('susGridTooltip');
        if (tooltip) {
            tooltip.style.left = (event.pageX + 15) + 'px';
            tooltip.style.top = (event.pageY + 15) + 'px';
        }
    },

    hideTooltip: function() {
        const tooltip = document.getElementById('susGridTooltip');
        if (tooltip) tooltip.style.display = 'none';
    },

    exportToCSV: function(filename, filteredData) {
        if (!filteredData || filteredData.length === 0) {
            alert("No schedule rows available to export for current dashboard context.");
            return;
        }

        let csvContent = "";
        csvContent += "Course Name,Course Code,Section No,Academic Day,Start Time,End Time,Assigned Room,Instructor Name,Instructor ID,Status\n";
        
        filteredData.forEach(row => {
            const cName = String(row.courseName).replace(/"/g, '""');
            const cCode = String(row.courseCode).replace(/"/g, '""');
            const sec = String(row.section).replace(/"/g, '""');
            const day = String(row.day).replace(/"/g, '""');
            const sTime = String(row.startTime).replace(/"/g, '""');
            const eTime = String(row.endTime).replace(/"/g, '""');
            const room = String(row.roomNumber).replace(/"/g, '""');
            const instName = String(row.instructorName).replace(/"/g, '""');
            const instId = String(row.instructorId).replace(/"/g, '""');
            const status = String(row.status).replace(/"/g, '""');

            csvContent += `"${cName}","${cCode}","${sec}","${day}","${sTime}","${eTime}","${room}","${instName}","${instId}","${status}"\n`;
        });
        
        const bom = new Uint8Array([0xEF, 0xBB, 0xBF]);
        const blob = new Blob([bom, csvContent], { type: 'text/csv;charset=utf-8;' });
        
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.setAttribute("href", url);
        link.setAttribute("download", filename);
        
        document.body.appendChild(link);
        link.click(); 

        document.body.removeChild(link);
        URL.revokeObjectURL(url);
    }
};