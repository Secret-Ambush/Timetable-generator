document.getElementById('timetableForm').addEventListener('submit', function(e) {
    e.preventDefault();
    const formData = new FormData(this);
    
    // Replace '/upload' with the actual endpoint where you process the PDF
    fetch('/upload', {
        method: 'POST',
        body: formData,
    })
    .then(response => response.json())
    .then(data => {
        console.log('Success:', data);
        // Handle the response here, e.g., display the generated timetable
    })
    .catch((error) => {
        console.error('Error:', error);
    });
});
