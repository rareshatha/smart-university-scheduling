function populateVisitorDropdowns() {
    const tSelect = document.getElementById('termFilter');
    const sSelect = document.getElementById('subjectFilter');
    
    if (!tSelect || !sSelect || allData.length === 0) return;

    const terms = [...new Set(allData.map(item => item.Term))].filter(Boolean).sort();
    const subjects = [...new Set(allData.map(item => item.Subject))].filter(Boolean).sort();

    tSelect.innerHTML = '<option value="">All Semesters</option>' + 
                        terms.map(t => `<option value="${t}">${t}</option>`).join('');

    sSelect.innerHTML = '<option value="">All Subjects</option>' + 
                        subjects.map(s => `<option value="${s}">${s}</option>`).join('');
    
    console.log("Filters Updated ✅");
}

function filterData() {
    const termVal = document.getElementById('termFilter')?.value || "";
    const subjectVal = document.getElementById('subjectFilter')?.value || "";
    const dayVal = document.getElementById('dayFilter')?.value || "";
    const searchVal = document.getElementById('vSearch')?.value.toLowerCase().trim();

    const filtered = allData.filter(item => {
        
        const matchesTerm = !termVal || String(item.Term) === termVal;

        const matchesSubject = !subjectVal || item.Subject === subjectVal;

        const matchesDay = !dayVal || item[dayVal] === 'Y';
    
        const searchStr = (
            String(item.Name) + 
            String(item.Descr) + 
            String(item.Subject) + 
            String(item.Catalog) + 
            String(item['Facil ID'])
        ).toLowerCase();
        
        const matchesSearch = !searchVal || searchStr.includes(searchVal);

        return matchesTerm && matchesSubject && matchesDay && matchesSearch;
    });

    if (typeof renderVisitorTable === "function") {
        renderVisitorTable(filtered);
    }

    const noDataMsg = document.getElementById('noDataMsg');
    if (noDataMsg) {
        noDataMsg.style.display = filtered.length === 0 ? 'block' : 'none';
    }
}
