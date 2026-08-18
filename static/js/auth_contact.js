function handleLogin() {
    const userField = document.getElementById('username');
    const passField = document.getElementById('password');

    if (!userField || !passField) return;

    const username = userField.value.trim();
    const password = passField.value.trim();

    if (!username || !password) {
        alert("Please enter both ID and Password");
        return;
    }

    fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            username: username, 
            password: password 
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {

            localStorage.setItem('username', username); 
            
            if (data.full_name) {
                localStorage.setItem('full_name', data.full_name);
            } else if (data.user && data.user.full_name) {
                localStorage.setItem('full_name', data.user.full_name);
            } else {
                localStorage.setItem('full_name', username); 
            }

            if (data.role === 'admin') {
                window.location.href = '/admin';
            } else if (data.role === 'instructor') {
                window.location.href = '/instructor';
            } else {
                window.location.href = '/'; 
            }
        } else {
            alert("Invalid ID or Password. Please try again.");
        }
    })
    .catch(error => {
        console.error('Error during login:', error);
        alert("Server connection failed. Make sure the Flask app is running.");
    });
}

document.addEventListener('DOMContentLoaded', function() {
    const contactForm = document.getElementById('contactForm');
    const successCard = document.getElementById('successCard');

    if (contactForm && successCard) {
        contactForm.addEventListener('submit', function(e) {
            e.preventDefault();
            const formData = new FormData(contactForm);

            fetch('http://127.0.0.1:5001/submit_contact', { 
                method: 'POST', 
                body: formData 
            })
            .then(res => { 
                if(res.ok) { 
                    contactForm.style.display = 'none'; 

                    const contactHeader = document.querySelector('.contact-header');
                    if (contactHeader) contactHeader.style.display = 'none';

                    successCard.style.display = 'block'; 
                    
                    contactForm.reset(); 
                } else {
                    alert("Submission failed. Please try again later.");
                }
            })
            .catch(err => {
                console.error("Error submitting contact form:", err);
                alert("Error connecting to the contact service.");
            });
        });
    }
});

function executeSearchWithScroll() {
    const queryEl = document.getElementById('searchID');
    const resultArea = document.getElementById('searchResultArea');
    const resultBody = document.getElementById('searchTableBody');
    
    if (!queryEl || !resultBody) return;
    
    const query = queryEl.value.toLowerCase().trim();
    if (!query) return;

    const matches = allData.filter(item => 
        Object.values(item).some(val => String(val).toLowerCase().includes(query))
    );

    if (matches.length > 0) {
        resultBody.innerHTML = matches.map(m => `
            <tr>
                <td>${m.ID || 'N/A'}</td>
                <td>${m.Name || 'N/A'}</td>
                <td>${m.Catalog || 'N/A'}</td>
                <td><span class="badge bg-light text-dark border">${m['Facil ID'] || 'N/A'}</span></td>
                <td>${m['Mtg Start'] || ''}</td>
            </tr>`).join('');
            
        resultArea.style.display = 'block';

        resultArea.scrollIntoView({ behavior: 'smooth', block: 'center' });
    } else {
        alert("No results found for: " + query);
        if (resultArea) resultArea.style.display = 'none';
    }
}