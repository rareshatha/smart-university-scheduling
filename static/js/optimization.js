function runOptimization() {
    const datasetSelect = document.getElementById('internalDataset');
    const scriptSelect = document.getElementById('optimizationScript');

    if (!datasetSelect || !scriptSelect) {
        console.error("SUS Error: Optimization DOM elements missing. Check HTML IDs.");
        return;
    }
    
    const selectedDataset = datasetSelect.value;
    const selectedScript = scriptSelect.value; 
    
    const runButton = document.querySelector("button[onclick='runOptimization()']");
    let originalText = "";
    
    if (runButton) {
        originalText = runButton.innerHTML;
        runButton.disabled = true;
        runButton.innerHTML = `<span class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>Optimizing...`;
    }

    console.log(`[SUS Engine] Sending full-stack request...`);
    console.log(`[SUS Engine] Target Dataset: ${selectedDataset}`);
    console.log(`[SUS Engine] Selected AI Script: ${selectedScript}`);

    fetch('http://127.0.0.1:5001/run_optimization', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ 
            dataset: selectedDataset,
            script: selectedScript 
        })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Server responded with status code: ${response.status}`);
        }
        return response.json();
    })
    .then(result => {
        if (result.status === "success") {
            alert(`🎉 ${result.message}`);

            if (result.data && result.data.length > 0) {
                console.log(`[SUS Engine] Success! Received ${result.data.length} optimized rows from Python.`);

                allData = result.data; 

                if (typeof updateDashboard === "function") {
                    updateDashboard();
                }

                if (typeof renderSmartTimeGrid === "function") {
                    console.log("[SUS Engine] Re-rendering Time-Grid with newly optimized data...");
                    renderSmartTimeGrid(allData);
                }

                const vTableBody = document.getElementById('vTableBody');
                if (vTableBody) {
                    vTableBody.innerHTML = ""; 
                    allData.forEach(item => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>${item.Term || ''}</td>
                            <td>${item.Subject || ''}${item.Catalog || ''}</td>
                            <td>${item['Course Title'] || item.Descr || ''}</td>
                            <td>${item['Course ID'] || item.ID || ''}</td>
                            <td>${item.Instructor || ''}</td>
                            <td>${item['Instructor ID'] || item.InstID || ''}</td>
                            <td>${item.Room || item['Facil ID'] || ''}</td>
                            <td>
                                <span class="tag-day">${item.Sun === 'Y' ? 'Sun' : ''} ${item.Mon === 'Y' ? 'Mon' : ''} ${item.Tues === 'Y' ? 'Tue' : ''} ${item.Wed === 'Y' ? 'Wed' : ''} ${item.Thurs === 'Y' ? 'Thu' : ''}</span>
                            </td>
                            <td>
                                <span class="tag-time">${item['Start Time'] || item['Mtg Start'] || ''} - ${item['End Time'] || item['Mtg End'] || ''}</span>
                            </td>
                        `;
                        vTableBody.appendChild(tr);
                    });
                }
                
            } else {
                console.warn("[SUS Engine] Optimization succeeded but returned empty dataset matrix.");
            }
        } else {
            alert(`⚠️ Optimization Engine Notice: ${result.message}`);
        }
    })
    .catch(error => {
        console.error("[SUS System Connection Error]:", error);
        alert("Failed to connect to the Python Optimization Engine.\n\n" +
              "Please ensure that:\n" +
              "1. Your Flask Server ('python3 app.py') is actively running in the terminal.\n" +
              "2. The system is listening properly on port 5001.\n" +
              "3. The requested script exists in 'optimizationCodes' folder without syntax errors.");
    })
    .finally(() => {
        if (runButton) {
            runButton.disabled = false;
            runButton.innerHTML = originalText;
        }
    });
}